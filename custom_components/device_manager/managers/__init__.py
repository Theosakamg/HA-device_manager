"""Treatment managers for Device Manager.

Orchestration layer sitting between the ``api`` / ``ha`` entry points and the
per-firmware ``firmware`` implementations. One dedicated manager per treatment:
  * ``provision_manager`` - device loading and provisioning coordination;
  * ``update_manager``    - firmware update dispatch;
  * ``maintenance_manager`` - runtime maintenance dispatch;
  * ``csv_import_service`` - CSV device import (non-HTTP, non-firmware use-case).

Managers depend on ``firmware`` and ``persistence``; they never talk to the
database directly except through the persistence layer.
"""
