"""Treatment managers for Device Manager.

Orchestration layer sitting between the ``api`` / ``ha`` entry points and the
per-firmware ``firmware`` implementations. One dedicated manager per treatment:
  * ``deploy_manager``    - deployment + network-scan coordination (DeployManager);
  * ``provision_manager`` - device loading and provisioning coordination;
  * ``update_manager``    - firmware update dispatch (UpdateManager);
  * ``maintenance_manager`` - runtime maintenance dispatch (MaintenanceManager);
  * ``network_scanner``   - network discovery (NetworkScanner);
  * ``csv_import_service`` - CSV device import (non-HTTP, non-firmware use-case).

Managers depend on ``firmware`` and ``persistence``; they never talk to the
database directly except through the persistence layer.
"""
