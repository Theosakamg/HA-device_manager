---
applyTo: "**/*.py"
description: "Backend architecture layering and naming conventions for the device_manager custom component."
---

# `device_manager` — Backend Architecture & Naming Conventions

This document is the source of truth for how Python code in
`custom_components/device_manager/` is organized and named. Follow it when adding
or changing any backend code. All code, comments, and docstrings are English only.

## 1. Layered architecture

Code is organized into single-responsibility packages. Dependencies flow in **one
direction only** (a layer may import from layers below it, never above):

```
api/  +  ha/            HTTP views (controllers) and Home Assistant integration
   |                    (service registration, HA entity lookup)
   v
managers/               Orchestrators / use-cases (deploy, provision, update,
   |                    maintenance, network scan, CSV import). No HTTP, no
   |                    HA specifics.
   v
firmware/               Firmware-specific treatment grouped by firmware family
   |                    (base/ + tasmota/ + wled/ + zigbee/). Adapters + clients.
   v
dto/                    Data Transfer Objects for the API/frontend boundary.
   v
persistence/            SEALED data layer: models (POPO) + repositories +
                        database_manager + migrations. No upward imports.
utils/                  Cross-cutting stdlib-only helpers (crypto, case_convert).
```

### Package map

| Package                    | Responsibility                                                                 |
| -------------------------- | ------------------------------------------------------------------------------ |
| `persistence/models/`      | Plain Old Python Objects (POPO). One dataclass-style entity per file.          |
| `persistence/repositories/`| One `*Repository` per aggregate. Only place that runs SQL.                     |
| `persistence/database_manager.py` | Connection, schema init, `migrations/` runner. Loadable standalone.     |
| `persistence/migrations/`  | Ordered `NNNN_*.py` schema migrations.                                          |
| `dto/`                     | `*Dto` objects that cross the API/frontend boundary.                            |
| `firmware/base/`           | `FirmwareAdapter`, `FirmwareFactory`, shared utility/config loading.            |
| `firmware/tasmota/`        | Tasmota client + provision/update/maintenance treatment.                       |
| `firmware/wled/`           | WLED provision treatment.                                                       |
| `firmware/zigbee/`         | Zigbee provision treatment.                                                     |
| `managers/`                | `*Manager` orchestrators (`deploy_manager`, `provision_manager`, `update_manager`, `maintenance_manager`) + `network_scanner`, `csv_import_service`. |
| `api/`                     | `HomeAssistantView` subclasses (`*_controller.py`) + `crud`/`base` helpers.     |
| `ha/`                      | HA service registration and HA device lookup.                                   |
| `utils/`                   | Pure, dependency-free helpers.                                                  |

## 2. Étanchéité — the persistence layer is sealed

`persistence/` MUST remain watertight. It defines what the data *is*, never how it
is used.

- **Never** import from `dto/`, `firmware/`, `managers/`, `api/`, or `ha/`
  inside `persistence/`.
- `persistence/` may only import: the Python standard library, `aiosqlite`,
  top-level `const`/`utils`, and other modules **within** `persistence/`.
- `database_manager.py` must stay loadable in isolation (no relative import of
  sibling layers) so migrations and tests can import it directly.
- Conversions between models and DTOs live in `dto/` or above — never inside
  `persistence/`.

## 3. Naming conventions (PEP 8)

| Kind                       | Convention                    | Example                                  |
| -------------------------- | ----------------------------- | ---------------------------------------- |
| Class                      | `PascalCase`                  | `DeviceRepository`                       |
| DB entity (model)          | `Dm` prefix + `PascalCase`    | `DmDevice`, `DmRoom`                      |
| Repository                 | `*Repository`                 | `DeviceRepository`                       |
| DTO                        | `*Dto`                        | `DeviceDto`                              |
| Manager / orchestrator     | `*Manager`                    | `ProvisioningManager`, `UpdateManager`   |
| Firmware adapter           | `*Adapter`                    | `TasmotaAdapter`                         |
| API view                   | `*APIView` / existing `*View` | `DeviceListView`                         |
| Function / method / var    | `snake_case`                  | `load_all_devices`                       |
| Constant                   | `UPPER_SNAKE_CASE`            | `DATA_KEY_DB`, `SETTING_MQTT_PREFIX`     |
| Boolean                    | `is_` / `has_` / `should_`    | `is_deployable`, `has_credentials`       |
| Module / file              | `snake_case.py`               | `network_scanner.py`                     |
| API controller file        | keep `*_controller.py`        | `device_controller.py`                   |

- DB tables use the `dm_` prefix (`dm_devices`, `dm_rooms`).
- At the frontend boundary, keys are `camelCase`; convert via DTOs / `utils.case_convert`,
  never by hand-rolling conversions in views.

## 3.1 When to introduce a DTO (shape-divergence rule)

A `*Dto` is justified **only when the payload shape diverges** from the underlying
model(s): it **adds or removes** properties, **flattens** nested objects, or
**computes** derived values.

- **Never** create a DTO for pure `snake_case` → `camelCase` renaming. The
  frontend `BaseClient` (`camelizeKeys()`) and the backend
  `utils.case_convert.to_camel_dict()` already handle that generically in both
  directions.
- A payload that is a straight serialization of **one** model stays on the
  generic `to_camel_dict()` — no DTO (e.g. building, floor, room, model,
  function, firmware, activity_log). `DeviceDto` is the intentional reference
  exception documenting the entity-DTO pattern.
