---
description: "Define the **firmwares** (OS / software type) running on your devices."
---

Every device must be linked to a firmware, which is then used during **deployments** to select and filter the targeted devices.

## Fields

| Field | Description |
|---|---|
| **Name** | Unique identifier for this firmware (used as a key in provisioning workflows) |
| **Deployable** | When enabled, this firmware appears in the deploy modal as a valid target. Disable it for firmwares that exist for classification purposes only but should never be directly deployed |
| **Enabled** | Whether this firmware is available for assignment to devices |

## Why track firmwares?

- **Filter** devices by firmware when deploying
- **Group** devices by OS type for consistent updates
- **Control** which firmwares can be targeted by deploy operations via the `Deployable` flag
- Keep this list accurate for **reliable deploy operations**

## The Deployable flag

Only firmwares with **Deployable = on** appear in the deploy modal checklist. This lets you keep reference firmwares (e.g. `zigbee`, `esphome`) in the catalogue for classification and filtering purposes, while preventing accidental deploy attempts on firmware types that don't support remote provisioning.

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
