#!/bin/bash

# === CONFIGURATION ===
BACKUP_DIR=$1  # e.g. ./docker_backups/2025-06-04_12-00-00
VOLUMES=("oda_influxdbconfig" "oda_influxdbdata" "oda_topiclist")

if [ -z "$BACKUP_DIR" ]; then
    echo "❌ Usage: $0 /path/to/backup_dir"
    exit 1
fi

# === CHECK IF DIRECTORY EXISTS ===
if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory does not exist: $BACKUP_DIR"
    exit 1
fi

# === RESTORE EACH VOLUME ===
for VOLUME in "${VOLUMES[@]}"; do
    BACKUP_FILE="${BACKUP_DIR}/${VOLUME}.tar.gz"

    if [ ! -f "$BACKUP_FILE" ]; then
        echo "⚠️ Backup file not found: $BACKUP_FILE — skipping."
        continue
    fi

    echo "🔄 Restoring volume: $VOLUME"

    # Create volume if it doesn't exist
    docker volume inspect "$VOLUME" >/dev/null 2>&1 || docker volume create "$VOLUME"

    # Restore contents from tar.gz archive
    docker run --rm \
        -v ${VOLUME}:/volume \
        -v ${BACKUP_DIR}:/backup \
        alpine \
        sh -c "rm -rf /volume/* && tar xzf /backup/${VOLUME}.tar.gz -C /volume"

    echo "✅ Restored $VOLUME"
done

echo "🎉 Restore complete!"
