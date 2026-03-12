#!/bin/bash
cd ~/agent-system
cp /data/shared/scripts/telegram_bot.py .
cp /data/shared/scripts/ollama_client.py .
cp /data/shared/scripts/claude_client.py .
cp /data/shared/scripts/chromadb_manager.py .
if ! git diff --quiet || ! git diff --cached --quiet; then
    git add -A
    git commit -m "Auto backup - $(date '+%Y-%m-%d %H:%M')"
    git push
    echo "Backup completato - $(date)"
else
    echo "Nessuna modifica - $(date)"
fi
