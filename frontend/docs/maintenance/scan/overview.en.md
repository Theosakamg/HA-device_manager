---
description: "Scan the local network to **discover connected devices** and refresh their IP addresses."
---

The network scanner executes a **configurable bash script** (configured in System → Common tab) to discover MAC-to-IP mappings on your network. The script can query DHCP servers, routers, or perform ARP scans. When a MAC address matches a known device, the IP is updated directly in the database.

## How it works

1. The backend executes the configured scan script (stored in database settings)
2. The script outputs YAML format: `ip: mac` pairs
3. Each MAC address is matched against devices in the database
4. Matching devices have their `ip` field updated
5. The result summary reports how many addresses were resolved

## Script configuration

The scan script content is configured in **System → Common → Network Scan Script**. Available environment variables:
- `$SCAN_SCRIPT_SSH_USER` - SSH username for remote queries
- `$SCAN_SCRIPT_SSH_HOST` - SSH host (router/DHCP server)
- `$SCAN_SCRIPT_PRIVATE_KEY_FILE` - SSH key file path

## When to use it

- After a DHCP lease renewal moves devices to new IPs
- After adding new devices to the network
- Periodically to keep IP addresses accurate for deploy operations
- Before a mass deployment to ensure IP addresses are correct

> **Prerequisites:** Configure the **Network Scan Script** in System → Common tab and ensure SSH credentials are valid if your script requires remote access to a DHCP server or router.
