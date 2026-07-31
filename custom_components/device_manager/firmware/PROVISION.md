# Provisioning System Architecture

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Migration from Legacy](#migration-from-legacy)
- [Core Components](#core-components)
- [Firmware Adapters](#firmware-adapters)
- [Usage](#usage)
- [Configuration](#configuration)

---

## Overview

The provisioning system handles network discovery, configuration deployment, and management of IoT devices across multiple firmware types (Tasmota, WLED, Zigbee2MQTT).

**Key Features:**
- ✅ Type-safe device handling using `DmDevice` model objects
- ✅ Direct database integration (no intermediate cache files)
- ✅ Polymorphic firmware adapter pattern
- ✅ Network scanning with automatic IP updates
- ✅ Factory pattern for adapter creation
- ✅ Clean separation of concerns

---

## Architecture

### Directory Structure

```
provisioning/
├── core/                      # Core provisioning components
│   ├── __init__.py
│   ├── firmware_base.py       # FirmwareAdapter base class
│   ├── firmware_factory.py    # Factory for creating adapters
│   ├── manager.py             # ProvisioningManager for DB/settings access
│   └── scanner.py             # NetworkScanner for IP discovery
│
├── adapters/                  # Firmware-specific implementations
│   ├── __init__.py
│   ├── tasmota.py            # Tasmota device provisioning
│   ├── wled.py               # WLED device provisioning
│   └── zigbee.py             # Zigbee2MQTT device provisioning
│
├── deploy.py                 # Deploy and scan operations
├── utility.py                # Utility functions and config management
├── .env.sample              # Environment configuration template
└── legacy/                   # Old implementation (archived)
    ├── common.py
    ├── contract.py
    ├── discovery.py
    ├── tasmota.py
    ├── wled.py
    └── zigbee.py
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      deploy_controller.py                    │
│                    (HTTP API endpoints)                      │
└────────────────┬───────────────────────┬────────────────────┘
                 │                       │
                 ▼                       ▼
         ┌──────────────┐        ┌──────────────┐
         │  deploy()    │        │   scan()     │
         └──────┬───────┘        └──────┬───────┘
                │                       │
                ▼                       ▼
    ┌─────────────────────┐    ┌──────────────────┐
    │ ProvisioningManager │    │  NetworkScanner  │
    │   - load_devices()  │    │ - scan_network() │
    │   - load_settings() │    │ - update_ips()   │
    └──────────┬──────────┘    └──────────────────┘
               │                        │
               ▼                        ▼
    ┌──────────────────┐       ┌───────────────┐
    │ FirmwareFactory  │       │   Database    │
    │  - create()      │       │  (SQLite)     │
    │  - get_adapter() │       └───────────────┘
    └──────┬───────────┘
           │
           ├─────────┬─────────┬─────────┐
           ▼         ▼         ▼         ▼
    ┌──────────┐ ┌──────┐ ┌──────┐ ┌─────────┐
    │ Tasmota  │ │ WLED │ │Zigbee│ │  Base   │
    │ Adapter  │ │Adptr │ │Adptr │ │ Adapter │
    └──────────┘ └──────┘ └──────┘ └─────────┘
```

---

## Migration from Legacy

### What Changed

#### 1. **Removed Dict-based Device Structures**

**Before (Legacy):**
```python
device = {
    '_FLD_ID': 1,
    '_FLD_MAC': 'aa:bb:cc:dd:ee:ff',
    '_FLD_IP': '192.168.1.100',
    '_FLD_HOST': 'device_hostname',
    '_FLD_MQTT': 'home/l0/room/light/main',
    # ... many more fields
}

# Access via constants
mac = device[_FLD_MAC]
topic = slug_device_topic(device)
```

**After (Modern):**
```python
device = DmDevice(
    id=1,
    mac='aa:bb:cc:dd:ee:ff',
    ip='192.168.1.100',
    # ... typed fields
)

# Access via attributes and methods
mac = device.mac
topic = device.mqtt_topic(mqtt_prefix='home')
hostname = device.hostname()
```

#### 2. **Removed cache_ip.yaml File**

**Before:**
- External script writes MAC→IP mapping to `cache_ip.yaml`
- `CacheManager` loads YAML file into memory
- Devices manually populated with IP from cache dict

**After:**
- `NetworkScanner.run_network_scan()` executes script
- IPs written directly to database via `DeviceRepository`
- Devices loaded with IPs already populated via SQL JOIN

#### 3. **Simplified Contract Functions**

**Before:**
```python
from .contract import (
    _FLD_MAC, _FLD_HOST, _FLD_MQTT,
    slug_device_id, slug_device_topic,
    slug_device_name
)

hostname = slug_device_id(device)
topic = slug_device_topic(device)
name = slug_device_name(device)
```

**After:**
```python
# Methods built into DmDevice model
hostname = device.hostname()
topic = device.mqtt_topic(mqtt_prefix='home')
name = device.display_name()
fqdn = device.fqdn(dns_suffix='domo.local')
```

#### 4. **Refactored Manager Classes**

| Legacy Class | Modern Replacement | Purpose |
|--------------|-------------------|---------|
| `GlobalManager` | `ProvisioningManager` | Load devices & settings from DB |
| `CacheManager` | `NetworkScanner` | Network scan & IP updates |
| `DevicesManager` | Removed | DB access now via `DeviceRepository` |
| `FirmwareManagerBase` | `FirmwareAdapter` | Base class for firmware handlers |
| `FirmwareFactory` | `FirmwareFactory` | Factory pattern (improved) |

---

## Core Components

### 1. ProvisioningManager

**Location:** `core/manager.py`

**Responsibilities:**
- Load devices from database with full JOIN data
- Load application settings
- Filter devices by MAC or enabled status

**Usage:**
```python
from .core.manager import ProvisioningManager

manager = ProvisioningManager(db_path)

# Load all enabled devices
devices = manager.load_devices_sync(enabled_only=True)

# Load specific devices by MAC
devices = manager.load_devices_sync(
    mac_filter=['aa:bb:cc:dd:ee:ff', '11:22:33:44:55:66']
)

# Access settings
settings = manager.get_settings()
mqtt_host = manager.get_setting('bus_host', default='localhost')
```

**Key Methods:**
- `load_devices_sync(mac_filter, enabled_only)` → List[DmDevice]
- `load_devices(...)` → async version
- `load_settings()` → Dict[str, Any]
- `get_setting(key, default)` → Any

---

### 2. NetworkScanner

**Location:** `core/scanner.py`

**Responsibilities:**
- Execute network scan script
- Parse MAC→IP mappings
- Update device IPs directly in database

**Usage:**
```python
from .core.scanner import NetworkScanner

scanner = NetworkScanner(db_path)

# Run scan and update DB
stats = scanner.scan_and_update()

print(f"Total: {stats['total']}")
print(f"Mapped: {stats['mapped']}")
print(f"Not found: {stats['not_found']}")
print(f"Errors: {stats['errors']}")
```

**Configuration (via .env or database settings):**
- `SCAN_SCRIPT_CONTENT` - (Database setting) Bash script content for network scanning
- `SCAN_SCRIPT_PRIVATE_KEY_FILE` - SSH key file path (passed as env var to script)
- `SCAN_SCRIPT_SSH_USER` - SSH username (passed as env var to script)
- `SCAN_SCRIPT_SSH_HOST` - SSH host (passed as env var to script)

**Script Output Format:**
The scan script must output YAML in the format:
```yaml
192.168.1.100: aa:bb:cc:dd:ee:ff
192.168.1.101: 11:22:33:44:55:66
```

**Script Examples:**

*Example 1: Kea DHCP Query with Validation*
```bash
SSH_USER=$SCAN_SCRIPT_SSH_USER
SSH_HOST=$SCAN_SCRIPT_SSH_HOST

# SCAN_SCRIPT_PRIVATE_KEY_FILE is now the absolute path to the key file
# (uploaded via the Device Manager UI and stored in /config/dm/keys/).
PRIVATE_KEY_FILE=$SCAN_SCRIPT_PRIVATE_KEY_FILE

if [ -z "$PRIVATE_KEY_FILE" ]; then
    echo "ERROR: SCAN_SCRIPT_PRIVATE_KEY_FILE is not set" >&2
    exit 1
fi

if [ ! -f "$PRIVATE_KEY_FILE" ]; then
    echo "ERROR: SSH key file not found: $PRIVATE_KEY_FILE" >&2
    exit 1
fi

# Retrieve MAC addresses from Kea DHCP server and output in "ip: mac" format
ssh -T -i "$PRIVATE_KEY_FILE" -o BatchMode=yes -o LogLevel=ERROR -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" | jq -r '.arguments.leases[] | "\(."ip-address"): \(."hw-address")"' 2>/dev/null
```

*Example 2: ARP Scan via SSH*
```bash
PRIVATE_KEY_FILE=$SCAN_SCRIPT_PRIVATE_KEY_FILE
SSH_USER=$SCAN_SCRIPT_SSH_USER
SSH_HOST=$SCAN_SCRIPT_SSH_HOST

# Retrieve MAC addresses from remote router and output in "ip: mac" format
ssh -T -i "$PRIVATE_KEY_FILE" -o BatchMode=yes -o LogLevel=ERROR -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" 'arp -n' 2>/dev/null | awk '/ether/ {print $1": "$3}'
```

---

### 3. FirmwareAdapter (Base Class)

**Location:** `core/firmware_base.py`

**Abstract base class for all firmware-specific adapters.**

**Key Methods:**
- `get_firmware_type()` → str (abstract)
- `is_compatible(device)` → bool
- `can_deploy(device)` → bool
- `process(device)` → None (abstract)
- `post_process(devices)` → None (optional)
- `validate(device)` → None

**Example Implementation:**
```python
from ..core.firmware_base import FirmwareAdapter

class CustomAdapter(FirmwareAdapter):
    def get_firmware_type(self) -> str:
        return "CustomFirmware"
    
    def process(self, device: DmDevice) -> None:
        # Deploy configuration to device
        self.validate(device)
        self._configure_device(device)
```

---

### 4. FirmwareFactory

**Location:** `core/firmware_factory.py`

**Creates and manages firmware adapter instances based on database configuration.**

**Important:** The factory loads adapters based on the `dm_device_firmwares` table where `enabled=true` AND `deployable=true`. It does NOT use the `firmware_types` parameter to decide which adapters to load.

**Usage:**
```python
from .core.firmware_factory import FirmwareFactory

# Firmware types come from database (deployable firmwares)
deployable_firmwares = manager.load_deployable_firmwares_sync()
# Returns: ['tasmota', 'wled', 'zigbee'] (example)

# Create factory with firmwares from DB
factory = FirmwareFactory(manager, deployable_firmwares)

# Get all loaded adapters
adapters = factory.get_adapters()

# Find adapter for specific device
adapter = factory.get_adapter_for_device(device)
if adapter:
    adapter.process(device)
```

**Note:** To enable/disable a firmware for deployment, update the `deployable` field in the `dm_device_firmwares` table, not the code.

---

## Firmware Adapters

### TasmotaAdapter

**Location:** `adapters/tasmota.py`

**Handles Tasmota ESP8266/ESP32 devices.**

**Features:**
- HTTP-based configuration via Tasmota web API
- Config backup to timestamped folders
- WiFi, MQTT, timezone configuration
- Device-specific rules (buttons, lights, shutters)
- Interlock configuration

**Configuration Applied:**
- Device name and friendly names
- MQTT broker settings and topics
- WiFi credentials (SSID1/2, passwords)
- NTP servers and timezone
- Hardware-specific settings (interlock, rules)

**Device Functions Supported:**
- `Button` - Configures rules for button devices
- `Light` - Light-specific settings
- `Shutters` - Shutter/blind controls

---

### WLEDAdapter

**Location:** `adapters/wled.py`

**Handles WLED LED controller devices.**

**Features:**
- JSON API configuration
- Preset upload from file
- Network and MQTT setup
- Device reboot after configuration

**Configuration Applied:**
- Device name and mDNS hostname
- WiFi settings
- MQTT broker and topics
- NTP and timezone
- LED hardware settings
- Presets file upload

**Presets File:**
- Location: `data/wled/presets.json`
- Uploaded to each device via `/upload` endpoint

---

### ZigbeeAdapter

**Location:** `adapters/zigbee.py`

**Handles Zigbee devices via Zigbee2MQTT bridge.**

**Features:**
- MQTT-based communication with bridge
- Device configuration via YAML
- Bridge restart after configuration
- Batch processing (post_process)

**Configuration Applied:**
- Friendly names and MQTT topics
- Home Assistant device class
- Device area/room assignments

**Post-processing:**
All Zigbee devices are configured in a batch:
1. Build configuration dict for all devices
2. Merge with existing bridge config
3. Upload to bridge
4. Restart bridge to apply changes

---

## Usage

### Deploying Devices

**Important:** 
- **Firmware adapters loaded**: Based on `dm_device_firmwares` table where `enabled=true` AND `deployable=true`
- **`firmware_types` parameter**: Filters which **devices** to deploy (not which adapters to load)
- **`mac_filter` parameter**: Filters devices by MAC address
- Both filters can be combined

**Example workflow:**
1. Database has 3 deployable firmwares: Tasmota, WLED, Zigbee
2. Factory loads 3 adapters (one for each)
3. If `firmware_types=['tasmota']` → only Tasmota devices are deployed
4. If `mac_filter=['aa:bb:cc']` → only this specific device is deployed
5. If both parameters → only Tasmota devices with matching MAC

**From Python:**
```python
from pathlib import Path
from custom_components.device_manager.provisioning.deploy import deploy

# Deploy all enabled devices (for all deployable firmwares from DB)
deploy(
    db_path=Path('/path/to/database.db'),
    firmware_types=None,  # No filter = all devices
    mac_filter=None       # No filter = all devices
)

# Deploy only devices with Tasmota or WLED firmware
# (adapters are still loaded based on DB deployable firmwares)
deploy(
    db_path=db_path,
    firmware_types=['tasmota', 'wled'],  # Filter devices by firmware
    mac_filter=None
)

# Deploy only specific devices by MAC address
deploy(
    db_path=db_path,
    firmware_types=None,
    mac_filter=['aa:bb:cc:dd:ee:ff', '11:22:33:44:55:66']
)

# Combine both filters: only Tasmota devices with specific MACs
deploy(
    db_path=db_path,
    firmware_types=['tasmota'],
    mac_filter=['aa:bb:cc:dd:ee:ff']
)
```

**From HTTP API:**
```bash
# Deploy all devices (all deployable firmwares from DB)
curl -X POST http://localhost:8123/api/device_manager/deploy

# Filter devices by firmware type
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"firmware_types": ["tasmota", "wled"]}' \
  http://localhost:8123/api/device_manager/deploy

# Filter devices by MAC address
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"macs": ["aa:bb:cc:dd:ee:ff"]}' \
  http://localhost:8123/api/device_manager/deploy

# Combine both filters
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "firmware_types": ["tasmota"],
    "macs": ["aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66"]
  }' \
  http://localhost:8123/api/device_manager/deploy
```

---

### Scanning Network

**From Python:**
```python
from pathlib import Path
from custom_components.device_manager.provisioning.deploy import scan

stats = scan(db_path=Path('/path/to/database.db'))

print(f"Total devices: {stats['total']}")
print(f"Mapped: {stats['mapped']}")
print(f"Not found: {stats['not_found']}")
print(f"Errors: {stats['errors']}")
```

**From HTTP API:**
```bash
# Scan network and update IPs
curl -X POST http://localhost:8123/api/device_manager/scan
```

---

## Configuration

### Environment Variables (.env)

The provisioning system uses environment variables or database settings for configuration. See `.env.sample` for all available options.

**Network Scanning:**
```bash
# Note: The scan script content itself is stored in database settings (scan_script_content)
# These variables are passed to the script at runtime:
SCAN_SCRIPT_PRIVATE_KEY_FILE=/path/to/ssh-key
SCAN_SCRIPT_SSH_USER=root
SCAN_SCRIPT_SSH_HOST=router.local
```

**Device Credentials:**
```bash
DEVICE_PASS=admin_password
```

**WiFi Networks:**
```bash
WF1_SSID=MyWiFi
WF1_PASSWORD=wifi_password
WF2_SSID=MyWiFi_Guest
WF2_PASSWORD=guest_password
```

**MQTT Broker:**
```bash
BUS_HOST=mqtt.local
BUS_PORT=1883
BUS_USERNAME=mqtt_user
BUS_PASSWORD=mqtt_password
```

**NTP Servers:**
```bash
NTP_SRV1=pool.ntp.org
```

**Zigbee2MQTT Bridge:**
```bash
BRIDGE_HOST=zigbee-bridge.local
BRIDGE_DEVICES_CONFIG_PATH=/opt/zigbee2mqtt/data/devices.yaml
```

### Database Settings

Settings can also be stored in the database via the `settings` table. Database settings take precedence over `.env` file values.

The `utility.update_runtime_configs(settings)` function merges DB settings into the runtime configuration before each deploy/scan operation.

---

## Deploy Workflow

### Complete Deployment Process
ployable Firmwares from DB
   (WHERE enabled=true AND deployable=true)
   ↓
5. Load Devices from DB (with MAC filter if provided)
   ↓
6. Filter Devices by firmware_types (if provided)
   ↓
7. Create FirmwareFactory (with deployable firmwares)
   ↓
8. For Each Device:
   ├─ Find Compatible Adapter
   ├─ Check if Can Deploy
   ├─ Validate Device
   ├─ Process (Deploy Config)
   └─ Mark Success/Failure
   ↓
9. Post-Process (Batch Operations)
   ↓
10. Persist Deploy Status to DB
    ↓
11. Return Statistics
```

**Key Points:**
- Firmware adapters are **always** loaded from `dm_device_firmwares.deployable=true`
- `firmware_types` parameter **filters devices**, not adapters
- `mac_filter` parameter **filters devices** by MAC address
- Both filters can be combined for fine-grained control├─ Process (Deploy Config)
   └─ Mark Success/Failure
   ↓
7. Post-Process (Batch Operations)
   ↓
8. Persist Deploy Status to DB
   ↓
9. Return Statistics
```

### Scan Workflow

```
1. Load Settings from DB
   ↓
2. Update Runtime Config
   ↓
3. Create NetworkScanner
   ↓
4. Execute Scan Script
   ↓
5. Parse MAC→IP Mappings
   ↓
6. For Each Device in DB:
   ├─ Find MAC in Scan Results
   ├─ Update IP in Database
   └─ Track Statistics
   ↓
7. Return Statistics
```

---

## Extending the System

### Adding a New Firmware Adapter

1. **Create adapter file:**
   ```python
   # adapters/newfirmware.py
   from ..core.firmware_base import FirmwareAdapter
   
   class NewFirmwareAdapter(FirmwareAdapter):
       def get_firmware_type(self) -> str:
           return "NewFirmware"
       
       def process(self, device: DmDevice) -> None:
           # Implement deployment logic
           pass
   ```

2. **Register in factory:**
   ```python
   # core/firmware_factory.py
   def _create_adapter(self, firmware_type: str):
       # ... existing code ...
       elif fw_type_lower == 'newfirmware':
           from ..adapters.newfirmware import NewFirmwareAdapter
           return NewFirmwareAdapter(self._manager)
   ```

3. **Export in __init__.py:**
   ```python
   # adapters/__init__.py
   from .newfirmware import NewFirmwareAdapter
   
   __all__ = [
       "TasmotaAdapter",
       "WLEDAdapter",
       "ZigbeeAdapter",
       "NewFirmwareAdapter",
   ]
   ```

---

## Troubleshooting

### Common Issues

**1. Devices not found during deployment**
- Check device is enabled in database
- Verify device has IP address (`scan` first)
- Ensure firmware type matches adapter

**2. Scan finds no devices**
- Verify `scan_script_content` database setting is configured (System → Common tab)
- Check SSH credentials if scanning remote network (SCAN_SCRIPT_SSH_* env vars)
- Ensure script outputs correct YAML format (see examples in NetworkScanner section)

**3. Import errors**
- Clear Python cache: `find . -name "*.pyc" -delete`
- Verify all __init__.py files exist
- Check for circular imports

**4. Configuration not applied**
- Check device responds to ping
- Verify device credentials (`DEVICE_PASS`)
- Review logs for specific error messages

---

## Migration Checklist

If migrating from legacy code:

- [ ] Move old files to `legacy/` folder
- [ ] Update imports from `contract` to model methods
- [ ] Replace dict access with object attributes
- [ ] Remove `_FLD_*` constant usage
- [ ] Update `slug_*` function calls to model methods
- [ ] Replace `GlobalManager` with `ProvisioningManager`
- [ ] Replace `CacheManager` with `NetworkScanner`
- [ ] Update adapter inheritance to `FirmwareAdapter`
- [ ] Clear Python cache files
- [ ] Run tests to verify functionality

---

## Performance Considerations

**Network Scanning:**
- Scan script should complete within 5 minutes (timeout)
- Large networks: consider batching or parallel scanning

**Device Deployment:**
- Devices are processed sequentially
- Each device: ~10-30 seconds depending on firmware
- Total time = (number of devices) × (average deploy time)

**Database:**
- Uses SQLite with async operations
- Connection pooling via DatabaseManager
- Efficient JOINs for loading device relationships

---

## Security Notes

1. **Credentials:** Store sensitive data in database settings, not `.env` file
2. **SSH Keys:** Use read-only keys for network scanning
3. **API Auth:** Enable `requires_auth = True` in production controllers
4. **Device Passwords:** Use strong passwords for device access
5. **MQTT:** Configure authentication on MQTT broker

---

## References

- **DmDevice Model:** `models/device.py`
- **Device Repository:** `repositories/device_repository.py`
- **API Controllers:** `controllers/deploy_controller.py`
- **Settings Management:** `repositories/settings_repository.py`

---

## Changelog

**2026-03-10 - Database-stored Network Scan Scripts**
- ✅ Migrated network scan script from filesystem to database storage
- ✅ Added `scan_script_content` setting (stored in dm_settings table)
- ✅ Created migration 0007_add_scan_script_content.py with default Kea DHCP script
- ✅ Removed filesystem-based script loading from scanner.py
- ✅ Deleted obsolete script files (macs_kea.sh, arp_scan_remote.sh, scripts/ directory)
- ✅ Updated scanner.py to execute script content via `bash -c` directly
- ✅ Added script validation (10000 char limit, accepts all characters)
- ✅ Added frontend textarea UI in System and Maintenance views
- ✅ Updated documentation with script examples from deleted files
- ✅ Updated .env.sample to remove SCAN_SCRIPT variable
- ✅ Added EN/FR translations for scan_script_content setting

**2026-03-08 - Major Refactoring**
- ✅ Replaced dict-based devices with DmDevice model objects
- ✅ Removed cache_ip.yaml dependency
- ✅ Integrated contract functions into model methods
- ✅ Created core/ and adapters/ architecture
- ✅ Implemented ProvisioningManager and NetworkScanner
- ✅ Refactored all firmware adapters (Tasmota, WLED, Zigbee)
- ✅ Moved legacy code to legacy/ folder
- ✅ Updated deploy.py and scan operations
- ✅ Fixed all type hints and linting issues

---

*For questions or issues, refer to the codebase documentation or create an issue in the repository.*
