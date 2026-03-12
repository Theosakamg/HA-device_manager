---
description: "A **building** is the top-level container of your location hierarchy."
---

Every device is ultimately located inside a building. A building groups one or more floors and carries metadata such as a slug (used in generated identifiers), a description and an optional image URL.

## Fields

| Field | Required | Notes |
|---|---|---|
| `name` | ✅ | Display name of the building |
| `slug` | ✅ | Short machine-friendly identifier — used in MQTT topics and hostnames |
| `description` | — | Free-text description visible in the detail panel |
| `image` | — | HTTP/HTTPS URL to a representative image |

## Relationships

```
Building
└── Floor (1…n)
    └── Room (1…n)
        └── Device (0…n)
```

> **Tip:** The building slug propagates into device identifiers — choose a concise, lowercase value (e.g. `main`, `annex`) and avoid renaming it once devices are deployed.
