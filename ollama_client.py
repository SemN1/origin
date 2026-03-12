#!/usr/bin/env python3
"""
Ollama Client - Interface per modelli LLM locali
Version: 2.0
Usage: 
    - Importa in altri script: from ollama_client import OllamaClient
    - Usa standalone: python ollama_client.py --test
"""

import os
import sys
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime


class OllamaClient:
    """Client per interfacciarsi con Ollama locale"""
    
    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = None,
        temperature: float = 0.7
    ):
        """
        Inizializza client Ollama
        
        Args:
            host: URL del server Ollama (default: container name in Docker network)
            model: Nome modello (default: da variabile ambiente OLLAMA_MODEL)
            temperature: Creatività risposta (0.0-1.0)
        """
        self.host = host
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.temperature = temperature
        
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Genera risposta da prompt
        
        Args:
            prompt: Prompt utente
            system: System prompt (opzionale)
            max_tokens: Max token output
            temperature: Override temperature default
            stream: Stream response (default: False)
            
        Returns:
            Dict con 'response', 'total_duration', 'prompt_eval_count', 'eval_count'
        """
        url = f"{self.host}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
                "num_predict": max_tokens
            }
        }
        
        if system:
            payload["system"] = system
            
        try:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            
            if stream:
                # Per streaming, ritorna generator
                return self._handle_stream(response)
            else:
                result = response.json()
                return {
                    "response": result.get("response", ""),
                    "total_duration_ms": result.get("total_duration", 0) // 1_000_000,
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "output_tokens": result.get("eval_count", 0),
                    "model": self.model
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "response": "",
                "total_duration_ms": 0,
                "prompt_tokens": 0,
                "output_tokens": 0
            }
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Chat multi-turno
        
        Args:
            messages: Lista di {"role": "user/assistant/system", "content": "..."}
            max_tokens: Max token output
            temperature: Override temperature
            
        Returns:
            Dict con response e metadata
        """
        url = f"{self.host}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            
            return {
                "response": result.get("message", {}).get("content", ""),
                "total_duration_ms": result.get("total_duration", 0) // 1_000_000,
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "output_tokens": result.get("eval_count", 0),
                "model": self.model
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "response": "",
                "total_duration_ms": 0,
                "prompt_tokens": 0,
                "output_tokens": 0
            }
    
    def summarize_log(
        self,
        log_text: str,
        max_length: int = 200
    ) -> str:
        """
        Riassumi log/errore tecnico
        
        Args:
            log_text: Testo log completo
            max_length: Lunghezza max summary (in parole)
            
        Returns:
            Summary conciso
        """
        system = (
            "Sei un assistente tecnico. Riassumi log ed errori in modo conciso, "
            "evidenziando la causa principale e i passi per risolvere."
        )
        
        prompt = f"""Riassumi questo log in massimo {max_length} parole:

```
{log_text[:2000]}  # Tronca log troppo lunghi
```

Rispondi SOLO con il riassunto, senza preamble."""
        
        result = self.generate(prompt, system=system, max_tokens=300, temperature=0.3)
        return result.get("response", "Errore: impossibile generare summary")
    
    def categorize_email(
        self,
        subject: str,
        body: str,
        categories: List[str] = None
    ) -> Dict[str, Any]:
        """
        Categorizza email
        
        Args:
            subject: Oggetto email
            body: Corpo email
            categories: Lista categorie possibili (default: client, prospect, vendor, spam, other)
            
        Returns:
            Dict con 'category', 'confidence', 'reasoning'
        """
        if categories is None:
            categories = ["client", "prospect", "vendor", "spam", "other"]
            
        system = (
            "Sei un assistente che categorizza email. Rispondi SOLO in formato JSON "
            "con i campi: category, confidence (0.0-1.0), reasoning."
        )
        
        prompt = f"""Categorizza questa email in una delle seguenti categorie: {', '.join(categories)}

Oggetto: {subject}
Corpo: {body[:500]}

Rispondi in JSON:
```json
{{
  "category": "...",
  "confidence": 0.0,
  "reasoning": "..."
}}
```"""
        
        result = self.generate(prompt, system=system, max_tokens=200, temperature=0.1)
        
        try:
            # Estrai JSON dalla risposta
            response_text = result.get("response", "{}")
            # Rimuovi markdown fences se presenti
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            categorization = json.loads(response_text)
            return categorization
        except json.JSONDecodeError:
            return {
                "category": "other",
                "confidence": 0.0,
                "reasoning": "Errore parsing risposta modello"
            }
    
    def extract_entities(
        self,
        text: str,
        entity_types: List[str] = None
    ) -> List[Dict[str, str]]:
        """
        Estrai entità da testo (NER)
        
        Args:
            text: Testo input
            entity_types: Tipi di entità da estrarre (default: person, org, location, date, phone, email)
            
        Returns:
            Lista di {"type": "...", "value": "...", "context": "..."}
        """
        if entity_types is None:
            entity_types = ["person", "org", "location", "date", "phone", "email"]
            
        system = (
            "Sei un assistente NER (Named Entity Recognition). Estrai entità dal testo. "
            "Rispondi SOLO in formato JSON array."
        )
        
        prompt = f"""Estrai queste entità dal testo: {', '.join(entity_types)}

Testo:
{text[:1000]}

Rispondi in JSON array:
```json
[
  {{"type": "person", "value": "Mario Rossi", "context": "ha inviato email"}},
  ...
]
```"""
        
        result = self.generate(prompt, system=system, max_tokens=500, temperature=0.1)
        
        try:
            response_text = result.get("response", "[]")
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            entities = json.loads(response_text)
            return entities if isinstance(entities, list) else []
        except json.JSONDecodeError:
            return []
    
    def generate_report(
        self,
        data: Dict[str, Any],
        report_type: str = "daily"
    ) -> str:
        """
        Genera report testuale da dati strutturati
        
        Args:
            data: Dati da includere nel report (dict con metriche)
            report_type: Tipo report (daily, weekly, monthly, benchmark)
            
        Returns:
            Report in formato Markdown
        """
        system = (
            "Sei un assistente che genera report tecnici chiari e concisi in Markdown. "
            "Usa emoji per rendere leggibile, ma mantieni tono professionale."
        )
        
        prompt = f"""Genera un report {report_type} basato su questi dati:

```json
{json.dumps(data, indent=2, ensure_ascii=False)}
```

Il report deve includere:
1. Summary esecutivo (2-3 righe)
2. Metriche chiave
3. Trend (se applicabile)
4. Raccomandazioni (se ci sono anomalie)

Formato: Markdown con emoji."""
        
        result = self.generate(prompt, system=system, max_tokens=800, temperature=0.4)
        return result.get("response", "Errore: impossibile generare report")
    
    def answer_question(
        self,
        question: str,
        context: str = "",
        max_tokens: int = 500
    ) -> str:
        """
        Rispondi a domanda con RAG-style (question + context)
        
        Args:
            question: Domanda utente
            context: Contesto da cui estrarre risposta
            max_tokens: Max token risposta
            
        Returns:
            Risposta alla domanda
        """
        if context:
            system = (
                "Sei un assistente che risponde a domande basandoti SOLO sul contesto fornito. "
                "Se la risposta non è nel contesto, dì 'Non ho informazioni sufficienti'."
            )
            prompt = f"""Contesto:
{context[:3000]}

Domanda: {question}

Rispondi in modo conciso basandoti solo sul contesto."""
        else:
            system = "Sei un assistente tecnico che fornisce risposte precise e concise."
            prompt = question
            
        result = self.generate(prompt, system=system, max_tokens=max_tokens, temperature=0.3)
        return result.get("response", "Errore: impossibile generare risposta")
    
    def list_models(self) -> List[str]:
        """
        Lista modelli disponibili su Ollama
        
        Returns:
            Lista nomi modelli
        """
        url = f"{self.host}/api/tags"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            models = [m.get("name") for m in result.get("models", [])]
            return models
            
        except requests.exceptions.RequestException as e:
            print(f"Errore connessione Ollama: {e}", file=sys.stderr)
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """
        Scarica un nuovo modello
        
        Args:
            model_name: Nome modello (es. 'llama3.2:latest')
            
        Returns:
            True se successo, False altrimenti
        """
        url = f"{self.host}/api/pull"
        payload = {"name": model_name}
        
        try:
            response = requests.post(url, json=payload, stream=True, timeout=600)
            response.raise_for_status()
            
            # Mostra progress
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    print(f"\r{status}", end="", flush=True)
                    
            print("\n✅ Download completato")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Errore download: {e}", file=sys.stderr)
            return False
    
    def _handle_stream(self, response):
        """Helper per gestire streaming response"""
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                yield chunk.get("response", "")


