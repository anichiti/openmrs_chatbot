import os
import chromadb
from chromadb.config import Settings
import ollama
from utils.logger import setup_logger
from utils.config import (
    VECTORSTORE_DIR, 
    DOCTOR_KB_DIR, 
    PATIENT_KB_DIR,
    OLLAMA_HOST,
    OLLAMA_EMBED_MODEL
)

# Try to import langchain components - fallback if not available
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    SPLITTER_AVAILABLE = True
except:
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        SPLITTER_AVAILABLE = True
    except:
        SPLITTER_AVAILABLE = False
        logger = setup_logger(__name__)
        logger.warning("RecursiveCharacterTextSplitter not available - PDF indexing disabled")

try:
    from langchain_community.document_loaders import PyPDFLoader
    PDF_LOADER_AVAILABLE = True
except:
    try:
        from langchain.document_loaders import PyPDFLoader
        PDF_LOADER_AVAILABLE = True
    except:
        PyPDFLoader = None
        PDF_LOADER_AVAILABLE = False

logger = setup_logger(__name__)

# Configure Ollama client
ollama_client = ollama.Client(host=OLLAMA_HOST)

logger = setup_logger(__name__)


class VectorStore:
    def __init__(self):
        os.makedirs(VECTORSTORE_DIR, exist_ok=True)
        try:
            # Try new ChromaDB API
            import chromadb
            self.client = chromadb.PersistentClient(path=VECTORSTORE_DIR)
            logger.info("Using new ChromaDB API (PersistentClient)")
        except Exception as e:
            logger.warning(f"New ChromaDB API failed: {e}. Trying ephemeral client...")
            try:
                # Fall back to ephemeral client
                self.client = chromadb.EphemeralClient()
                logger.info("Using ChromaDB EphemeralClient (data not persisted)")
            except Exception as e2:
                logger.error(f"ChromaDB initialization failed: {e2}")
                self.client = None
                
        self.doctor_collection = None
        self.patient_collection = None

    def get_embedding(self, text):
        """Get embedding using Ollama's embedding model"""
        try:
            result = ollama_client.embeddings(
                model=OLLAMA_EMBED_MODEL,
                prompt=text
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return None

    def load_pdf_documents(self, directory):
        """Load PDF documents if langchain is available"""
        documents = []
        
        if not PDF_LOADER_AVAILABLE:
            return documents
            
        if not os.path.exists(directory):
            return documents

        for filename in os.listdir(directory):
            if filename.endswith('.pdf'):
                filepath = os.path.join(directory, filename)
                try:
                    loader = PyPDFLoader(filepath)
                    docs = loader.load()
                    documents.extend(docs)
                    logger.info(f"Loaded PDF: {filename}")
                except Exception as e:
                    logger.error(f"Error loading PDF {filename}: {str(e)}")

        return documents

    def split_documents(self, documents, chunk_size=1000, chunk_overlap=100):
        """Split documents if langchain is available"""
        if not SPLITTER_AVAILABLE:
            logger.warning("RecursiveCharacterTextSplitter not available - returning documents as-is")
            return documents
            
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(documents)
        logger.info(f"Split documents into {len(chunks)} chunks")
        return chunks

    def index_doctor_kb(self):
        try:
            self.doctor_collection = self.client.get_or_create_collection(
                name="doctor_knowledge_base",
                metadata={"hnsw:space": "cosine"}
            )
            
            documents = self.load_pdf_documents(DOCTOR_KB_DIR)
            if not documents:
                return False

            chunks = self.split_documents(documents)
            
            for i, chunk in enumerate(chunks):
                embedding = self.get_embedding(chunk.page_content)
                if embedding:
                    self.doctor_collection.add(
                        ids=[f"doctor_{i}"],
                        embeddings=[embedding],
                        documents=[chunk.page_content],
                        metadatas=[{"source": chunk.metadata.get("source", "unknown")}]
                    )
            
            logger.info(f"Doctor KB indexed with {len(chunks)} chunks")
            return True
        except Exception as e:
            logger.error(f"Error indexing doctor KB: {str(e)}")
            return False

    def index_patient_kb(self):
        try:
            self.patient_collection = self.client.get_or_create_collection(
                name="patient_knowledge_base",
                metadata={"hnsw:space": "cosine"}
            )
            
            documents = self.load_pdf_documents(PATIENT_KB_DIR)
            if not documents:
                return False

            chunks = self.split_documents(documents)
            
            for i, chunk in enumerate(chunks):
                embedding = self.get_embedding(chunk.page_content)
                if embedding:
                    self.patient_collection.add(
                        ids=[f"patient_{i}"],
                        embeddings=[embedding],
                        documents=[chunk.page_content],
                        metadatas=[{"source": chunk.metadata.get("source", "unknown")}]
                    )
            
            logger.info(f"Patient KB indexed with {len(chunks)} chunks")
            return True
        except Exception as e:
            logger.error(f"Error indexing patient KB: {str(e)}")
            return False

    def query_doctor_kb(self, query, top_k=5):
        if not self.doctor_collection:
            self.doctor_collection = self.client.get_or_create_collection(
                name="doctor_knowledge_base"
            )

        try:
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return None
            
            results = self.doctor_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            logger.info(f"Doctor KB retrieved {len(results['documents'][0])} results")
            return results
        except Exception as e:
            logger.error(f"Error querying doctor KB: {str(e)}")
            return None

    def query_patient_kb(self, query, top_k=5):
        if not self.patient_collection:
            self.patient_collection = self.client.get_or_create_collection(
                name="patient_knowledge_base"
            )

        try:
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return None
            
            results = self.patient_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            logger.info(f"Patient KB retrieved {len(results['documents'][0])} results")
            return results
        except Exception as e:
            logger.error(f"Error querying patient KB: {str(e)}")
            return None

    def initialize_collections(self):
        self.index_doctor_kb()
        self.index_patient_kb()
        logger.info("Knowledge base collections initialized")
