---
description: "Define the **hardware models** used in your installation."
---

Every device must be linked to a model, which standardises its configuration. The optional *Template* field lets you store a shared config (e.g. ESPHome YAML) for all devices of the same model.

## Why use models?

- **Standardise** configurations across identical devices
- **Simplify** CSV imports with consistent model names
- **Share** a common template for bulk management

## Template field

The `template` field is free text — use it to store a YAML snippet, a JSON profile, or any config fragment that applies globally to this model. During a **deploy**, this template can be injected as the base configuration for each targeted device.

> **Tip:** Keep model names short and machine-friendly (e.g. `esp32-cam`, `sonoff-basic`) to ensure clean MQTT topics and hostnames.
