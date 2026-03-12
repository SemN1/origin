# Origin Snapshot — 2026-03-12_23-03
**Adam** | Agente Segretario di Sem

## Identità
- Progetto: Origin
- Agente: Adam
- Proprietario: Sem (Simone)
- Server: semn1 / 192.168.1.13
- GitHub: https://github.com/SemN1/origin

## Progetti Attivi

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