- A **composite** payload — assembled from several sources or previously
  hand-built as an ad-hoc dict in a view — gets a typed DTO. The existing
  composite DTOs are:

  | DTO                            | Endpoint(s)                                   | Why it diverges                                  |
  | ------------------------------ | --------------------------------------------- | ------------------------------------------------ |
  | `ScanReportDto`                | `POST /scan`                                   | Renames + coerces scan stats (`not_found`, …)    |
  | `ImportResultDto`              | `POST /import`                                 | Flattens CSV import result + logs                |
  | `StatsDto`                     | `GET /stats`                                   | Nests `*_count` under `settingsCounts`; aggregates |
  | `HierarchyDto` / `HierarchyNodeDto` | `GET /hierarchy`, `GET /buildings/{id}/tree` | Recursive tree; adds `type`/`deviceCount`, drops FKs |
  | `HaSyncResultDto`              | `POST /ha_floors\|ha_rooms\|ha_groups/sync`    | Wraps items under a collection key + computes `total` |

- Keep composite DTOs **stdlib-only** (dataclasses + `typing`, no relative
  imports). Expose `to_api_dict()` emitting `camelCase`, and `from_*()` builders
  that read the source `snake_case`. This keeps them trivially unit-testable by
  direct `importlib` load (see `tests/test_*_dto.py`).

## 3.2 Classes vs. module functions — prefer OOP for cohesive behavior

Group **cohesive behavior into a class**; keep only genuinely pure, stateless
helpers as module-level functions. When a set of module-level functions all take
the same first argument, share configuration, or read/write common state, that
is an object asking to exist — make it one.

- **Introduce a class** when the code has an identity or holds collaborators /
  configuration, or exposes several related operations over the same subject.
  Name it by its role (§3): `*Manager`, `*Adapter`, `*Repository`, or a concrete
  noun. Bind shared dependencies in `__init__` (e.g. `hass`, a backend), and
  expose the operations as methods instead of threading the same parameter
  through free functions. Current examples:

  | Class                    | Module                          | Binds / groups                                  |
  | ------------------------ | ------------------------------- | ----------------------------------------------- |
  | `HaDeviceLookup`         | `ha/device_lookup.py`           | `hass`; device + version lookups                |
  | `UpstreamVersionSensor`  | `ha/upstream_version.py`        | `hass`; fetch + refresh + ensure                |
  | `TasmotaServiceRegistrar`| `ha/service_registration.py`    | `hass` + managers; service handlers             |
  | `TasmotaMaintenance`     | `firmware/tasmota/maintenance.py` | restart / status / AP / batches (backend)     |
  | `TasmotaUpdate`          | `firmware/tasmota/update.py`    | OTA upgrade + version-gated batch (backend)     |

- **Keep module-level functions** for pure, stateless, single-purpose helpers
  that take their whole input as arguments and hold no state — the sanctioned
  Python idiom. Do not wrap these in a class "just for OOP". These stay
  functional: `utils/case_convert.py`, `utils/` crypto helpers,
  `firmware/tasmota/common.py` (URL / topic / command builders),
  `firmware/tasmota/version.py` (version parsing/compare),
  `managers/device_loader.py` (stateless load/filter helpers).

- **Never** wrap framework-mandated module entry points in a class: Home
  Assistant's `async_setup_entry` / `async_unload_entry` in `__init__.py`, the
  `upgrade()` function of each `persistence/migrations/NNNN_*.py`, and
  `run_tests.py` stay as module-level functions.

## 4. Relative import depth

Moving a file one level deeper changes its relative import depth. From inside a
nested package (e.g. `persistence/repositories/`), reaching a top-level module
needs one extra dot:

- `from ..const import ...`  →  `from ...const import ...`
- `from ..utils import ...`  →  `from ...utils import ...`

Imports **within** the same top-level package resolve normally
(`from ..models.device import DmDevice` inside `persistence/`).

## 5. Import placement — no lazy imports to break cycles

Imports go at the **top of the module**, grouped stdlib / third-party / local
(PEP 8). Seeing every dependency in a single read is a feature — keep it that
way. A function-local ("lazy") import is allowed **only** when the reason is one
of the following and is obvious from the surrounding code:

- **Optional / heavy third-party dependency** not declared in `manifest.json`
  `requirements`, imported only on the code path that needs it and guarded so
  its absence degrades gracefully (e.g. `paho.mqtt.publish` on the MQTT path).
- **Plugin / optional-family loader** that must survive a missing package via
  `try/except ImportError` (e.g. `firmware/base/firmware_factory.py`).
- **Home Assistant startup deferral** inside `__init__.py`
  (`async_setup_entry` / `async_unload_entry`) or HA registry helpers imported
  at call time — the HA-idiomatic way to keep the integration's import light.
- **Typing-only** symbols, placed under `if TYPE_CHECKING:`.

**Never** use a lazy import to break a *circular* import. A circular import is a
signal that the one-directional layering of section 1 is violated: fix the
dependency direction (move the shared piece down a layer, or invert it) instead
of papering over it with a deferred import.

## 6. Adding a new firmware family

1. Create `firmware/<name>/` with an `__init__.py` and `provision.py`.
2. Implement an adapter subclassing `firmware.base.firmware_adapter.FirmwareAdapter`,
   named `<Name>Adapter`.
3. Register it in `firmware.base.firmware_factory.FirmwareFactory`.
4. Keep all firmware-specific HTTP/MQTT logic inside that package — managers and
   API stay firmware-agnostic and talk to adapters through the factory.
