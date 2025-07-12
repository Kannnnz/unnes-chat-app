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
from langchain.docstore.in_memory import InMemoryDocstore
import google.generativeai as genai
import pypdf
import faiss
import traceback
import numpy as np

from app.core import config

def load_and_split_document(file_path: Path):
    ext = file_path.suffix.lower()
    documents = []
    try:
        if ext == '.pdf':
            with open(file_path, "rb") as pdf_file:
                reader = pypdf.PdfReader(pdf_file)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        documents.append(Document(page_content=text, metadata={"source": str(file_path), "page": i}))
        elif ext == '.docx':
            documents = Docx2txtLoader(str(file_path)).load()
        elif ext == '.txt':
            documents = TextLoader(str(file_path), encoding='utf-8').load()
        else:
            return []

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)
        return text_splitter.split_documents(documents)
    except Exception:
        traceback.print_exc()
        return []

class RAGService:
    def __init__(self):
        self.is_ready = False
        try:
            genai.configure(api_key=config.GOOGLE_API_KEY)
            self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            
            if config.FAISS_INDEX_PATH.exists():
                print(f"🚀 Loading existing FAISS index from {config.FAISS_INDEX_PATH}...")
                self.vector_store = FAISS.load_local(
                    folder_path=str(config.FAISS_INDEX_PATH.parent), 
                    index_name=config.FAISS_INDEX_PATH.stem,
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True
                )
            else:
                print("⚠️ FAISS index not found. Creating a new empty, correctly dimensioned index.")
                # PERBAIKAN UTAMA: Membuat index kosong dengan dimensi yang benar secara eksplisit
                embedding_size = len(self.embeddings.embed_query("test"))
                index = faiss.IndexFlatL2(embedding_size)
                docstore = InMemoryDocstore({})
                index_to_docstore_id = {}
                self.vector_store = FAISS(self.embeddings.embed_query, index, docstore, index_to_docstore_id)
                
                # Simpan index kosong yang sudah benar
                self.vector_store.save_local(
                    folder_path=str(config.FAISS_INDEX_PATH.parent),
                    index_name=config.FAISS_INDEX_PATH.stem
                )

            self._create_retrieval_chain()
            self.is_ready = True
            print("✅ RAG components are ready.")
        except Exception:
            self.is_ready = False
            print(f"❌ CRITICAL ERROR: Failed to initialize RAG components.")
            traceback.print_exc()

    def _create_retrieval_chain(self):
        llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3, convert_system_message_to_human=True)
        prompt_template = "Gunakan potongan konteks berikut untuk menjawab pertanyaan.\nKonteks: {context}\nPertanyaan: {question}\nJawaban yang membantu:"
        prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        self.retrieval_chain = RetrievalQA.from_chain_type(
            llm=llm, chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 5}),
            chain_type_kwargs={"prompt": prompt}
        )

    def add_documents_to_index(self, documents):
        if self.vector_store is not None and documents:
            self.vector_store.add_documents(documents)
            self.vector_store.save_local(
                folder_path=str(config.FAISS_INDEX_PATH.parent),
                index_name=config.FAISS_INDEX_PATH.stem
            )
            print(f"✅ Successfully added {len(documents)} chunks to FAISS index.")

    def invoke_chain(self, query: str, document_ids: list):
        if self.retrieval_chain:
            return self.retrieval_chain.invoke(query).get("result", "Tidak dapat menemukan jawaban.")
        return "Sistem chat tidak siap."

rag_service = RAGService()
