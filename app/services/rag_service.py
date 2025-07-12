# file: app/services/rag_service.py

from pathlib import Path
from langchain_community.document_loaders import Docx2txtLoader, TextLoader
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

# Kunci untuk sinkronisasi thread agar tidak terjadi race condition
index_lock = threading.Lock()

def load_and_split_document(file_path: Path) -> list[Document]:
    """Memuat dan memvalidasi dokumen, memastikan tidak ada konten kosong."""
    ext = file_path.suffix.lower()
    documents = []
    try:
        if ext == '.pdf':
            with open(file_path, "rb") as pdf_file:
                reader = pypdf.PdfReader(pdf_file)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text and text.strip():  # Hanya proses halaman yang benar-benar mengandung teks
                        documents.append(Document(page_content=text, metadata={"source": str(file_path), "page": i}))
        elif ext == '.docx':
            documents = Docx2txtLoader(str(file_path)).load()
        elif ext == '.txt':
            documents = TextLoader(str(file_path), encoding='utf-8').load()
        
        if not documents:
            return []

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE, 
            chunk_overlap=config.CHUNK_OVERLAP
        )
        chunks = text_splitter.split_documents(documents)
        
        # PERBAIKAN KRUSIAL: Memfilter semua chunk yang mungkin kosong setelah split
        valid_chunks = [chunk for chunk in chunks if chunk.page_content and chunk.page_content.strip()]
        return valid_chunks
        
    except Exception:
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
            self._load_or_init_vector_store()
            self._create_retrieval_chain()
            self.is_ready = True
            print("✅ RAG Service Initialized.")
        except Exception:
            print(f"❌ CRITICAL ERROR: Failed to initialize RAG Service.")
            traceback.print_exc()

    def _load_or_init_vector_store(self):
        if config.FAISS_INDEX_PATH.exists():
            print(f"🚀 Loading existing FAISS index...")
            self.vector_store = FAISS.load_local(
                folder_path=str(config.FAISS_INDEX_PATH.parent), 
                index_name=config.FAISS_INDEX_PATH.stem,
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
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

    def add_documents_to_index(self, documents: list[Document]):
        with index_lock:
            if not documents:
                print("No valid documents to add to index.")
                return

            if self.vector_store is None:
                print("✨ Creating new FAISS index from first document batch...")
                self.vector_store = FAISS.from_documents(documents, self.embeddings)
                self._create_retrieval_chain()
            else:
                print(f"➕ Adding {len(documents)} new chunks to existing index...")
                self.vector_store.add_documents(documents)
            
            self.vector_store.save_local(
                folder_path=str(config.FAISS_INDEX_PATH.parent),
                index_name=config.FAISS_INDEX_PATH.stem
            )
            print("✅ Index saved successfully.")

    def invoke_chain(self, query: str, document_ids: list):
        if self.retrieval_chain:
            return self.retrieval_chain.invoke(query).get("result", "Tidak dapat menemukan jawaban dari dokumen yang diberikan.")
        return "Sistem chat belum siap. Silakan unggah dokumen terlebih dahulu."

rag_service = RAGService()
