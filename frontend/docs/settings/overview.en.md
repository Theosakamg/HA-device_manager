---
description: "Manage the **reference data** used to classify and configure your devices."
---

The Settings section centralises the three building blocks that every device must reference before it can be fully configured or deployed.

## The three reference tabs

| Tab | Purpose |
|---|---|
| **Models** | Hardware models — standardise configuration across identical devices |
| **Firmwares** | OS / software type — used to filter devices during deploy operations. The **Deployable** flag controls which firmwares appear in the deploy modal |
| **Functions** | Functional role — directly shapes MQTT topics, hostnames and FQDNs |

> **Order matters:** populate Models, Firmwares and Functions *before* adding devices or running an import, otherwise the CSV import will fail on unknown references.

## Real-time counters

Each tab displays a **counter badge** synchronized with system statistics. These counters are optimized to minimize network overhead — a single API call loads all three counters simultaneously.

## Filter devices from Settings

Each row in a settings tab has a 🔍 button. Clicking it navigates to the **Devices** view with an **Excel column filter** pre-applied on the matching column (e.g. clicking 🔍 next to firmware "Tasmota" filters the device table to show only Tasmota devices). The filter badge is visible and can be cleared as usual.
