#!/bin/bash

# === CONFIGURATION ===
BACKUP_DIR=./docker_backups
VOLUMES=("oda_influxdbconfig" "oda_influxdbdata" "oda_topiclist")
DATE=$(date +%Y-%m-%d_%H-%M-%S)
DEST_DIR="${BACKUP_DIR}/${DATE}"

# === CREATE BACKUP DIRECTORY ===
mkdir -p "$DEST_DIR"

# === BACKUP EACH VOLUME ===
for VOLUME in "${VOLUMES[@]}"; do
    echo "Backing up volume: $VOLUME"
    docker run --rm \
        -v ${VOLUME}:/volume \
        -v ${DEST_DIR}:/backup \
        alpine \
        sh -c "tar czf /backup/${VOLUME}.tar.gz -C /volume ."
done

echo "✅ Backup complete. Files are saved in: $DEST_DIR"
