#!/usr/bin/env python3
"""
SemnMasterBot - Telegram Bot per Agent System v2.0
Comandi: /status, /report, /costs, /help, /ask
"""
import requests
import psycopg2
import time
import os
import sys
from datetime import datetime

import os; TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = [2560082]
DB_CONN = "postgresql://agent_system:1@localhost:5432/agent_hub"
API = f"https://api.telegram.org/bot{TOKEN}"

# Carica CLAUDE_API_KEY da .env se non è già in ambiente
def load_env():
    env_path = os.path.expanduser("~/agent-system/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip()

load_env()

def send(chat_id, text):
    try:
        requests.post(f"{API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        print(f"Errore invio messaggio: {e}")

def query_db(sql):
    conn = psycopg2.connect(DB_CONN)
    cur = conn.cursor()
    cur.execute(sql)
    row = cur.fetchone()
    cols = [d[0] for d in cur.description]
    cur.close()
    conn.close()
    return dict(zip(cols, row)) if row else {}

def ask_claude(question: str) -> str:
    """Chiama Claude Haiku per rispondere a domande"""
    api_key = os.environ.get("CLAUDE_API_KEY")
    if not api_key or api_key == "INSERISCI_QUI_LA_TUA_API_KEY":
        return "❌ Claude API key non configurata."

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "system": "Sei SemnMasterBot, l'assistente AI del sistema Agent System v2.0 di Simone. Rispondi in italiano, in modo conciso e utile.",
                "messages": [{"role": "user", "content": question}]
            },
            timeout=30
        )
        result = response.json()
        content = result.get("content", [])
        return content[0].get("text", "Nessuna risposta") if content else "Nessuna risposta"
    except Exception as e:
        return f"❌ Errore Claude API: {e}"

def handle(command, args, user_id):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    if command == "/status":
        d = query_db("""
            SELECT
              (SELECT COUNT(*) FROM projects WHERE status='active') as active_projects,
              (SELECT COUNT(*) FROM projects) as total_projects,
              (SELECT COUNT(*) FROM workflows WHERE status='active') as active_workflows,
              (SELECT COUNT(*) FROM execution_logs WHERE started_at>=CURRENT_DATE) as jobs_today,
              (SELECT COUNT(*) FROM execution_logs WHERE started_at>=CURRENT_DATE AND status='success') as success_today,
              (SELECT COUNT(*) FROM execution_logs WHERE started_at>=CURRENT_DATE AND status='error') as errors_today
        """)
        rate = round((d['success_today']/d['jobs_today'])*100) if d['jobs_today'] > 0 else 100
        send(user_id, f"🖥️ *SYSTEM STATUS*\n🕐 {now}\n\n📦 *Progetti*\n✅ Attivi: {d['active_projects']}\n📊 Totali: {d['total_projects']}\n⚙️ Workflow attivi: {d['active_workflows']}\n\n🔄 *Esecuzioni Oggi*\n✅ Successi: {d['success_today']}\n❌ Errori: {d['errors_today']}\n📈 Success rate: {rate}%\n\n🟢 Sistema operativo")

    elif command == "/report":
        d = query_db("""
            SELECT
              (SELECT COUNT(*) FROM projects WHERE status='active') as active_projects,
              (SELECT COUNT(*) FROM execution_logs WHERE started_at>=CURRENT_DATE) as jobs_today,
              (SELECT COUNT(*) FROM execution_logs WHERE started_at>=CURRENT_DATE AND status='success') as success_today,
              (SELECT COUNT(*) FROM execution_logs WHERE started_at>=CURRENT_DATE AND status='error') as errors_today,
              COALESCE((SELECT SUM(cost_eur) FROM cost_tracking WHERE date>=CURRENT_DATE),0) as cost_today,
              COALESCE((SELECT SUM(cost_eur) FROM cost_tracking WHERE date>=DATE_TRUNC('month',CURRENT_DATE)),0) as cost_month
        """)
        rate = round((d['success_today']/d['jobs_today'])*100) if d['jobs_today'] > 0 else 100
        send(user_id, f"📊 *REPORT ON-DEMAND*\n📅 {now}\n\n🏗️ Progetti Attivi: {d['active_projects']}\n\n⚡ *Esecuzioni Oggi*\n• Totali: {d['jobs_today']}\n• ✅ Successi: {d['success_today']}\n• ❌ Errori: {d['errors_today']}\n• 📈 Rate: {rate}%\n\n💰 *Costi Claude API*\n• Oggi: €{float(d['cost_today']):.4f}\n• Mese: €{float(d['cost_month']):.2f}")

    elif command == "/costs":
        d = query_db("""
            SELECT
              COALESCE(SUM(cost_eur),0) as total_month,
              COALESCE(SUM(cost_eur) FILTER (WHERE date>=CURRENT_DATE),0) as total_today,
              COUNT(*) as total_calls
            FROM cost_tracking WHERE provider='claude'
            AND date>=DATE_TRUNC('month',CURRENT_DATE)
        """)
        spent = float(d['total_month'])
        pct = (spent/50)*100
        emoji = '🔴' if spent>=40 else ('🟡' if spent>=30 else '🟢')
        send(user_id, f"💰 *COSTI CLAUDE API*\n{emoji} Budget usato: {pct:.1f}%\n\n• Spesa mese: €{spent:.4f}\n• Budget limite: €50.00\n• Chiamate: {d['total_calls']}\n• Oggi: €{float(d['total_today']):.4f}")

    elif command == "/ask":
        if not args:
            send(user_id, "❓ Uso: /ask <domanda>\n\nEsempio: /ask Come ottimizzare una query SQL?")
            return
        question = args
        send(user_id, "🤔 Sto chiedendo a Claude...")
        answer = ask_claude(question)
        send(user_id, f"🤖 *Claude risponde:*\n\n{answer}")

    elif command == "/help":
        send(user_id, "🤖 *SEMNMASTERBOT - COMANDI*\n\n/status — Stato sistema in tempo reale\n/report — Report completo on-demand\n/costs — Costi Claude API del mese\n/ask <domanda> — Chiedi qualcosa a Claude\n/help — Questo messaggio\n\n_Agent System v2.0 — semn1_")

    else:
        send(user_id, f"❓ Comando non riconosciuto: {command}\n\nUsa /help per i comandi disponibili.")

def main():
    offset = 0
    print("🤖 SemnMasterBot avviato")
    while True:
        try:
            r = requests.get(
                f"{API}/getUpdates",
                params={"offset": offset, "timeout": 10},
                timeout=15
            )
            data = r.json()
            if data.get("ok") and data["result"]:
                for update in data["result"]:
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    if not msg or not msg.get("text"):
                        continue
                    user_id = msg["from"]["id"]
                    if user_id not in ALLOWED_USERS:
                        continue
                    raw = msg["text"].strip()
                    parts = raw.split(None, 1)
                    command = parts[0].lower().split("@")[0]
                    args = parts[1] if len(parts) > 1 else ""
                    handle(command, args, user_id)
        except Exception as e:
            print(f"Errore: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
