#!/bin/bash

# Local directories to sync
LOCAL_DIR="/mnt/c/Users/tbrow/dev/pyguibank/dist/plugins"

# Remote server details
REMOTE_USER="tbrownhe"
REMOTE_HOST="192.168.1.53"
REMOTE_DIR="/srv/pyguibank-server/resources/"

echo ''
rsync -avz --progress --chmod=F640,D755 "$LOCAL_DIR" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"

echo "Sync complete!"
