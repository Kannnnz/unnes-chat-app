# file: app/services/rag_service.py

from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema.document import Document
import google.generativeai as genai
import pypdf
import traceback
import threading

from app.core import config
from app.db.session import get_db_connection
from psycopg2.extras import DictCursor

index_lock = threading.Lock()

def _load_and_split_single_document(file_path: Path) -> list[Document]:
    """Helper untuk memuat satu dokumen dan membaginya menjadi chunks."""
    ext = file_path.suffix.lower()
    documents = []
    try:
        print(f"  - Loading file: {file_path.name}")
        if ext == '.pdf':
            with open(file_path, "rb") as pdf_file:
                reader = pypdf.PdfReader(pdf_file)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        documents.append(Document(page_content=text, metadata={"source": str(file_path), "page": i}))
        
        if not documents:
            return []

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)
        chunks = text_splitter.split_documents(documents)
        
        valid_chunks = [chunk for chunk in chunks if chunk.page_content and chunk.page_content.strip()]
        return valid_chunks
        
    except Exception:
        print(f"  - Failed to load file {file_path.name}")
        traceback.print_exc()
        return []

class RAGService:
    def __init__(self):
        self.vector_store = None
        self.retrieval_chain = None
        self.is_ready = False
        try:
            genai.configure(api_key=config.GOOGLE_API_KEY)
            self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            self._load_vector_store()
            self._create_retrieval_chain()
            self.is_ready = True
            print("✅ RAG Service Initialized.")
        except Exception:
            print("❌ CRITICAL ERROR: Failed to initialize RAG Service.")
            traceback.print_exc()

    def _load_vector_store(self):
        with index_lock:
            if config.FAISS_INDEX_PATH.exists():
                print(f"🚀 Loading existing FAISS index...")
                self.vector_store = FAISS.load_local(
                    folder_path=str(config.FAISS_INDEX_PATH.parent), 
                    index_name=config.FAISS_INDEX_PATH.stem,
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print("✅ Index loaded.")
            else:
                print("⚠️ FAISS index not found. Will be created on first upload.")
                self.vector_store = None

    def _create_retrieval_chain(self):
        if not self.vector_store:
            self.retrieval_chain = None
            return
        
        llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3, convert_system_message_to_human=True)
        prompt_template_text = "Gunakan konteks berikut untuk menjawab pertanyaan.\nKonteks: {context}\nPertanyaan: {question}\nJawaban:"
        prompt = PromptTemplate(template=prompt_template_text, input_variables=["context", "question"])
        
        self.retrieval_chain = RetrievalQA.from_chain_type(
            llm=llm, chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 5}),
            chain_type_kwargs={"prompt": prompt}
        )
        print("✅ Retrieval chain created/updated.")

    def rebuild_index_from_db(self):
        """
        Membangun ulang seluruh index FAISS dari semua dokumen yang ada di database.
        Ini adalah metode yang paling kuat untuk memastikan konsistensi.
        """
        with index_lock:
            print(" rebuilding FAISS index from all documents in DB...")
            all_chunks = []
            
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=DictCursor)
                cursor.execute("SELECT file_path, filename FROM documents WHERE is_indexed = TRUE")
                all_docs = cursor.fetchall()
                cursor.close()

            if not all_docs:
                print("No indexed documents found in DB. Clearing index if it exists.")
                if config.FAISS_INDEX_PATH.exists():
                    config.FAISS_INDEX_PATH.unlink()
                    (config.FAISS_INDEX_PATH.parent / f"{config.FAISS_INDEX_PATH.stem}.pkl").unlink(missing_ok=True)
                self.vector_store = None
                self._create_retrieval_chain()
                return

            print(f"Found {len(all_docs)} documents to process for re-indexing.")
            for doc in all_docs:
                file_path = Path(doc['file_path'])
                if file_path.exists():
                    chunks = _load_and_split_single_document(file_path)
                    for chunk in chunks:
                        chunk.metadata.update({"doc_id": doc.get('id', 'N/A'), "filename": doc['filename']})
                    all_chunks.extend(chunks)
            
            if not all_chunks:
                print("No valid content could be extracted from documents. Index will not be created.")
                return

            print(f"Creating new index from {len(all_chunks)} total chunks...")
            # Buat index baru dari awal
            self.vector_store = FAISS.from_documents(all_chunks, self.embeddings)
            
            # Simpan index yang baru dan segar
            self.vector_store.save_local(
                folder_path=str(config.FAISS_INDEX_PATH.parent),
                index_name=config.FAISS_INDEX_PATH.stem
            )
            # Buat ulang chain dengan retriever yang baru
            self._create_retrieval_chain()
            print("✅ Index rebuild complete and saved.")

    def invoke_chain(self, query: str, document_ids: list):
        if self.retrieval_chain:
            return self.retrieval_chain.invoke(query).get("result", "Tidak dapat menemukan jawaban dari dokumen.")
        return "Sistem chat belum siap. Silakan unggah dokumen terlebih dahulu."

rag_service = RAGService()
