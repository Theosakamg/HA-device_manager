---
description: "Configure the **network prefixes, domains and provisioning parameters** used across the application."
---

These settings define the global naming conventions and deployment configurations that are automatically applied when computing device identifiers and during provisioning operations. Any change here affects all devices immediately — no rebuild required.

## Network & naming settings

| Field | Example | Effect |
|---|---|---|
| **IP Prefix** | `192.168.0` | Prepended to short numeric IPs — `42` becomes `192.168.0.42` |
| **DNS Suffix** | `domo.local` | Appended to the hostname to build the FQDN |
| **MQTT Prefix** | `home` | First segment of every MQTT topic |
| **Default Building** | `Home` | Building assigned to devices imported without an explicit building column |

## Provisioning settings

These settings are used during automated firmware deployment to your devices:

| Field | Usage |
|---|---|
| **SSH Key File** | Path to the private SSH key for device access |
| **SSH User / Host** | Credentials for remote SSH connections |
| **Device Password** | Default password for new devices |
| **WiFi SSID / Password** | WiFi credentials configured during provisioning |
| **Bus Host / Port** | MQTT broker address (typically `mosquitto:1883`) |
| **Bus Username / Password** | Credentials to connect to the MQTT broker |
| **NTP Server** | NTP server for time synchronization |
| **Bridge Host** | Zigbee2MQTT bridge address if used |

## Impact on identifiers

```
Hostname : {level}_{room}_{function}_{position}
FQDN     : {hostname}.{dns_suffix}
MQTT     : {mqtt_prefix}/{level}/{room}/{function}/{position}
```

> **Tip:** Changing the DNS suffix or MQTT prefix does not rename existing retained MQTT topics in your broker — you may need to clear them manually. Provisioning settings are stored securely and are only accessible to the backend API.
