---
description: "A **floor** groups rooms within a building and provides a level index for device identification."
---

A floor belongs to a building and contains one or more rooms. Its slug and name are used to compose device identifiers — a numeric level (e.g. `1`, `2`) or a short label (e.g. `rdc`, `basement`) both work well.

## Fields

| Field | Required | Notes |
|---|---|---|
| `name` | ✅ | Display name of the floor (e.g. "Ground Floor", "1st Floor") |
| `slug` | ✅ | Used in device identifiers — prefer a short level code (e.g. `0`, `1`, `rdc`) |
| `description` | — | Optional free-text description |
| `image` | — | HTTP/HTTPS URL to a floor plan or representative image |

## Impact on device identifiers

The floor slug appears as the `{level}` segment in all device identifiers:

```
MQTT     : {prefix}/{level}/{room}/{function}/{position}
Hostname : {level}_{room}_{function}_{position}
```

> **Tip:** Use numeric slugs for floors when possible (`0`, `1`, `2`) — they are unambiguous and sort naturally in lists and MQTT topic browsers.
