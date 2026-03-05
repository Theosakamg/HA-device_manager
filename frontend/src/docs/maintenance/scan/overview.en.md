---
description: "Scan the local network to **discover connected devices** and refresh their IP addresses."
---

The network scanner probes the subnet defined by the **IP Prefix** in Configuration and attempts to match discovered hosts against known device MAC addresses. When a match is found, the device IP is updated automatically.

## How it works

1. The backend iterates over the configured IP range
2. Each reachable host is queried for its MAC address (ARP / mDNS)
3. Matching devices in the database have their `ip` field updated
4. The result summary reports how many addresses were resolved

## When to use it

- After a DHCP lease renewal moves devices to new IPs
- After adding new devices to the network
- Periodically to keep IP addresses accurate for deploy operations

> **Prerequisites:** the **IP Prefix** must be configured in the Configuration section before scanning. The scanner only covers the `/24` subnet of that prefix.
