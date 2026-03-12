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
- **Deploy status** — result of the last deploy operation (✓ Done / ✗ Fail / Never)
- **Last deploy** — timestamp of the last deploy attempt

## Search & Filter

Two filtering systems are available and can be combined:

### Text search
The search bar at the top right filters devices against all visible fields (MAC, IP, room, floor, model, firmware, function, extra data, deploy status).

### Column filters (Excel-style)
Each column header has a **▾** button that opens a dropdown with all distinct values for that column. Select one or more values to filter rows — only rows matching **all** active column filters are shown.

- A **search field** inside each dropdown lets you quickly find a value in long lists.
- Active filters appear as **badges** below the documentation panel.
- Each badge has an individual **✕** to remove that filter.
- The **✕ Clear filters** button removes all active column filters at once.
- The **🔗 Share** button copies a URL with all active filters encoded — paste it to restore the exact same view.
- Filters are **persisted in sessionStorage**: navigating away and coming back restores your last filter state.

> **Tip:** When you click the 🔍 button next to a firmware, model or function in the **Settings** view, it navigates here with the matching column filter already applied.

## Deploy status columns

| Column | Description |
|---|---|
| **Deploy status** | Badge showing the result of the last deploy: ✓ *Done* (green), ✗ *Fail* (red), or *Never* (grey) |
| **Last deploy** | Local timestamp of the last deploy attempt (set automatically by the deploy process) |

These fields are **read-only** — they are updated automatically after each deploy run and cannot be edited manually.

## Actions

- **+ Add** — register a new device manually
- **🚀 Deploy** — open the provisioning panel to push firmware or configuration to one or more devices
- **Edit** (row) — update device details inline
- **Delete** (row) — permanently remove the device from the registry
