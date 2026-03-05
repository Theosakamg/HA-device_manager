---
description: "Configure the **network prefixes and domain defaults** used across the application."
---

These settings define the global naming conventions that are automatically applied when computing device identifiers. Any change here affects all devices immediately — no rebuild required.

## Fields

| Field | Example | Effect |
|---|---|---|
| **IP Prefix** | `192.168.0` | Prepended to short numeric IPs — `42` becomes `192.168.0.42` |
| **DNS Suffix** | `domo.local` | Appended to the hostname to build the FQDN |
| **MQTT Prefix** | `home` | First segment of every MQTT topic |
| **Default Building** | `Home` | Building assigned to devices imported without an explicit building column |

## Impact on identifiers

```
Hostname : {level}_{room}_{function}_{position}
FQDN     : {hostname}.{dns_suffix}
MQTT     : {mqtt_prefix}/{level}/{room}/{function}/{position}
```

> **Tip:** Changing the DNS suffix or MQTT prefix does not rename existing retained MQTT topics in your broker — you may need to clear them manually.
