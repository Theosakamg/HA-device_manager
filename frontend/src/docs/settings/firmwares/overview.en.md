---
description: "Define the **firmwares** (OS / software type) running on your devices."
---

Every device must be linked to a firmware, which is then used during **deployments** to select and filter the targeted devices.

## Why track firmwares?

- **Filter** devices by firmware when deploying
- **Group** devices by OS type for consistent updates
- Keep this list accurate for **reliable deploy operations**

## Supported firmware types

Common firmware types used in home automation:

| Firmware | Description |
|---|---|
| `tasmota` | ESP8266/ESP32 devices running Tasmota |
| `esphome` | ESP devices managed via ESPHome |
| `wled` | LED controllers running WLED |
| `zigbee` | Zigbee devices (coordinator managed) |
| `zigbee2mqtt` | Zigbee devices connected via Zigbee2MQTT |

> **Tip:** The firmware name is used as a key during provisioning workflows. Keep it lowercase and consistent with your deploy scripts.
