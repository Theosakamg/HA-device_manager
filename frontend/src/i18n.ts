/**
 * Internationalization system for Device Manager.
 *
 * Supports English and French with automatic browser language detection.
 */

type Translations = {
  [key: string]: string;
};

const translations: { [lang: string]: Translations } = {
  en: {
    // Navigation
    app_title: "Device Manager",
    nav_dashboard: "Dashboard",
    nav_hierarchy: "Hierarchy",
    nav_devices: "All Devices",
    nav_map: "Map",
    nav_settings: "Settings",
    nav_maintenance: "Maintenance",
    nav_system: "System",
    nav_activity_log: "Activity Log",
    system_tab_import_export: "Import / Export",
    system_tab_common: "Common",
    system_tab_mqtt: "MQTT",
    system_tab_wifi: "WiFi",
    system_tab_zigbee: "Zigbee",
    system_tab_maintenance: "Maintenance",
    system_common_network: "Network & Application",
    system_mqtt_topics: "Topics",
    system_wifi_primary: "Primary Network",
    system_wifi_fallback: "Fallback Network",
    map_loading: "Loading 3D map…",
    filter_all: "All",

    // Dashboard
    dashboard_title: "Dashboard",
    dashboard_subtitle: "Global overview of your installation",
    dashboard_by_firmware: "Devices by Firmware",
    dashboard_by_hardware: "Devices by Hardware Model",
    dashboard_last_refresh: "Last refreshed at",
    dashboard_refresh: "Refresh",
    dashboard_deployment_title: "Deployment Statistics",
    dashboard_deployment_total: "Total Deployments",
    dashboard_deployment_success: "Successful",
    dashboard_deployment_fail: "Failed",
    dashboard_deployment_by_firmware: "Deployment Success Rate by Firmware",
    dashboard_deployment_by_hardware:
      "Deployment Success Rate by Hardware Model",
    dashboard_show_more: "Show more",
    dashboard_show_less: "Show less",
    unknown: "Unknown",

    // Hierarchy
    hierarchy_title: "Location Hierarchy",
    building: "Building",
    buildings: "Buildings",
    floor: "Floor",
    floors: "Floors",
    room: "Room",
    rooms: "Rooms",
    add_building: "Add Building",
    add_floor: "Add Floor",
    add_room: "Add Room",
    edit_building: "Edit Building",
    edit_floor: "Edit Floor",
    edit_room: "Edit Room",
    delete_building: "Delete Building",
    delete_floor: "Delete Floor",
    delete_room: "Delete Room",
    no_buildings: "No buildings yet. Create your first building!",
    no_floors: "No floors in this building.",
    no_rooms: "No rooms in this floor.",
    no_devices_in_room: "No devices in this room.",
    device_count: "devices",
    room_login: "Login",
    room_password: "Password",
    show_password: "Show password",
    hide_password: "Hide password",
    parent_floor: "Parent Floor",
    parent_building: "Parent Building",
    generated_fields: "Generated Fields",
    mqtt_topic: "MQTT topic",
    ha_entity_id: "HA entity_id",
    full_name: "Full name",

    // Devices
    devices_list: "Devices",
    device: "Device",
    devices: "Devices",
    add_device: "Add Device",
    edit_device: "Edit Device",
    device_mac: "MAC Address",
    device_ip: "IP Address",
    device_enabled: "Enabled",
    device_state: "State",
    state_deployed: "Deployed",
    state_parking: "Parking",
    state_out_of_order: "Out of Order",
    state_deployed_hot: "Hot",
    device_level: "Floor",
    device_position_name: "Position",
    device_location: "Name",
    device_position_slug: "Position Slug",
    device_mode: "Mode",
    device_interlock: "Interlock",
    device_ha_class: "HA Device Class",
    device_extra: "Extra",
    device_room: "Room",
    device_model: "Model",
    device_firmware: "Firmware",
    device_function: "Function",
    device_target: "Target Device",
    device_link: "Link",
    device_hostname: "Hostname",
    device_mqtt: "MQTT Topic",
    device_fqdn: "FQDN",
    select_room: "Select a room",
    select_model: "Select a model",
    select_firmware: "Select a firmware",
    select_function: "Select a function",
    select_target: "Select target (optional)",
    no_devices: "No devices yet. Add your first device!",
    device_last_deploy_at: "Last Deploy",
    device_last_deploy_status: "Status",
    deploy_status_done: "Done",
    deploy_status_fail: "Fail",
    deploy_status_none: "Never",

    // Deploy
    deploy: "Deploy All",
    deploy_title: "Deploy Firmwares",
    deploy_select_firmwares: "Select firmwares to deploy",
    deploy_no_firmwares: "No firmwares available",
    deploy_confirm: "Confirm Deploy",
    deploy_result_title: "Deploy Results",
    deploy_total_devices: "Total devices",
    deploy_firmware_selected: "Firmwares selected",
    deploy_no_devices: "No devices match selected firmwares",
    deploy_select_all: "Select All",
    deploy_deselect_all: "Deselect All",
    deploy_firmware: "Firmware",
    deploy_device_count: "Devices",
    deploy_device_mac: "MAC",
    deploy_device_position: "Position",
    deploy_new: "New Deploy",
    batch_selected: "device(s) selected",
    batch_select_mode: "Selection mode",
    batch_exit_select_mode: "Exit selection",
    batch_deploy_selected: "Deploy selected",
    batch_clear_selection: "Clear selection",
    batch_deploy_triggered: "Deployment triggered",
    batch_deploy_error: "Deploy failed",

    // Settings
    settings_title: "Settings",
    tab_models: "Models",
    tab_firmwares: "Firmwares",
    tab_functions: "Functions",
    tab_models_desc:
      "Define the **hardware models** used in your installation.\n\nEvery device must be linked to a model, which standardises its configuration. The optional *Template* field lets you store a shared config (e.g. ESPHome YAML) for all devices of the same model.\n\n- **Standardise** configurations across identical devices\n- **Simplify** CSV imports with consistent model names\n- **Share** a common template for bulk management",
    tab_firmwares_desc:
      "Define the **firmwares** (OS / software type) running on your devices.\n\nEvery device must be linked to a firmware, which is then used during **deployments** to select and filter the targeted devices.\n\n- **Filter** devices by firmware when deploying\n- **Group** devices by OS type for consistent updates\n- Keep this list accurate for **reliable deploy operations**",
    tab_functions_desc:
      "Define the **functional roles** of your devices (e.g. light, shutter, button, sensor).\n\nEvery device must be linked to a function — this choice **directly impacts** the generated identifiers:\n\n- **MQTT topic**: `{prefix}/{level}/{room}/{function}/{position}`\n- **Hostname**: `{level}_{room}_{function}_{position}`\n- **FQDN**: `{hostname}.{dns_suffix}`\n\nA consistent naming convention also enables **fine-grained MQTT security**: you can define ACL rules based on topic patterns (e.g. allow `light/#` only for lighting controllers) to restrict access per function.",
    model_name: "Model Name",
    model_template: "Template",
    firmware_name: "Firmware Name",
    firmware_deployable: "Deployable",
    function_name: "Function Name",
    enabled: "Enabled",
    disabled: "Disabled",
    no_models: "No models defined.",
    no_firmwares: "No firmwares defined.",
    no_functions: "No functions defined.",

    // Import
    import_title: "Import CSV",
    import_select_file: "Select CSV file",
    import_start: "Start Import",
    import_success: "Import completed successfully",
    import_error: "Import failed",
    import_result_created: "Created",
    import_result_errors: "Errors",
    import_result_line: "Line",

    // Export
    export_title: "Export Data",
    export_desc: "Download all devices in your preferred format.",

    // SQLite DB Backup
    db_backup_title: "Database Backup",
    db_backup_desc:
      "Export or restore the full SQLite database. The WAL buffer is flushed before export to guarantee a consistent snapshot.",
    db_export_btn: "Export DB (.sqlite)",
    db_import_btn: "Restore DB from file",
    db_import_confirm:
      "WARNING: Restoring the database will replace ALL current data. A backup will be created automatically. Continue?",
    db_import_success: "Database restored successfully. Backup saved at:",
    db_import_error: "Database restore failed.",
    db_exporting: "Exporting…",
    db_importing: "Restoring…",

    // Configuration (user-configurable parameters)
    config_title: "Configuration",
    config_desc:
      "Configure network prefixes and domain defaults used across the application.",
    config_ip_prefix: "IP Prefix",
    config_ip_prefix_hint:
      "Prefix for numeric-only IP addresses (e.g. 192.168.0)",
    config_dns_suffix: "DNS Suffix",
    config_dns_suffix_hint:
      "Domain appended to hostnames for FQDN (e.g. domo.local)",
    config_mqtt_prefix: "MQTT Topic Prefix",
    config_mqtt_prefix_hint: "First segment of MQTT topics (e.g. home)",
    config_default_home: "Default Building Name",
    config_default_home_hint:
      "Name used when importing devices without an explicit building",
    config_saved: "Settings saved successfully",
    config_save_error: "Failed to save settings",
    config_loading: "Loading settings…",
    // Provisioning settings
    config_prov_title: "Provisioning",
    config_prov_desc:
      "Configure credentials and addresses used during device deployment and network scanning.",
    config_scan_section: "Network Scan (SSH)",
    config_scan_ssh_key_file: "SSH Key File",
    config_scan_ssh_key_file_hint:
      "Absolute path to the private key stored in /config/dm/keys/",
    config_scan_ssh_key_upload: "Upload Private Key",
    config_scan_ssh_key_upload_hint:
      "Upload the SSH private key file (will be stored in /config/dm/keys/ with mode 0600)",
    config_scan_ssh_key_uploading: "Uploading…",
    config_scan_ssh_key_upload_success: "Key uploaded and path saved",
    config_scan_ssh_key_upload_error: "Upload failed",
    config_scan_ssh_user: "SSH User",
    config_scan_ssh_user_hint:
      "Username for SSH connection to the router (e.g. root)",
    config_scan_ssh_host: "SSH Host",
    config_scan_ssh_host_hint:
      "IP address or hostname of the router (e.g. 192.168.0.254)",
    config_scan_script_content: "Network Scan Script",
    config_scan_script_security_warning:
      "SECURITY WARNING: This script is executed with server privileges. Only insert trusted code.",
    config_scan_script_content_hint:
      "Bash script to discover MAC-to-IP mappings. Must output YAML format: 'ip: mac'. Available variables: $SCAN_SCRIPT_SSH_USER, $SCAN_SCRIPT_SSH_HOST, $SCAN_SCRIPT_PRIVATE_KEY_FILE",
    config_device_section: "Device Access",
    config_device_pass: "Device Password",
    config_device_pass_hint:
      "Web interface password for devices (Tasmota / WLED)",
    config_ntp_section: "NTP",
    config_ntp_server1: "NTP Server",
    config_ntp_server1_hint: "Primary NTP server address (e.g. pool.ntp.org)",
    config_wifi_section: "WiFi",
    config_wifi1_ssid: "WiFi 1 SSID",
    config_wifi1_ssid_hint: "Primary WiFi network name",
    config_wifi1_password: "WiFi 1 Password",
    config_wifi1_password_hint: "Primary WiFi network password",
    config_wifi2_ssid: "WiFi 2 SSID",
    config_wifi2_ssid_hint: "Fallback WiFi network name (optional)",
    config_wifi2_password: "WiFi 2 Password",
    config_wifi2_password_hint: "Fallback WiFi network password (optional)",
    config_bus_section: "MQTT Bus",
    config_bus_host: "MQTT Broker Host",
    config_bus_host_hint: "Hostname or IP of the MQTT broker (e.g. bus)",
    config_bus_port: "MQTT Broker Port",
    config_bus_port_hint: "TCP port of the MQTT broker (default: 1883)",
    config_bus_username: "MQTT Username",
    config_bus_username_hint: "Authentication username for the MQTT broker",
    config_bus_password: "MQTT Password",
    config_bus_password_hint: "Authentication password for the MQTT broker",
    config_bridge_section: "Zigbee Bridge",
    config_bridge_host: "Bridge Host",
    config_bridge_host_hint:
      "SSH address of the Zigbee2MQTT host (user@host, optional)",
    config_bridge_devices_config_path: "Devices Config Path",
    config_bridge_devices_config_path_hint:
      "Remote path to the Zigbee2MQTT devices.yaml file",
    // Maintenance
    maint_danger_zone: "Danger Zone",
    maint_danger_desc:
      "These operations are irreversible. Proceed with caution.",
    maint_clean_db: "Clean Database",
    maint_clean_db_desc:
      "Delete all data (devices, rooms, floors, buildings, models, firmwares, functions).",
    maint_confirm_title: "Confirm Database Wipe",
    maint_confirm_desc:
      "This action will permanently delete ALL data. Type the phrase below to confirm:",
    maint_confirm_placeholder: "Type the confirmation phrase...",
    maint_confirm_execute: "Wipe All Data",
    maint_clean_success: "Database cleaned successfully",
    maint_rows_deleted: "rows deleted",
    maint_scan_network: "Scan Network",
    maint_scan_network_desc:
      "Scan the network to discover connected devices and update IP addresses.",
    maint_scan_triggered: "Scan completed",
    maint_scan_running: "Scanning...",
    maint_scan_stat_total: "Total devices",
    maint_scan_stat_mapped: "Mapped (IP found)",
    maint_scan_stat_not_found: "Not found",
    maint_scan_stat_errors: "Errors",
    maint_scan_stat_error_details: "Error details",
    maint_clear_ip_cache: "Clear IP Cache",
    maint_clear_ip_cache_desc:
      "Reset the IP address of all devices to NULL. Useful after a network change.",
    maint_clear_ip_cache_success: "IP cache cleared",
    maint_clear_ip_updated: "devices updated",

    // Common
    name: "Name",
    slug: "Slug",
    description: "Description",
    image: "Image",
    save: "Save",
    cancel: "Cancel",
    reset: "Reset",
    delete: "Delete",
    edit: "Edit",
    add: "Add",
    close: "Close",
    confirm: "Confirm",
    loading: "Loading...",
    error_loading: "Error loading data",
    error_saving: "Error saving",
    error_deleting: "Error deleting",
    confirm_delete: "Are you sure you want to delete this item?",
    confirm_delete_cascade: "This will also delete all child items. Continue?",
    success_created: "Created successfully",
    success_updated: "Updated successfully",
    success_deleted: "Deleted successfully",
    previous: "Previous",
    next: "Next",
    reload: "Reload",
    search: "Search",
    filter_devices: "Filter devices",
    clear_filter: "Clear filter",
    clear_all_filters: "Clear filters",
    col_filter_select_all: "All",
    col_filter_clear_col: "None",
    col_filter_title: "Filter column",
    col_filter_search: "Search values...",
    col_filter_no_results: "No matching values",
    filter_link_copied: "Link copied!",
    filter_share: "Copy filter link",
    actions: "Actions",
    id: "ID",
    no_items: "No items yet.",
    created_at: "Created At",
    updated_at: "Updated At",
    view_in_devices: "View in Devices",
    validation_name_required: "Name is required",
    validation_slug_required: "Slug is required",
    validation_slug_format:
      "Slug must contain only letters, numbers, hyphens and underscores",
    validation_url_format: "Image must be a valid http/https URL",

    // HA Groups
    ha_groups_sync: "Sync HA Groups",
    ha_groups_syncing: "Syncing groups…",
    ha_groups_sync_success: "{count} group(s) synced to Home Assistant",
    ha_groups_sync_none: "No groups synced (no devices with function assigned)",
    ha_groups_sync_error: "Failed to sync HA groups",
    config_ha_groups_section: "HA Groups Sync",
    config_ha_groups_empty_groups: "Create empty groups",
    config_ha_groups_empty_groups_hint:
      "When enabled, groups are created even if no matching HA entities are registered for the devices in that room.",
    // HA Floors
    ha_floors_sync: "Sync HA Floors",
    ha_floors_syncing: "Syncing floors\u2026",
    ha_floors_sync_success: "{count} floor(s) synced to Home Assistant",
    ha_floors_sync_none: "No floors to sync",
    ha_floors_sync_error: "Failed to sync HA floors",
    // HA Rooms
    ha_rooms_sync: "Sync HA Rooms",
    ha_rooms_syncing: "Syncing rooms\u2026",
    ha_rooms_sync_success: "{count} room(s) synced to Home Assistant",
    ha_rooms_sync_none: "No rooms to sync",
    ha_rooms_sync_error: "Failed to sync HA rooms",

    // Activity Log
    activity_log_date_from: "From",
    activity_log_date_to: "To",
    activity_log_event_type: "Event Type",
    activity_log_config_change: "Config Change",
    activity_log_action: "Action",
    activity_log_entity_type: "Entity Type",
    activity_log_user_col: "User",
    activity_log_severity: "Severity",
    activity_log_severity_info: "Info",
    activity_log_severity_warning: "Warning",
    activity_log_severity_error: "Error",
    activity_log_apply_filters: "Apply",
    activity_log_reset_filters: "Reset",
    activity_log_empty: "No activity log entries found.",
    activity_log_col_timestamp: "Timestamp",
    activity_log_col_user: "User",
    activity_log_col_type: "Type",
    activity_log_col_entity: "Entity",
    activity_log_col_severity: "Severity",
    activity_log_col_message: "Message",
    activity_log_click_expand: "Click to expand details",
    activity_log_result: "Output",
    activity_log_total: "Total entries",
    activity_log_purge_title: "Purge Old Entries",
    activity_log_purge_label: "Delete entries older than (days):",
    activity_log_purge_btn: "Purge",
    activity_log_purge_success: "Entries deleted",
  },
  fr: {
    // Navigation
    app_title: "Gestionnaire d'Équipements",
    nav_dashboard: "Tableau de bord",
    nav_hierarchy: "Hiérarchie",
    nav_devices: "Tous les Équipements",
    nav_map: "Map",
    nav_settings: "Paramètres",
    nav_maintenance: "Maintenance",
    nav_system: "Système",
    nav_activity_log: "Journal d'activité",
    system_tab_import_export: "Import / Export",
    system_tab_common: "Commun",
    system_tab_mqtt: "MQTT",
    system_tab_wifi: "WiFi",
    system_tab_zigbee: "Zigbee",
    system_tab_maintenance: "Maintenance",
    system_common_network: "Réseau & Application",
    system_mqtt_topics: "Topics",
    system_wifi_primary: "Réseau Principal",
    system_wifi_fallback: "Réseau de Secours",
    map_loading: "Chargement de la carte 3D…",
    filter_all: "Tous",

    // Dashboard
    dashboard_title: "Tableau de bord",
    dashboard_subtitle: "Vue d'ensemble globale de votre installation",
    dashboard_by_firmware: "Équipements par Firmware",
    dashboard_by_hardware: "Équipements par Modèle Matériel",
    dashboard_last_refresh: "Actualisé à",
    dashboard_refresh: "Actualiser",
    dashboard_deployment_title: "Statistiques de Déploiement",
    dashboard_deployment_total: "Déploiements Totaux",
    dashboard_deployment_success: "Réussis",
    dashboard_deployment_fail: "Échoués",
    dashboard_deployment_by_firmware: "Taux de Réussite par Firmware",
    dashboard_deployment_by_hardware: "Taux de Réussite par Modèle Matériel",
    dashboard_show_more: "Voir plus",
    dashboard_show_less: "Voir moins",
    unknown: "Inconnu",

    // Hierarchy
    hierarchy_title: "Hiérarchie des Emplacements",
    building: "Bâtiment",
    buildings: "Bâtiments",
    floor: "Étage",
    floors: "Étages",
    room: "Pièce",
    rooms: "Pièces",
    add_building: "Ajouter un Bâtiment",
    add_floor: "Ajouter un Étage",
    add_room: "Ajouter une Pièce",
    edit_building: "Modifier le Bâtiment",
    edit_floor: "Modifier l'Étage",
    edit_room: "Modifier la Pièce",
    delete_building: "Supprimer le Bâtiment",
    delete_floor: "Supprimer l'Étage",
    delete_room: "Supprimer la Pièce",
    no_buildings: "Aucun bâtiment. Créez votre premier bâtiment !",
    no_floors: "Aucun étage dans ce bâtiment.",
    no_rooms: "Aucune pièce dans cet étage.",
    no_devices_in_room: "Aucun équipement dans cette pièce.",
    device_count: "équipements",
    room_login: "Identifiant",
    room_password: "Mot de passe",
    show_password: "Afficher le mot de passe",
    hide_password: "Masquer le mot de passe",
    parent_floor: "Étage parent",
    parent_building: "Bâtiment parent",
    generated_fields: "Champs générés",
    mqtt_topic: "Topic MQTT",
    ha_entity_id: "entity_id HA",
    full_name: "Nom complet",

    // Devices
    devices_list: "Équipements",
    device: "Équipement",
    devices: "Équipements",
    add_device: "Ajouter un Équipement",
    edit_device: "Modifier l'Équipement",
    device_mac: "Adresse MAC",
    device_ip: "Adresse IP",
    device_enabled: "Activé",
    device_state: "État",
    state_deployed: "Déployé",
    state_parking: "Parking",
    state_out_of_order: "Hors Service",
    state_deployed_hot: "Hot",
    device_level: "Étage",
    device_position_name: "Position",
    device_location: "Nom",
    device_position_slug: "Slug de Position",
    device_mode: "Mode",
    device_interlock: "Verrouillage",
    device_ha_class: "Classe HA",
    device_extra: "Extra",
    device_room: "Pièce",
    device_model: "Modèle",
    device_firmware: "Firmware",
    device_function: "Fonction",
    device_target: "Équipement Cible",
    device_link: "Lien",
    device_hostname: "Nom d'hôte",
    device_mqtt: "Topic MQTT",
    device_fqdn: "FQDN",
    select_room: "Sélectionner une pièce",
    select_model: "Sélectionner un modèle",
    select_firmware: "Sélectionner un firmware",
    select_function: "Sélectionner une fonction",
    select_target: "Sélectionner la cible (optionnel)",
    no_devices: "Aucun équipement. Ajoutez votre premier équipement !",
    device_last_deploy_at: "Déployé le",
    device_last_deploy_status: "Statut",
    deploy_status_done: "Succès",
    deploy_status_fail: "Échec",
    deploy_status_none: "Jamais",

    // Deploy
    deploy: "Déployer tout",
    deploy_title: "Déployer les Firmwares",
    deploy_select_firmwares: "Sélectionner les firmwares à déployer",
    deploy_no_firmwares: "Aucun firmware disponible",
    deploy_confirm: "Confirmer le Déploiement",
    deploy_result_title: "Résultats du Déploiement",
    deploy_total_devices: "Total équipements",
    deploy_firmware_selected: "Firmwares sélectionnés",
    deploy_no_devices:
      "Aucun équipement ne correspond aux firmwares sélectionnés",
    deploy_select_all: "Tout sélectionner",
    deploy_deselect_all: "Tout désélectionner",
    deploy_firmware: "Firmware",
    deploy_device_count: "Équipements",
    deploy_device_mac: "MAC",
    deploy_device_position: "Position",
    deploy_new: "Nouveau Déploiement",
    batch_selected: "équipement(s) sélectionné(s)",
    batch_select_mode: "Mode sélection",
    batch_exit_select_mode: "Quitter la sélection",
    batch_deploy_selected: "Déployer la sélection",
    batch_clear_selection: "Effacer la sélection",
    batch_deploy_triggered: "Déploiement déclenché",
    batch_deploy_error: "Échec du déploiement",

    // Settings
    settings_title: "Paramètres",
    tab_models: "Modèles",
    tab_firmwares: "Firmwares",
    tab_functions: "Fonctions",
    tab_models_desc:
      "Définissez les **modèles matériels** utilisés dans votre installation.\n\nChaque équipement doit être rattaché à un modèle, ce qui permet de standardiser sa configuration. Le champ *Template* (optionnel) stocke une config partagée (ex : YAML ESPHome) pour tous les équipements du même modèle.\n\n- **Standardisez** les configurations d'équipements identiques\n- **Simplifiez** les imports CSV avec des noms de modèles cohérents\n- **Partagez** un template commun pour la gestion en masse",
    tab_firmwares_desc:
      "Définissez les **firmwares** (OS / type de logiciel) embarqués sur vos équipements.\n\nChaque équipement doit être rattaché à un firmware, utilisé ensuite lors des **déploiements** pour sélectionner et filtrer les équipements ciblés.\n\n- **Filtrez** les équipements par firmware lors du déploiement\n- **Regroupez** les équipements par type d'OS pour des mises à jour cohérentes\n- Maintenez cette liste à jour pour des **opérations de déploiement fiables**",
    tab_functions_desc:
      "Définissez les **rôles fonctionnels** de vos équipements (ex : lumière, volet, bouton, capteur).\n\nChaque équipement doit être rattaché à une fonction — ce choix **impacte directement** les identifiants générés :\n\n- **Topic MQTT** : `{prefix}/{niveau}/{pièce}/{fonction}/{position}`\n- **Hostname** : `{niveau}_{pièce}_{fonction}_{position}`\n- **FQDN** : `{hostname}.{suffixe_dns}`\n\nUne convention de nommage harmonisée permet aussi d'appliquer une **sécurité MQTT fine** : vous pouvez définir des règles ACL par pattern de topic (ex : autoriser `light/#` uniquement pour les contrôleurs d'éclairage) afin de restreindre l'accès par fonction.",
    model_name: "Nom du Modèle",
    model_template: "Template",
    firmware_name: "Nom du Firmware",
    firmware_deployable: "Déployable",
    function_name: "Nom de la Fonction",
    enabled: "Activé",
    disabled: "Désactivé",
    no_models: "Aucun modèle défini.",
    no_firmwares: "Aucun firmware défini.",
    no_functions: "Aucune fonction définie.",

    // Import
    import_title: "Importer CSV",
    import_select_file: "Sélectionner le fichier CSV",
    import_start: "Lancer l'Import",
    import_success: "Import terminé avec succès",
    import_error: "L'import a échoué",
    import_result_created: "Créés",
    import_result_errors: "Erreurs",
    import_result_line: "Ligne",

    // Export
    export_title: "Exporter les Données",
    export_desc: "Télécharger tous les équipements dans le format souhaité.",

    // SQLite DB Backup
    db_backup_title: "Sauvegarde de la Base de Données",
    db_backup_desc:
      "Exportez ou restaurez la base SQLite complète. Le buffer WAL est vidé avant l'export pour garantir un snapshot cohérent.",
    db_export_btn: "Exporter la DB (.sqlite)",
    db_import_btn: "Restaurer la DB depuis un fichier",
    db_import_confirm:
      "ATTENTION : La restauration remplacera TOUTES les données actuelles. Une sauvegarde sera créée automatiquement. Continuer ?",
    db_import_success:
      "Base de données restaurée avec succès. Sauvegarde enregistrée :",
    db_import_error: "La restauration a échoué.",
    db_exporting: "Export en cours…",
    db_importing: "Restauration en cours…",

    // Configuration (user-configurable parameters)
    config_title: "Configuration",
    config_desc:
      "Configurez les préfixes réseau et les domaines par défaut utilisés dans l'application.",
    config_ip_prefix: "Préfixe IP",
    config_ip_prefix_hint:
      "Préfixe pour les IP numériques courtes (ex: 192.168.0)",
    config_dns_suffix: "Suffixe DNS",
    config_dns_suffix_hint:
      "Domaine ajouté aux hostnames pour le FQDN (ex: domo.local)",
    config_mqtt_prefix: "Préfixe MQTT",
    config_mqtt_prefix_hint: "Premier segment des topics MQTT (ex: home)",
    config_default_home: "Nom de Bâtiment par Défaut",
    config_default_home_hint:
      "Nom utilisé lors de l'import sans bâtiment explicite",
    config_saved: "Paramètres enregistrés avec succès",
    config_save_error: "Échec de l'enregistrement des paramètres",
    config_loading: "Chargement des paramètres…",

    // Provisioning settings
    config_prov_title: "Provisioning",
    config_prov_desc:
      "Configurez les identifiants et adresses utilisés lors du déploiement des équipements et du scan réseau.",
    config_scan_section: "Scan Réseau (SSH)",
    config_scan_ssh_key_file: "Fichier clé SSH",
    config_scan_ssh_key_file_hint:
      "Chemin absolu vers la clé stockée dans /config/dm/keys/",
    config_scan_ssh_key_upload: "Envoyer la clé privée",
    config_scan_ssh_key_upload_hint:
      "Téléverser le fichier de clé privée SSH (stocké dans /config/dm/keys/ avec les droits 0600)",
    config_scan_ssh_key_uploading: "Envoi en cours…",
    config_scan_ssh_key_upload_success: "Clé envoyée et chemin enregistré",
    config_scan_ssh_key_upload_error: "Envoi échoué",
    config_scan_ssh_user: "Utilisateur SSH",
    config_scan_ssh_user_hint:
      "Nom d'utilisateur pour la connexion SSH au routeur (ex: root)",
    config_scan_ssh_host: "Hôte SSH",
    config_scan_ssh_host_hint:
      "Adresse IP ou hostname du routeur (ex: 192.168.0.254)",
    config_scan_script_content: "Script de scan réseau",
    config_scan_script_security_warning:
      "ATTENTION SÉCURITÉ : Ce script est exécuté avec les privilèges du serveur. N'insérez que du code de confiance.",
    config_scan_script_content_hint:
      "Script bash pour découvrir les correspondances MAC→IP. Doit retourner du YAML au format 'ip: mac'. Variables disponibles: $SCAN_SCRIPT_SSH_USER, $SCAN_SCRIPT_SSH_HOST, $SCAN_SCRIPT_PRIVATE_KEY_FILE",
    config_device_section: "Accès Appareil",
    config_device_pass: "Mot de passe appareil",
    config_device_pass_hint:
      "Mot de passe de l'interface web des appareils (Tasmota / WLED)",
    config_ntp_section: "NTP",
    config_ntp_server1: "Serveur NTP",
    config_ntp_server1_hint:
      "Adresse du serveur NTP principal (ex: pool.ntp.org)",
    config_wifi_section: "WiFi",
    config_wifi1_ssid: "SSID WiFi 1",
    config_wifi1_ssid_hint: "Nom du réseau WiFi principal",
    config_wifi1_password: "Mot de passe WiFi 1",
    config_wifi1_password_hint: "Mot de passe du réseau WiFi principal",
    config_wifi2_ssid: "SSID WiFi 2",
    config_wifi2_ssid_hint: "Nom du réseau WiFi de secours (optionnel)",
    config_wifi2_password: "Mot de passe WiFi 2",
    config_wifi2_password_hint:
      "Mot de passe du réseau WiFi de secours (optionnel)",
    config_bus_section: "Bus MQTT",
    config_bus_host: "Hôte MQTT",
    config_bus_host_hint: "Hostname ou IP du broker MQTT (ex: bus)",
    config_bus_port: "Port MQTT",
    config_bus_port_hint: "Port TCP du broker MQTT (défaut : 1883)",
    config_bus_username: "Utilisateur MQTT",
    config_bus_username_hint: "Nom d'utilisateur pour l'authentification MQTT",
    config_bus_password: "Mot de passe MQTT",
    config_bus_password_hint: "Mot de passe pour l'authentification MQTT",
    config_bridge_section: "Passerelle Zigbee",
    config_bridge_host: "Hôte de la passerelle",
    config_bridge_host_hint:
      "Adresse SSH de l'hôte Zigbee2MQTT (user@host, optionnel)",
    config_bridge_devices_config_path: "Chemin de la config",
    config_bridge_devices_config_path_hint:
      "Chemin distant vers le fichier devices.yaml de Zigbee2MQTT",

    // Maintenance
    maint_danger_zone: "Zone de Danger",
    maint_danger_desc:
      "Ces opérations sont irréversibles. Procédez avec prudence.",
    maint_clean_db: "Nettoyer la Base",
    maint_clean_db_desc:
      "Supprimer toutes les données (devices, pièces, étages, bâtiments, modèles, firmwares, fonctions).",
    maint_confirm_title: "Confirmer la suppression",
    maint_confirm_desc:
      "Cette action supprimera DÉFINITIVEMENT toutes les données. Saisissez la phrase ci-dessous pour confirmer :",
    maint_confirm_placeholder: "Saisissez la phrase de confirmation...",
    maint_confirm_execute: "Tout Supprimer",
    maint_clean_success: "Base de données nettoyée",
    maint_rows_deleted: "lignes supprimées",
    maint_scan_network: "Scanner le Réseau",
    maint_scan_network_desc:
      "Scanne le réseau pour découvrir les équipements connectés et mettre à jour les adresses IP.",
    maint_scan_triggered: "Scan terminé",
    maint_scan_running: "Scan en cours...",
    maint_scan_stat_total: "Total équipements",
    maint_scan_stat_mapped: "Mappés (IP trouvée)",
    maint_scan_stat_not_found: "Non trouvés",
    maint_scan_stat_errors: "Erreurs",
    maint_scan_stat_error_details: "Détails des erreurs",
    maint_clear_ip_cache: "Vider le Cache IP",
    maint_clear_ip_cache_desc:
      "Réinitialise l'adresse IP de tous les équipements à NULL. Utile après un changement de réseau.",
    maint_clear_ip_cache_success: "Cache IP effacé",
    maint_clear_ip_updated: "équipements mis à jour",

    // Common
    name: "Nom",
    slug: "Slug",
    description: "Description",
    image: "Image",
    save: "Enregistrer",
    cancel: "Annuler",
    reset: "Réinitialiser",
    delete: "Supprimer",
    edit: "Modifier",
    add: "Ajouter",
    close: "Fermer",
    confirm: "Confirmer",
    loading: "Chargement...",
    error_loading: "Erreur lors du chargement",
    error_saving: "Erreur lors de l'enregistrement",
    error_deleting: "Erreur lors de la suppression",
    confirm_delete: "Êtes-vous sûr de vouloir supprimer cet élément ?",
    confirm_delete_cascade:
      "Cela supprimera aussi tous les éléments enfants. Continuer ?",
    success_created: "Créé avec succès",
    success_updated: "Mis à jour avec succès",
    success_deleted: "Supprimé avec succès",
    previous: "Précédent",
    next: "Suivant",
    reload: "Recharger",
    search: "Rechercher",
    filter_devices: "Filtrer les équipements",
    clear_filter: "Effacer le filtre",
    clear_all_filters: "Effacer les filtres",
    col_filter_select_all: "Tout",
    col_filter_clear_col: "Aucun",
    col_filter_title: "Filtrer la colonne",
    col_filter_search: "Rechercher parmi les valeurs...",
    col_filter_no_results: "Aucune valeur correspondante",
    filter_link_copied: "Lien copié !",
    filter_share: "Copier le lien filtré",
    actions: "Actions",
    id: "ID",
    no_items: "Aucun élément.",
    created_at: "Créé le",
    updated_at: "Mis à jour le",
    view_in_devices: "Voir dans Équipements",
    validation_name_required: "Le nom est requis",
    validation_slug_required: "Le slug est requis",
    validation_slug_format:
      "Le slug doit contenir uniquement des lettres, chiffres, tirets et underscores",
    validation_url_format: "L'image doit être une URL http/https valide",

    // HA Groups
    ha_groups_sync: "Synchroniser les groupes HA",
    ha_groups_syncing: "Synchronisation des groupes…",
    ha_groups_sync_success:
      "{count} groupe(s) synchronisé(s) dans Home Assistant",
    ha_groups_sync_none:
      "Aucun groupe à synchroniser (aucun appareil avec une fonction assignée)",
    ha_groups_sync_error: "Impossible de synchroniser les groupes HA",
    config_ha_groups_section: "Synchronisation des groupes HA",
    config_ha_groups_empty_groups: "Créer des groupes vides",
    config_ha_groups_empty_groups_hint:
      "Si activé, les groupes sont créés même si aucune entité HA correspondante n’est enregistrée pour les appareils de la pièce.",
    // HA Floors
    ha_floors_sync: "Synchroniser les étages HA",
    ha_floors_syncing: "Synchronisation des étages…",
    ha_floors_sync_success:
      "{count} étage(s) synchronisé(s) dans Home Assistant",
    ha_floors_sync_none: "Aucun étage à synchroniser",
    ha_floors_sync_error: "Impossible de synchroniser les étages HA",
    // HA Rooms
    ha_rooms_sync: "Synchroniser les pièces HA",
    ha_rooms_syncing: "Synchronisation des pièces\u2026",
    ha_rooms_sync_success:
      "{count} pièce(s) synchronisée(s) dans Home Assistant",
    ha_rooms_sync_none: "Aucune pièce à synchroniser",
    ha_rooms_sync_error: "Impossible de synchroniser les pièces HA",

    // Activity Log
    activity_log_date_from: "Du",
    activity_log_date_to: "Au",
    activity_log_event_type: "Type d'événement",
    activity_log_config_change: "Changement config",
    activity_log_action: "Action",
    activity_log_entity_type: "Type d'entité",
    activity_log_user_col: "Utilisateur",
    activity_log_severity: "Sévérité",
    activity_log_severity_info: "Info",
    activity_log_severity_warning: "Avertissement",
    activity_log_severity_error: "Erreur",
    activity_log_apply_filters: "Appliquer",
    activity_log_reset_filters: "Réinitialiser",
    activity_log_empty: "Aucune entrée dans le journal d'activité.",
    activity_log_col_timestamp: "Horodatage",
    activity_log_col_user: "Utilisateur",
    activity_log_col_type: "Type",
    activity_log_col_entity: "Entité",
    activity_log_col_severity: "Sévérité",
    activity_log_col_message: "Message",
    activity_log_click_expand: "Cliquez pour développer les détails",
    activity_log_result: "Résultat",
    activity_log_total: "Total des entrées",
    activity_log_purge_title: "Purger les anciennes entrées",
    activity_log_purge_label:
      "Supprimer les entrées plus anciennes que (jours) :",
    activity_log_purge_btn: "Purger",
    activity_log_purge_success: "Entrées supprimées",
  },
};

