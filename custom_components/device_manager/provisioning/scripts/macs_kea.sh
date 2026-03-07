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
