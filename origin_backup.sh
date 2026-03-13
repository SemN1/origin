#!/bin/bash
# ============================================================
# Origin Backup Script
# Backup completo dello stato di Adam/Origin su GitHub e server
# Gira ogni notte alle 03:00 via cron
# ============================================================

set -e

ORIGIN_DIR="/home/semn1/origin"
BACKUP_DIR="/data/backups/secretary-chat"
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M')
TELEGRAM_TOKEN=$(grep TELEGRAM_BOT_TOKEN /home/semn1/origin/.env | cut -d'=' -f2)
TELEGRAM_CHAT_ID="2560082"
GITHUB_TOKEN=$(grep GITHUB_TOKEN /home/semn1/origin/.env | cut -d'=' -f2)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

send_telegram() {
    local msg="$1"
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=${msg}" \
        -d "parse_mode=Markdown" > /dev/null 2>&1
}

# ============================================================
# STEP 1 — Genera snapshot stato sistema
# ============================================================
log "Generazione snapshot sistema..."

mkdir -p "$BACKUP_DIR"

SNAPSHOT_FILE="$BACKUP_DIR/origin_snapshot_${TIMESTAMP}.md"

cat > "$SNAPSHOT_FILE" << EOF
# Origin Snapshot — ${TIMESTAMP}
**Adam** | Agente Segretario di Sem

## Identità
- Progetto: Origin
- Agente: Adam
- Proprietario: Sem (Simone)
- Server: semn1 / 192.168.1.13
- GitHub: https://github.com/SemN1/origin

## Progetti Attivi
EOF

# Leggi stato progetti da PostgreSQL
PGPASSWORD='1' psql -U agent_system -d agent_hub -h localhost -t -A -F'|' << 'SQLEOF' >> "$SNAPSHOT_FILE" 2>/dev/null || echo "DB non raggiungibile" >> "$SNAPSHOT_FILE"
SELECT '- **' || project_name || '** (' || project_id || '): ' || status || ' — ' || COALESCE(current_phase, 'N/A')
FROM project_status
ORDER BY status, project_name;
SQLEOF

cat >> "$SNAPSHOT_FILE" << EOF

## Repo GitHub per Progetto
- Origin (infrastruttura): https://github.com/SemN1/origin
- Beauty Salon DB: https://github.com/SemN1/beauty-salon-db
- Ollama Lab: https://github.com/SemN1/ollama-lab
- CRM Personale: https://github.com/SemN1/crm-personale
- Personal RAG: https://github.com/SemN1/personal-rag

## Architettura Core
- Server: Ubuntu 24, GTX 1080 8GB, 32GB RAM
- Stack: Docker, n8n, PostgreSQL, ChromaDB, Ollama
- Telegram Bot: SemnMasterBot
- Backup: GitHub (origin) + /data/backups/secretary-chat/ + PC Windows

## Regole Sistema
1. Ogni progetto ha repo GitHub dedicato
2. Ogni chat di progetto carica PROJECT_BOOTSTRAP.md all'avvio
3. STATUS.md aggiornato daily da ogni agente
4. n8n legge GitHub ogni 6h → aggiorna PostgreSQL project_status
5. Adam ha accesso a tutti i repo e risponde via Telegram
6. Quando Origin si avvicina al limite contesto → backup + nuova chat

## Cron Jobs Attivi
- */15 * * * * aggiorna_status.sh (voice)
- */30 * * * * aggiorna_status.sh (status)
- 0 1,12,20 * * * telegram_library_bot.py
- 30 1 * * * backup_to_pc.sh
- 0 2 * * * cleanup status_updates_voice
- 0 3 * * * origin/auto_backup.sh (questo script)
- 0 */8 * * * beauty-salon-db/update_docs.sh

## Note Importanti
- Questa è la chat originale — il punto zero di tutto
- La chat successiva di Adam deve leggere questo file e continuare
- DB n8n: PostgreSQL (già configurato)
- Tutte le credenziali in /home/semn1/origin/.env
EOF

log "Snapshot generato: $SNAPSHOT_FILE"

# ============================================================
# STEP 2 — Copia snapshot in origin repo
# ============================================================
log "Push su GitHub origin..."

cp "$SNAPSHOT_FILE" "$ORIGIN_DIR/secretary-backup/latest_snapshot.md"
mkdir -p "$ORIGIN_DIR/secretary-backup/history"
cp "$SNAPSHOT_FILE" "$ORIGIN_DIR/secretary-backup/history/snapshot_${TIMESTAMP}.md"

cd "$ORIGIN_DIR"
git add secretary-backup/
git commit -m "Auto-backup Origin snapshot ${TIMESTAMP}" --allow-empty
git push origin main

log "Push GitHub completato"

# ============================================================
# STEP 3 — Pulizia backup locali (tieni ultimi 30 giorni)
# ============================================================
find "$BACKUP_DIR" -name "origin_snapshot_*.md" -mtime +30 -delete
log "Pulizia backup vecchi completata"

# ============================================================
# STEP 4 — Notifica Telegram
# ============================================================
PROJECTS_COUNT=$(PGPASSWORD='1' psql -U agent_system -d agent_hub -h localhost -t -c "SELECT COUNT(*) FROM project_status;" 2>/dev/null | tr -d ' ' || echo "?")

send_telegram "✅ *Origin Backup Completato*
📅 ${TIMESTAMP}
📦 Snapshot salvato su GitHub e server
📊 ${PROJECTS_COUNT} progetti nel sistema
🔗 github.com/SemN1/origin"

log "Backup Origin completato con successo"
exit 0
