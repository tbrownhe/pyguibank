#!/bin/bash

# Local directories to sync
LOCAL_DIR="../dist/macos"

# Remote server details
REMOTE_USER="tbrownhe"
REMOTE_HOST="192.168.1.53"
REMOTE_DIR="/srv/pyguibank-server/resources/clients/"

echo ''
rsync -avz --progress "$LOCAL_DIR" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"

echo "Sync complete!"
