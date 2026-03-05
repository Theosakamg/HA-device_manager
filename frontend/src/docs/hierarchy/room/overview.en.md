---
description: "A **room** is the direct parent of devices and the lowest level of the location hierarchy."
---

A room belongs to a floor and contains devices. It is the most operationally important node — device MQTT topics, hostnames and FQDNs are all built using the room slug. Rooms also support optional access credentials (login / password) for cases where a local gateway requires authentication.

## Fields

| Field | Required | Notes |
|---|---|---|
| `name` | ✅ | Display name (e.g. "Living Room", "Kitchen") |
| `slug` | ✅ | Used in every device identifier of this room |
| `description` | — | Optional free-text description |
| `image` | — | HTTP/HTTPS URL to a photo or floor-plan cutout |
| `login` | — | Optional credential stored at room level |
| `password` | — | Optional credential stored at room level |

## Impact on device identifiers

The room slug appears as the `{room}` segment in all device identifiers:

```
MQTT     : {prefix}/{level}/{room}/{function}/{position}
Hostname : {level}_{room}_{function}_{position}
```

> **Tip:** Keep room slugs short and lowercase without special characters (e.g. `living`, `kitchen`, `garage`) — they become part of every MQTT topic and hostname in the room.