class I18n {
  private currentLang: string;

  constructor() {
    const browserLang = navigator.language.toLowerCase().split("-")[0];
    this.currentLang = translations[browserLang] ? browserLang : "en";
  }

  /**
   * Translate a key to the current language.
   *
   * @param key - The translation key.
   * @returns The translated string or the key itself if not found.
   */
  t(key: string): string {
    return (
      translations[this.currentLang]?.[key] ?? translations["en"]?.[key] ?? key
    );
  }

  /**
   * Set the current language and notify all subscribers.
   *
   * @param lang - The language code (e.g. 'en', 'fr').
   */
  setLanguage(lang: string): void {
    if (translations[lang] && lang !== this.currentLang) {
      this.currentLang = lang;
      window.dispatchEvent(new CustomEvent("lang-changed", { detail: lang }));
    }
  }

  /**
   * Get the current language code.
   */
  getCurrentLanguage(): string {
    return this.currentLang;
  }
}

export const i18n = new I18n();

/**
 * Class decorator that triggers a re-render when the language changes.
 *
 * Usage: add `@localized` before `@customElement(...)` on any LitElement class.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function localized(constructor: any): void {
  const origConnected = constructor.prototype.connectedCallback;
  const origDisconnected = constructor.prototype.disconnectedCallback;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor.prototype.connectedCallback = function (this: any) {
    origConnected?.call(this);
    this.__langHandler = () => this.requestUpdate();
    window.addEventListener("lang-changed", this.__langHandler);
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor.prototype.disconnectedCallback = function (this: any) {
    if (this.__langHandler) {
      window.removeEventListener("lang-changed", this.__langHandler);
    }
    origDisconnected?.call(this);
  };
}
