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

from app.core import config

def load_and_split_document(file_path: Path):
    """
    Memuat dokumen dan membaginya menjadi beberapa bagian dengan cara yang hemat memori.
    PDF diproses halaman per halaman untuk menghindari kehabisan RAM.
    """
    ext = file_path.suffix.lower()
    documents = []

    try:
        if ext == '.pdf':
            print(f"Optimized PDF processing for: {file_path.name}")
            with open(file_path, "rb") as pdf_file:
                reader = pypdf.PdfReader(pdf_file)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:  # Hanya proses halaman yang mengandung teks
                        documents.append(Document(
                            page_content=text,
                            metadata={"source": str(file_path), "page": i}
                        ))
        elif ext == '.docx':
            loader = Docx2txtLoader(str(file_path))
            documents = loader.load()
        elif ext == '.txt':
            loader = TextLoader(str(file_path), encoding='utf-8')
            documents = loader.load()
        else:
            print(f"Unsupported file type: {ext}")
            return []

        if not documents:
            print(f"Warning: No documents were loaded from {file_path.name}.")
            return []

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE, 
            chunk_overlap=config.CHUNK_OVERLAP
        )
        return text_splitter.split_documents(documents)

    except Exception as e:
        print(f"❌ Error loading document {file_path.name}:")
        traceback.print_exc()
        return []


class RAGService:
    def __init__(self):
        self.is_ready = False
        self.vector_store = None
        self.retrieval_chain = None
        self.embeddings = None
        
        try:
            if not config.GOOGLE_API_KEY:
                print("❌ CRITICAL ERROR: GOOGLE_API_KEY tidak diatur.")
                return

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
                print("⚠️ FAISS index not found. Creating a new empty index.")
                dummy_texts = ["init"]
                self.vector_store = FAISS.from_texts(texts=dummy_texts, embedding=self.embeddings)
                self.vector_store.delete(self.vector_store.index_to_docstore_id.values())
                self.vector_store.save_local(
                    folder_path=str(config.FAISS_INDEX_PATH.parent),
                    index_name=config.FAISS_INDEX_PATH.stem
                )

            self._create_retrieval_chain()
            self.is_ready = True
            print("✅ RAG components (Google Gemini) are ready.")
        except Exception as e:
            print(f"❌ CRITICAL ERROR: Failed to initialize RAG components.")
            traceback.print_exc()

    def _create_retrieval_chain(self):
        llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3, convert_system_message_to_human=True)
        prompt_template = """
        Gunakan potongan konteks berikut untuk menjawab pertanyaan.
        Jika tidak tahu jawabannya, katakan saja Anda tidak tahu. Jangan mencoba mengarang jawaban.
        Konteks: {context}
        Pertanyaan: {question}
        Jawaban yang membantu:
        """
        prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        self.retrieval_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 5}),
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True
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
            result = self.retrieval_chain.invoke(query)
            return result.get("result", "Tidak dapat menemukan jawaban.")
        return "Sistem chat tidak siap."
    
    def rebuild_index(self):
        pass

rag_service = RAGService()
