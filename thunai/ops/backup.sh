#!/bin/sh
# Nightly PostgreSQL backup (custom format, restorable with pg_restore).
# Runs once at start, then every day at BACKUP_HOUR (plant time). Keeps BACKUP_KEEP_DAYS days.
set -eu
: "${BACKUP_HOUR:=2}"
: "${BACKUP_KEEP_DAYS:=14}"
mkdir -p /backups

backup() {
  file="/backups/thunai-$(date +%Y%m%d-%H%M).dump"
  if pg_dump -Fc -f "$file.part"; then
    mv "$file.part" "$file"
    echo "$(date -Iseconds) backup written: $file ($(du -h "$file" | cut -f1))"
  else
    rm -f "$file.part"
    echo "$(date -Iseconds) BACKUP FAILED" >&2
  fi
  find /backups -name 'thunai-*.dump' -mtime +"$BACKUP_KEEP_DAYS" -delete
}

backup
while true; do
  now=$(date +%s)
  next=$(date -d "$(date +%Y-%m-%d) ${BACKUP_HOUR}:00" +%s)
  [ "$next" -le "$now" ] && next=$((next + 86400))
  sleep $((next - now))
  backup
done