# ============================================================
# Funzioni Standalone (per chiamata diretta da n8n)
# ============================================================

def summarize_log_standalone(log_text: str) -> Dict[str, Any]:
    """
    Funzione standalone per summarize_log (chiamabile da n8n Execute Command)
    
    Returns:
        JSON con summary e metadata
    """
    client = OllamaClient()
    summary = client.summarize_log(log_text)
    
    return {
        "summary": summary,
        "timestamp": datetime.now().isoformat(),
        "model": client.model
    }


def categorize_email_standalone(subject: str, body: str) -> Dict[str, Any]:
    """
    Funzione standalone per categorize_email
    
    Returns:
        JSON con category, confidence, reasoning
    """
    client = OllamaClient()
    result = client.categorize_email(subject, body)
    result["timestamp"] = datetime.now().isoformat()
    return result


def generate_report_standalone(data_json: str, report_type: str = "daily") -> Dict[str, Any]:
    """
    Funzione standalone per generate_report
    
    Args:
        data_json: Dati in formato JSON string
        report_type: Tipo report
        
    Returns:
        JSON con report markdown e metadata
    """
    client = OllamaClient()
    
    try:
        data = json.loads(data_json)
    except json.JSONDecodeError:
        return {
            "error": "Invalid JSON input",
            "report": "",
            "timestamp": datetime.now().isoformat()
        }
    
    report = client.generate_report(data, report_type)
    
    return {
        "report": report,
        "report_type": report_type,
        "timestamp": datetime.now().isoformat(),
        "model": client.model
    }


