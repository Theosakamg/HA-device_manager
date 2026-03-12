# 🏠 HA Device Manager

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Compatible-brightgreen.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.1.0-orange.svg)](manifest.json)
[![HACS](https://img.shields.io/badge/HACS-Compatible-brightgreen.svg)](https://github.com/hacs)

> An independent, location-first device registry for Home Assistant.

## Philosophy

What separates home automation from robotics is, fundamentally, **spatial context**.

A robot knows where it is and acts accordingly. A home automation system should too — yet most platforms, including Home Assistant, are built around a device-and-integration model first. HA is excellent at discovering and connecting devices, but the *where* has long been secondary: rooms existed as a lightweight label, and Building/Floor support was added only recently, without a strong structural distinction.

We believe location is a first-class citizen of any automation system — and even more so in the AI era, where context is everything. Knowing that a device is on the second floor of building A, in the east-facing bedroom, is not just organisational metadata. It is actionable context for:

- **Automation** — propagate a scene, a state, or an alert across a well-defined physical scope
- **Security** — isolate or monitor by zone rather than by device name
- **Maintenance** — understand the physical reach of a firmware rollout or a network scan
- **AI assistance** — give a language model a coherent spatial model of the home to reason over

**HA Device Manager** provides that foundation: a structured, independent inventory of your physical infrastructure (Building → Floor → Room → Device), with typed models, firmware metadata, and provisioning workflows. It is designed to sit alongside HA, not replace it — you describe the desired state, HA discovers and automates.

Core principles:

- **Location first** — physical hierarchy is the primary organisational axis, not device type or integration.
- **Intent before discovery** — define what should exist and where, before HA finds it on the network.
- **Independent storage** — a dedicated SQLite database, fully decoupled from HA's own entity registry.
- **Built-in tooling** — CSV import/export, network scan, deployment helpers, all in one panel.
- **Embedded documentation** — every section in the UI ships its own inline contextual help.

## Features

- Hierarchical site plan (Building / Floor / Room)
- Device catalogue with models, firmwares and functions
- Provisioning workflows (Tasmota, WLED, Zigbee)
- CSV import / export
- Network scan & device discovery
- FR / EN interface with automatic language detection
- Collapsible inline documentation per section

## Installation

### HACS (recommended)

1. In HACS → Integrations, open **Custom repositories**
2. Add this repository URL, category **Integration**
3. Install **HA Device Manager**
4. Restart Home Assistant
5. Open `http://<your-ha>:8123/device_manager`

### Manual

```bash
git clone https://github.com/Theosakamg/HA-device_manager.git
cd HA-device_manager
./install.sh /config          # adapt path to your HA config directory
```

Then restart Home Assistant.

## Development

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ / npm
- VS Code (optional, tasks are pre-configured)

### Start the dev environment

```bash
./dev-start.sh
```

A local Home Assistant instance starts with the component live-mounted at `http://localhost:8123/device_manager`.

### Workflow

1. Edit backend code in `custom_components/` or frontend in `frontend/src/`
2. Rebuild the frontend: `cd frontend && npm run build`
3. Copy the generated bundle to the HA config directory:
   `cp frontend/dist/device-manager.js /path/to/ha/config/custom_components/device_manager/frontend/dist/`
4. `docker compose restart`
5. Hard-refresh the browser (`Ctrl+Shift+R`)

In VS Code, **Ctrl+Shift+B** runs the **Build & Restart HA** task which does steps 2–3 in one shot.

### Run backend tests

```bash
docker compose exec homeassistant bash -lc \
  "cd /config && PYTHONPATH=/config pytest -q custom_components/device_manager/tests -o addopts="
```

If pytest is not available in the container:

```bash
docker compose exec homeassistant bash -lc \
  "python3 /config/custom_components/device_manager/run_tests.py"
```

### Useful commands

| Command | Purpose |
|---|---|
| `./dev-start.sh` | Start the HA dev container |
| `./dev-stop.sh` | Stop the HA dev container |
| `./dev-logs.sh` | Follow container logs |
| `cd frontend && npm run build` | Rebuild the JS bundle |
| `docker compose restart` | Hot-reload after a build |

See [DEV_GUIDE.md](DEV_GUIDE.md) for deeper technical guidance and [SECURITY.md](SECURITY.md) for production considerations.

## Troubleshooting

### Interface won't load

- Check the bundle exists: `ls -lh custom_components/device_manager/frontend/dist/device-manager.js`
- Check HA logs for errors: `tail -f /config/home-assistant.log | grep device_manager`
- Open the browser console (F12) and look for JS errors

### Authentication errors

- Make sure you are logged into Home Assistant
- Clear the browser cache and retry

### Data not persisting

- Check file permissions on the SQLite database:
  `ls -la /config/custom_components/device_manager/*.db`
- Check HA logs for SQLite-related errors

## License

Apache-2.0 — see [LICENSE](LICENSE).

## Author

**Theosakamg** · [@Theosakamg](https://github.com/Theosakamg)

## Acknowledgments

- [Home Assistant](https://www.home-assistant.io/) community
- [Lit](https://lit.dev/) Web Components library
- [HACS](https://hacs.xyz/) for making custom integrations accessible
- All contributors and testers
