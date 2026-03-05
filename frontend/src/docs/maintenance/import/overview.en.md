---
description: "Bulk-create devices from a **CSV file** — the fastest way to populate the device inventory."
---

The CSV importer reads a structured file and creates or updates devices row by row. References to models, firmwares, functions, rooms, floors and buildings are resolved by name — make sure those reference entities exist in Settings before running an import.

## Expected CSV columns

| Column | Required | Notes |
|---|---|---|
| `name` | ✅ | Device display name |
| `mac` | ✅ | MAC address (any separator) |
| `model` | ✅ | Must match an existing model name |
| `firmware` | ✅ | Must match an existing firmware name |
| `function` | ✅ | Must match an existing function name |
| `building` | — | Falls back to the default building in Configuration |
| `floor` | — | Floor label within the building |
| `room` | — | Room label within the floor |
| `position_name` | — | Human-readable position label |
| `ip` | — | Optional static IP address |
| `enabled` | — | `true` / `false` (defaults to `true`) |

## Tips

- Use the **Export → CSV** to get a valid template with all columns
- Rows with unresolved references are skipped and shown in the error list
- The import is **additive** — existing devices are not modified
