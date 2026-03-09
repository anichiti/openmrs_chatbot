from vectorstore.chroma import VectorStore
from utils.logger import setup_logger

logger = setup_logger(__name__)


class KnowledgeAgent:
    def __init__(self):
        self.vectorstore = VectorStore()
        self.vectorstore.initialize_collections()

    def query_doctor_kb(self, question, top_k=5):
        results = self.vectorstore.query_doctor_kb(question, top_k=top_k)
        
        if results is None:
            return {"documents": [], "metadatas": [], "distances": []}

        return {
            "documents": results.get("documents", [[]]),
            "metadatas": results.get("metadatas", [[]]),
            "distances": results.get("distances", [[]])
        }

    def query_patient_kb(self, question, top_k=5):
        results = self.vectorstore.query_patient_kb(question, top_k=top_k)
        
        if results is None:
            return {"documents": [], "metadatas": [], "distances": []}

        return {
            "documents": results.get("documents", [[]]),
            "metadatas": results.get("metadatas", [[]]),
            "distances": results.get("distances", [[]])
        }

    def format_context(self, kb_results):
        if not kb_results or not kb_results.get("documents"):
            return ""

        context_parts = []
        documents = kb_results.get("documents", [[]])[0]
        
        for doc in documents:
            if doc:
                context_parts.append(doc)

        return "\n\n".join(context_parts)
