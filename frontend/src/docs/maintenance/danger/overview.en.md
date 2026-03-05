---
description: "**Irreversible operations** — use with extreme caution."
---

The Danger Zone contains two destructive actions that cannot be undone. Always export your data first.

## Clean Database

Permanently deletes **all data** across every table — devices, rooms, floors, buildings, models, firmwares and functions. The confirmation dialog requires you to type a specific phrase to prevent accidental execution.

**Use case:** full reset to a clean state for a new installation or a test environment wipe.

## Clear IP Cache

Resets the `ip` field of **all devices** to `NULL`. The device records are preserved; only the IP addresses are wiped.

**Use case:** after a major network change (new subnet, new DHCP scope) where all previously stored IPs are invalid. Follow up with a **Scan Network** to repopulate them.

---

> ⚠️ **Always export before any Danger Zone operation.** There is no undo.
