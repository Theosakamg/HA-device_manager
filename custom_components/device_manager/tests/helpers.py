"""Shared test utilities for the device_manager test suite.

Provides lazy, idempotent stub injectors and a generic module loader
so individual test files do not need to duplicate bootstrapping code.

This module is stdlib-only — no pytest or external dependencies.
"""

import importlib.util
import re
import sys
import types
from contextlib import contextmanager
from pathlib import Path

# Base directory: custom_components/device_manager/ (parent of tests/)
BASE_DIR = Path(__file__).resolve().parent.parent


def stub_ha_modules() -> None:
    """Inject minimal Home Assistant stubs into sys.modules (lazy, idempotent).

    Sets up:
      - homeassistant
      - homeassistant.components
      - homeassistant.components.http  (with HomeAssistantView = object)
    """
    ha_http = types.ModuleType("homeassistant.components.http")
    ha_http.HomeAssistantView = object  # type: ignore[attr-defined]

    for name, mod in [
        ("homeassistant", types.ModuleType("homeassistant")),
        ("homeassistant.components", types.ModuleType("homeassistant.components")),
        ("homeassistant.components.http", ha_http),
    ]:
        sys.modules.setdefault(name, mod)  # type: ignore[arg-type]


def stub_aiohttp() -> None:
    """Inject minimal aiohttp stubs into sys.modules (lazy, idempotent).

    Sets up:
      - aiohttp
      - aiohttp.web  (with Request = object, Response = object)
    """
    aiohttp_mod = types.ModuleType("aiohttp")
    web_mod = types.ModuleType("aiohttp.web")
    web_mod.Request = object  # type: ignore[attr-defined]
    web_mod.Response = object  # type: ignore[attr-defined]
    aiohttp_mod.web = web_mod  # type: ignore[attr-defined]
    sys.modules.setdefault("aiohttp", aiohttp_mod)
    sys.modules.setdefault("aiohttp.web", web_mod)


def load_module(
    rel_path: str,
    package: "str | None" = None,
    module_name: "str | None" = None,
):
    """Load a Python module from a path relative to BASE_DIR.

    Args:
        rel_path:    Path relative to BASE_DIR using forward slashes.
                     Example: 'models/device.py'
        package:     Value to set as __package__ on the loaded module.
                     Required for modules that use relative imports.
        module_name: Override the module name (defaults to filename stem).

    Returns:
        The loaded module object.
    """
    full_path = BASE_DIR / rel_path
    name = module_name or full_path.stem
    spec = importlib.util.spec_from_file_location(name, str(full_path))
    assert spec is not None and spec.loader is not None, (
        f"Cannot load module from {rel_path}"
    )
    mod = importlib.util.module_from_spec(spec)
    if package is not None:
        mod.__package__ = package
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@contextmanager
def assert_raises(expected_exc, match: str = ""):
    """Stdlib-only replacement for pytest.raises with optional message match.

    Args:
        expected_exc: Exception class expected to be raised.
        match:        Optional regex pattern that must appear in str(exc).
    """
    try:
        yield
    except expected_exc as exc:  # type: ignore[misc]
        if match and not re.search(match, str(exc)):
            raise AssertionError(
                f"{expected_exc.__name__} raised but message {str(exc)!r} "
                f"did not match pattern {match!r}"
            ) from exc
        return
    except Exception as exc:
        raise AssertionError(
            f"Expected {expected_exc.__name__}, got {type(exc).__name__}: {exc}"
        ) from exc
    raise AssertionError(f"{expected_exc.__name__} was not raised")


# ---------------------------------------------------------------------------
# High-level domain helpers
# ---------------------------------------------------------------------------

_device_model_cache: "object | None" = None


def load_device_model():
    """Load DmDevice and related refs classes (lazy, idempotent).

    Injects the minimal custom_components.* namespace and loads:
      - utils/case_convert.py
      - models/base.py
      - models/device.py

    Returns a SimpleNamespace with attributes:
      DmDevice, DeviceRoomRef, DeviceFloorRef, DeviceBuildingRef, DeviceLinkedRefs

    Calling this function multiple times returns the same cached object.
    """
    global _device_model_cache
    if _device_model_cache is not None:
        return _device_model_cache

    case_convert = load_module("utils/case_convert.py")

    _cm = types.ModuleType("custom_components")
    _dm = types.ModuleType("custom_components.device_manager")
    _utils = types.ModuleType("custom_components.device_manager.utils")
    _utils.case_convert = case_convert  # type: ignore[attr-defined]

    sys.modules.setdefault("custom_components", _cm)
    sys.modules.setdefault("custom_components.device_manager", _dm)
    sys.modules.setdefault("custom_components.device_manager.utils", _utils)
    sys.modules.setdefault("custom_components.device_manager.utils.case_convert", case_convert)

    base_mod = load_module(
        "models/base.py",
        package="custom_components.device_manager.models",
    )
    sys.modules["custom_components.device_manager.models.base"] = base_mod

    device_mod = load_module(
        "models/device.py",
        package="custom_components.device_manager.models",
    )

    import types as _types
    _device_model_cache = _types.SimpleNamespace(
        DmDevice=device_mod.DmDevice,
        DeviceRoomRef=device_mod.DeviceRoomRef,
        DeviceFloorRef=device_mod.DeviceFloorRef,
        DeviceBuildingRef=device_mod.DeviceBuildingRef,
        DeviceLinkedRefs=device_mod.DeviceLinkedRefs,
    )
    return _device_model_cache
