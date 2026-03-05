---
description: "Manage the **reference data** used to classify and configure your devices."
---

The Settings section centralises the three building blocks that every device must reference before it can be fully configured or deployed.

## The three reference tabs

| Tab | Purpose |
|---|---|
| **Models** | Hardware models — standardise configuration across identical devices |
| **Firmwares** | OS / software type — used to filter devices during deploy operations |
| **Functions** | Functional role — directly shapes MQTT topics, hostnames and FQDNs |

> **Order matters:** populate Models, Firmwares and Functions *before* adding devices or running an import, otherwise the CSV import will fail on unknown references.
