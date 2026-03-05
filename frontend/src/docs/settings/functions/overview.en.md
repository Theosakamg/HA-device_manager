---
description: "Define the **functional roles** of your devices (e.g. light, shutter, button, sensor)."
---

Every device must be linked to a function — this choice **directly impacts** the generated identifiers.

## Generated identifiers

| Identifier | Pattern |
|---|---|
| **MQTT topic** | `{prefix}/{level}/{room}/{function}/{position}` |
| **Hostname** | `{level}_{room}_{function}_{position}` |
| **FQDN** | `{hostname}.{dns_suffix}` |

## Why consistent functions matter

- **ACL-based MQTT security**: define topic ACL rules per function pattern (e.g. allow `light/#` only for lighting controllers)
- **Group filtering**: quickly target all "shutter" devices in a deploy
- **Readable identifiers**: self-documenting hostnames and topics in your network

## Best practices

- Use short, lowercase, singular names: `light`, `shutter`, `button`, `sensor`, `camera`
- Avoid special characters — the function becomes part of hostnames and MQTT topics
- Define functions broadly (by device role) rather than narrowly (by device model)

> **Example:** A Sonoff device controlling a roller shutter → function `shutter`  
> → MQTT topic: `home/1/living_room/shutter/left`
