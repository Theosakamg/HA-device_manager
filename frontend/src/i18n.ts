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
    nav_hierarchy: "Hierarchy",
    nav_devices: "All Devices",
    nav_map: "Map",
    nav_settings: "Settings",
    nav_maintenance: "Maintenance",
    map_loading: "Loading 3D map…",
    filter_all: "All",

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

    // Devices
    devices_list: "Devices",
    device: "Device",
    devices: "Devices",
    add_device: "Add Device",
    edit_device: "Edit Device",
    device_mac: "MAC Address",
    device_ip: "IP Address",
    device_enabled: "Enabled",
    device_level: "Floor",
    device_position_name: "Position Name",
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

    // Deploy
    deploy: "Deploy",
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
  },
  fr: {
    // Navigation
    app_title: "Gestionnaire d'Équipements",
    nav_hierarchy: "Hiérarchie",
    nav_devices: "Tous les Équipements",
    nav_map: "Map",
    nav_settings: "Paramètres",
    nav_maintenance: "Maintenance",
    map_loading: "Chargement de la carte 3D…",
    filter_all: "Tous",

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

    // Devices
    devices_list: "Équipements",
    device: "Équipement",
    devices: "Équipements",
    add_device: "Ajouter un Équipement",
    edit_device: "Modifier l'Équipement",
    device_mac: "Adresse MAC",
    device_ip: "Adresse IP",
    device_enabled: "Activé",
    device_level: "Étage",
    device_position_name: "Nom de Position",
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

    // Deploy
    deploy: "Déployer",
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
