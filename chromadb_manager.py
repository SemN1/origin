#!/usr/bin/env python3
"""
ChromaDB Manager - Gestione vector store per RAG e Knowledge Base
Version: 2.0
Usage:
    - Importa: from chromadb_manager import ChromaManager
    - CLI: python chromadb_manager.py --init-kb
"""

import os
import sys
import json
import hashlib
import chromadb

from typing import List, Dict, Optional, Any
from datetime import datetime


class ChromaManager:
    """Manager per ChromaDB - RAG e Knowledge Base"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        auth_token: str = None
    ):
        """
        Inizializza ChromaDB client
        
        Args:
            host: Hostname ChromaDB (default: container name)
            port: Porta ChromaDB
            auth_token: Token autenticazione (da .env)
        """
        self.host = host
        self.port = port
        self.auth_token = auth_token or os.getenv("CHROMA_AUTH_TOKEN")
        
        # Configurazione client
        if self.auth_token:
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )
        else:
            self.client = chromadb.HttpClient(
                host=host,
                port=port
            )
    
    def create_or_get_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Crea o ottieni collection esistente
        
        Args:
            name: Nome collection
            metadata: Metadata opzionale per la collection
            
        Returns:
            Collection ChromaDB
        """
        try:
            collection = self.client.get_collection(name=name)
            print(f"✅ Collection '{name}' già esistente")
            return collection
        except:
            collection = self.client.create_collection(
                name=name,
                metadata=metadata or {}
            )
            print(f"✅ Collection '{name}' creata")
            return collection
    
    def delete_collection(self, name: str) -> bool:
        """Elimina collection"""
        try:
            self.client.delete_collection(name=name)
            print(f"✅ Collection '{name}' eliminata")
            return True
        except Exception as e:
            print(f"❌ Errore eliminazione: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        """Lista tutte le collections"""
        collections = self.client.list_collections()
        return [c.name for c in collections]
    
    # ========================================================
    # KNOWLEDGE BASE (Auto-Healing Errors)
    # ========================================================
    
    def init_knowledge_base(self):
        """Inizializza Knowledge Base per errori noti"""
        kb = self.create_or_get_collection(
            name="known_errors_kb",
            metadata={
                "description": "Knowledge Base per Auto-Healing",
                "created_at": datetime.now().isoformat()
            }
        )
        
        # Seed con errori comuni
        common_errors = [
            {
                "error_signature": "ConnectionTimeout PagineGialle API",
                "error_pattern": "requests.exceptions.ConnectionError.*paginegialle",
                "error_type": "ConnectionError",
                "solution": "Aumentare timeout da 30s a 60s nella chiamata requests.get(). "
                           "Aggiungere retry logic con backoff esponenziale (3 tentativi).",
                "solution_code": """
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

response = session.get(url, timeout=60)
                """,
                "success_count": 5
            },
            {
                "error_signature": "PostgreSQL connection refused",
                "error_pattern": "psycopg2.OperationalError.*Connection refused",
                "error_type": "DatabaseError",
                "solution": "Verificare che container PostgreSQL sia up. "
                           "Attendere 10 secondi e riprovare. "
                           "Controllare docker-compose.yml per depends_on.",
                "solution_code": """
import time
import psycopg2

max_retries = 5
for i in range(max_retries):
    try:
        conn = psycopg2.connect(conn_string)
        break
    except psycopg2.OperationalError:
        if i < max_retries - 1:
            time.sleep(10)
        else:
            raise
                """,
                "success_count": 3
            },
            {
                "error_signature": "Ollama model not found",
                "error_pattern": "model.*not found",
                "error_type": "ModelError",
                "solution": "Modello non scaricato. Eseguire: docker exec ollama ollama pull <model_name>",
                "solution_code": """
import subprocess

model_name = "qwen2.5:14b"
result = subprocess.run(
    ["docker", "exec", "ollama", "ollama", "pull", model_name],
    capture_output=True
)
if result.returncode == 0:
    print(f"✅ Modello {model_name} scaricato")
                """,
                "success_count": 10
            },
            {
                "error_signature": "n8n workflow execution timeout",
                "error_pattern": "Execution.*timed out",
                "error_type": "TimeoutError",
                "solution": "Aumentare timeout workflow in n8n settings da 120s a 300s. "
                           "Se script Python, ottimizzare codice o spezzare in chunk.",
                "solution_code": """
# In n8n workflow settings:
# Settings > Executions > Timeout: 300

# Oppure in script Python, processa in batch:
for batch in chunks(data, batch_size=100):
    process_batch(batch)
    time.sleep(1)  # Pausa tra batch
                """,
                "success_count": 2
            },
            {
                "error_signature": "Claude API rate limit",
                "error_pattern": "rate_limit_error",
                "error_type": "APIError",
                "solution": "Rate limit raggiunto. Implementare exponential backoff. "
                           "Ridurre frequenza chiamate o switchare temporaneamente su Ollama.",
                "solution_code": """
import time

def call_claude_with_retry(client, prompt, max_retries=3):
    for i in range(max_retries):
        try:
            return client.generate(prompt)
        except Exception as e:
            if "rate_limit" in str(e):
                wait_time = 2 ** i  # Exponential backoff
                time.sleep(wait_time)
            else:
                raise
    return None
                """,
                "success_count": 1
            }
        ]
        
        # Aggiungi errori a KB
        for i, error in enumerate(common_errors):
            error_id = self._generate_error_id(error["error_signature"])
            
            kb.add(
                ids=[error_id],
                documents=[f"{error['error_signature']}: {error['solution']}"],
                metadatas=[{
                    "error_type": error["error_type"],
                    "error_pattern": error["error_pattern"],
                    "solution_code": error["solution_code"],
                    "success_count": error["success_count"],
                    "created_at": datetime.now().isoformat()
                }]
            )
        
        print(f"✅ Knowledge Base inizializzata con {len(common_errors)} errori comuni")
        return kb
    
    def search_known_error(
        self,
        error_message: str,
        n_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Cerca errore simile in Knowledge Base
        
        Args:
            error_message: Messaggio di errore da matchare
            n_results: Numero risultati da ritornare
            
        Returns:
            Lista di soluzioni trovate
        """
        try:
            kb = self.client.get_collection("known_errors_kb")
        except:
            print("⚠️  Knowledge Base non inizializzata. Esegui --init-kb")
            return []
        
        results = kb.query(
            query_texts=[error_message],
            n_results=n_results
        )
        
        solutions = []
        for i in range(len(results['ids'][0])):
            solutions.append({
                "error_id": results['ids'][0][i],
                "similarity_score": 1 - results['distances'][0][i],  # Maggiore è meglio
                "solution": results['documents'][0][i],
                "metadata": results['metadatas'][0][i]
            })
        
        return solutions
    
    def add_error_to_kb(
        self,
        error_signature: str,
        error_type: str,
        solution: str,
        solution_code: str = "",
        error_pattern: str = ""
    ):
        """Aggiungi nuovo errore risolto alla KB"""
        kb = self.create_or_get_collection("known_errors_kb")
        
        error_id = self._generate_error_id(error_signature)
        
        kb.add(
            ids=[error_id],
            documents=[f"{error_signature}: {solution}"],
            metadatas=[{
                "error_type": error_type,
                "error_pattern": error_pattern or error_signature,
                "solution_code": solution_code,
                "success_count": 1,
                "created_at": datetime.now().isoformat()
            }]
        )
        
        print(f"✅ Errore aggiunto alla KB: {error_id}")
    
    def increment_success_count(self, error_id: str):
        """Incrementa contatore successi per una soluzione"""
        kb = self.client.get_collection("known_errors_kb")
        
        # ChromaDB non supporta update in-place, quindi:
        # 1. Retrieve
        result = kb.get(ids=[error_id])
        if not result['ids']:
            print(f"⚠️  Error ID {error_id} non trovato")
            return
        
        # 2. Modifica metadata
        metadata = result['metadatas'][0]
        metadata['success_count'] = metadata.get('success_count', 0) + 1
        
        # 3. Delete + Re-add
        kb.delete(ids=[error_id])
        kb.add(
            ids=[error_id],
            documents=result['documents'],
            metadatas=[metadata]
        )
        
        print(f"✅ Success count incrementato per {error_id}")
    
    # ========================================================
    # RAG per Documenti Progetto
    # ========================================================
    
    def create_project_rag_collection(self, project_id: str):
        """Crea collection RAG per un progetto specifico"""
        collection_name = f"project_{project_id}_docs"
        
        collection = self.create_or_get_collection(
            name=collection_name,
            metadata={
                "project_id": project_id,
                "type": "rag_documents",
                "created_at": datetime.now().isoformat()
            }
        )
        
        return collection
    
    def add_documents_to_project(
        self,
        project_id: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]] = None,
        ids: List[str] = None
    ):
        """
        Aggiungi documenti a collection RAG progetto
        
        Args:
            project_id: ID progetto
            documents: Lista testi documenti
            metadatas: Lista metadata per ogni documento
            ids: Lista ID custom (opzionale, genera hash se None)
        """
        collection = self.create_project_rag_collection(project_id)
        
        # Genera IDs se non forniti
        if ids is None:
            ids = [self._generate_doc_id(doc) for doc in documents]
        
        # Default metadata se non fornite
        if metadatas is None:
            metadatas = [{"added_at": datetime.now().isoformat()} for _ in documents]
        
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        print(f"✅ {len(documents)} documenti aggiunti a progetto {project_id}")
    
    def query_project_docs(
        self,
        project_id: str,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query RAG su documenti progetto
        
        Args:
            project_id: ID progetto
            query: Query testuale
            n_results: Numero risultati
            where: Filtri metadata (es. {"doc_type": "report"})
            
        Returns:
            Lista documenti rilevanti con score
        """
        collection_name = f"project_{project_id}_docs"
        
        try:
            collection = self.client.get_collection(collection_name)
        except:
            print(f"⚠️  Collection RAG per progetto {project_id} non esiste")
            return []
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where
        )
        
        docs = []
        for i in range(len(results['ids'][0])):
            docs.append({
                "doc_id": results['ids'][0][i],
                "content": results['documents'][0][i],
                "relevance_score": 1 - results['distances'][0][i],
                "metadata": results['metadatas'][0][i]
            })
        
        return docs
    
    def delete_project_rag_collection(self, project_id: str):
        """Elimina collection RAG di un progetto"""
        collection_name = f"project_{project_id}_docs"
        return self.delete_collection(collection_name)
    
    # ========================================================
    # Master Agent Memory
    # ========================================================
    
    def init_master_agent_memory(self):
        """Inizializza memory per Master Agent (conversazioni passate)"""
        memory = self.create_or_get_collection(
            name="master_agent_memory",
            metadata={
                "description": "Conversational memory for Master Agent",
                "created_at": datetime.now().isoformat()
            }
        )
        return memory
    
    def save_conversation(
        self,
        conversation_id: str,
        user_message: str,
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Salva conversazione Master Agent"""
        memory = self.init_master_agent_memory()
        
        doc_text = f"User: {user_message}\nAgent: {agent_response}"
        
        doc_id = f"conv_{conversation_id}_{datetime.now().timestamp()}"
        
        meta = metadata or {}
        meta.update({
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat()
        })
        
        memory.add(
            ids=[doc_id],
            documents=[doc_text],
            metadatas=[meta]
        )
        
        print(f"✅ Conversazione salvata: {doc_id}")
    
    def search_past_conversations(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Cerca conversazioni passate simili"""
        try:
            memory = self.client.get_collection("master_agent_memory")
        except:
            return []
        
        results = memory.query(
            query_texts=[query],
            n_results=n_results
        )
        
        conversations = []
        for i in range(len(results['ids'][0])):
            conversations.append({
                "doc_id": results['ids'][0][i],
                "conversation": results['documents'][0][i],
                "relevance": 1 - results['distances'][0][i],
                "metadata": results['metadatas'][0][i]
            })
        
        return conversations
    
    # ========================================================
    # Utility Functions
    # ========================================================
    
    def _generate_error_id(self, error_signature: str) -> str:
        """Genera ID univoco per errore"""
        hash_obj = hashlib.sha256(error_signature.encode())
        return f"error_{hash_obj.hexdigest()[:16]}"
    
    def _generate_doc_id(self, document: str) -> str:
        """Genera ID univoco per documento"""
        hash_obj = hashlib.sha256(document.encode())
        return f"doc_{hash_obj.hexdigest()[:16]}"
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Ottieni statistiche collection"""
        try:
            collection = self.client.get_collection(collection_name)
            count = collection.count()
            
            return {
                "name": collection_name,
                "total_documents": count,
                "metadata": collection.metadata
            }
        except Exception as e:
            return {"error": str(e)}


# ============================================================
# Funzioni Standalone
# ============================================================

def search_error_solution_standalone(error_message: str) -> Dict[str, Any]:
    """
    Funzione standalone per cercare soluzione errore
    Chiamabile da n8n
    """
    manager = ChromaManager()
    solutions = manager.search_known_error(error_message, n_results=1)
    
    if solutions:
        best_match = solutions[0]
        return {
            "found": True,
            "similarity_score": best_match["similarity_score"],
            "solution": best_match["solution"],
            "solution_code": best_match["metadata"].get("solution_code", ""),
            "error_type": best_match["metadata"].get("error_type", ""),
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "found": False,
            "message": "Nessuna soluzione nota trovata per questo errore"
        }


# ============================================================
# CLI Interface
# ============================================================

def main():
    """Entry point CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ChromaDB Manager CLI")
    parser.add_argument("--init-kb", action="store_true", help="Inizializza Knowledge Base")
    parser.add_argument("--list", action="store_true", help="Lista collections")
    parser.add_argument("--stats", type=str, metavar="COLLECTION", help="Statistiche collection")
    parser.add_argument("--search-error", type=str, metavar="ERROR_MSG", help="Cerca soluzione errore")
    parser.add_argument("--test", action="store_true", help="Test connessione ChromaDB")
    
    args = parser.parse_args()
    
    try:
        manager = ChromaManager()
    except Exception as e:
        print(f"❌ Errore connessione ChromaDB: {e}", file=sys.stderr)
        sys.exit(1)
    
    if args.test:
        print("🧪 Test connessione ChromaDB...")
        collections = manager.list_collections()
        print(f"✅ Connessione OK - {len(collections)} collections trovate")
        sys.exit(0)
    
    elif args.init_kb:
        print("🔧 Inizializzazione Knowledge Base...")
        manager.init_knowledge_base()
        sys.exit(0)
    
    elif args.list:
        print("📋 Collections in ChromaDB:")
        collections = manager.list_collections()
        for i, name in enumerate(collections, 1):
            stats = manager.get_collection_stats(name)
            print(f"  {i}. {name} ({stats.get('total_documents', 0)} docs)")
        sys.exit(0)
    
    elif args.stats:
        stats = manager.get_collection_stats(args.stats)
        if stats.get("error"):
            print(f"❌ Errore: {stats['error']}")
            sys.exit(1)
        
        print(f"📊 Statistiche: {args.stats}")
        print(f"   Documenti totali: {stats['total_documents']}")
        print(f"   Metadata: {json.dumps(stats['metadata'], indent=2)}")
        sys.exit(0)
    
    elif args.search_error:
        print(f"🔍 Ricerca soluzione per: {args.search_error[:100]}...")
        solutions = manager.search_known_error(args.search_error)
        
        if not solutions:
            print("❌ Nessuna soluzione trovata")
            sys.exit(1)
        
        print(f"\n✅ Trovate {len(solutions)} soluzioni simili:\n")
        for i, sol in enumerate(solutions, 1):
            print(f"{i}. Similarity: {sol['similarity_score']:.2f}")
            print(f"   {sol['solution']}\n")
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