# ============================================================
# CLI Interface
# ============================================================

def main():
    """Entry point per uso CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ollama Client CLI")
    parser.add_argument("--test", action="store_true", help="Esegui test connessione")
    parser.add_argument("--list", action="store_true", help="Lista modelli disponibili")
    parser.add_argument("--pull", type=str, metavar="MODEL", help="Scarica modello")
    parser.add_argument("--prompt", type=str, help="Invia prompt e ricevi risposta")
    parser.add_argument("--summarize", type=str, metavar="TEXT", help="Riassumi testo")
    parser.add_argument("--model", type=str, help="Override modello default")
    
    args = parser.parse_args()
    
    # Inizializza client
    client = OllamaClient(model=args.model) if args.model else OllamaClient()
    
    if args.test:
        print("🧪 Test connessione Ollama...")
        result = client.generate("Rispondi con 'OK' se mi ricevi.", max_tokens=10)
        if result.get("error"):
            print(f"❌ Errore: {result['error']}")
            sys.exit(1)
        else:
            print(f"✅ Connessione OK")
            print(f"   Modello: {result['model']}")
            print(f"   Risposta: {result['response']}")
            print(f"   Latenza: {result['total_duration_ms']}ms")
            sys.exit(0)
    
    elif args.list:
        print("📋 Modelli disponibili su Ollama:")
        models = client.list_models()
        for i, model in enumerate(models, 1):
            marker = "⭐" if model == client.model else "  "
            print(f"{marker} {i}. {model}")
        sys.exit(0)
    
    elif args.pull:
        print(f"📥 Download modello: {args.pull}")
        success = client.pull_model(args.pull)
        sys.exit(0 if success else 1)
    
    elif args.prompt:
        print(f"💬 Invio prompt a {client.model}...")
        result = client.generate(args.prompt)
        if result.get("error"):
            print(f"❌ Errore: {result['error']}")
            sys.exit(1)
        else:
            print(f"\n{result['response']}\n")
            print(f"⏱️  {result['total_duration_ms']}ms | "
                  f"📥 {result['prompt_tokens']} tok | "
                  f"📤 {result['output_tokens']} tok")
            sys.exit(0)
    
    elif args.summarize:
        print(f"📝 Generazione summary...")
        summary = client.summarize_log(args.summarize)
        print(f"\n{summary}\n")
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
