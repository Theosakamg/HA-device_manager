---
description: "Complete list of all devices registered across your entire infrastructure."
---

This view is the central inventory of all devices managed by Device Manager, regardless of their physical location.

Each row represents a single device with its key attributes:

- **Status** — enabled or disabled (coloured dot)
- **MAC address** — unique hardware identifier
- **Floor / Room** — physical location in the hierarchy
- **Function** — the role this device plays (e.g. switch, sensor, light)
- **Position** — the labelled slot within the room
- **Firmware / Model** — the hardware and software profile

## Search & Filter

Use the search bar to filter devices by any visible field: MAC, IP, room, floor, model, firmware, function, or extra data. When you navigate here from another view (e.g. clicking a function in Settings), the filter is pre-filled — use **✕ Clear filter** to reset it.

## Actions

- **+ Add** — register a new device manually
- **🚀 Deploy** — open the provisioning panel to push firmware or configuration to one or more devices
- **Edit** (row) — update device details inline
- **Delete** (row) — permanently remove the device from the registry
