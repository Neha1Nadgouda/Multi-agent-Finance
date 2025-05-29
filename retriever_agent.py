from typing import Dict, Any, List, Optional
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import os
from datetime import datetime
import pickle
from pathlib import Path

class RetrieverAgent:
    def __init__(self):
        # Initialize the sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize FAISS index
        self.index = None
        self.documents = []
        self.embedding_size = 384  # Size of embeddings from all-MiniLM-L6-v2
        
        # Create data directory if it doesn't exist
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Load existing index if available
        self._load_index()
        
        self.context_store = {
            "market_trends": [
                "Tech stocks have shown strong momentum in recent weeks",
                "Asian markets are experiencing increased volatility",
                "Semiconductor sector faces supply chain challenges"
            ]
        }
    
    def _load_index(self):
        """Load existing FAISS index and documents if available"""
        index_path = self.data_dir / "faiss_index.bin"
        docs_path = self.data_dir / "documents.pkl"
        
        try:
            if index_path.exists() and docs_path.exists():
                self.index = faiss.read_index(str(index_path))
                with open(docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
            else:
                # Initialize new index
                self.index = faiss.IndexFlatL2(self.embedding_size)
                
        except Exception as e:
            print(f"Error loading index: {str(e)}")
            # Initialize new index
            self.index = faiss.IndexFlatL2(self.embedding_size)
    
    def _save_index(self):
        """Save FAISS index and documents"""
        try:
            index_path = self.data_dir / "faiss_index.bin"
            docs_path = self.data_dir / "documents.pkl"
            
            faiss.write_index(self.index, str(index_path))
            with open(docs_path, 'wb') as f:
                pickle.dump(self.documents, f)
                
        except Exception as e:
            print(f"Error saving index: {str(e)}")
    
    async def add_documents(self, documents: List[Dict[str, Any]]):
        """Add new documents to the index"""
        try:
            # Extract text content from documents
            texts = [doc.get("content", "") for doc in documents]
            
            # Generate embeddings
            embeddings = self.model.encode(texts)
            
            # Add to FAISS index
            self.index.add(np.array(embeddings))
            
            # Store original documents
            self.documents.extend(documents)
            
            # Save updated index
            self._save_index()
            
        except Exception as e:
            print(f"Error adding documents: {str(e)}")
    
    async def get_relevant_context(self, query: str) -> Dict[str, Any]:
        """Get relevant historical context based on the query"""
        try:
            # Encode query and context
            query_embedding = self.model.encode(query)
            context_embeddings = {
                category: self.model.encode(contexts)
                for category, contexts in self.context_store.items()
            }
            
            # Find most relevant contexts
            relevant_contexts = []
            for category, embeddings in context_embeddings.items():
                similarities = np.dot(embeddings, query_embedding)
                top_idx = np.argsort(similarities)[-2:]  # Get top 2 most relevant
                
                for idx in top_idx:
                    relevant_contexts.append({
                        "text": self.context_store[category][idx],
                        "category": category,
                        "relevance": float(similarities[idx])
                    })
            
            return {
                "contexts": sorted(relevant_contexts, key=lambda x: x["relevance"], reverse=True),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error retrieving context: {str(e)}")
            return {}
    
    async def update_document(self, doc_id: str, content: str):
        """Update an existing document in the index"""
        try:
            # Find document index
            doc_idx = None
            for i, doc in enumerate(self.documents):
                if doc.get("id") == doc_id:
                    doc_idx = i
                    break
            
            if doc_idx is not None:
                # Generate new embedding
                new_embedding = self.model.encode([content])
                
                # Remove old embedding
                self.index.remove_ids(np.array([doc_idx]))
                
                # Add new embedding
                self.index.add(np.array(new_embedding))
                
                # Update document
                self.documents[doc_idx]["content"] = content
                self.documents[doc_idx]["timestamp"] = datetime.now().isoformat()
                
                # Save updated index
                self._save_index()
                
        except Exception as e:
            print(f"Error updating document: {str(e)}")
    
    async def delete_document(self, doc_id: str):
        """Delete a document from the index"""
        try:
            # Find document index
            doc_idx = None
            for i, doc in enumerate(self.documents):
                if doc.get("id") == doc_id:
                    doc_idx = i
                    break
            
            if doc_idx is not None:
                # Remove from FAISS index
                self.index.remove_ids(np.array([doc_idx]))
                
                # Remove from documents list
                self.documents.pop(doc_idx)
                
                # Save updated index
                self._save_index()
                
        except Exception as e:
            print(f"Error deleting document: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the retriever service is working"""
        try:
            context = await self.get_relevant_context("How are tech stocks performing?")
            return {
                "healthy": len(context) > 0,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            } 