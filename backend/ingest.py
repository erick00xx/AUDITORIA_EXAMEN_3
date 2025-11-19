# backend/ingest.py
import os
import shutil
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

KNOWLEDGE_BASE_DIR = "knowledge_base"
VECTOR_STORE_DIR = "vector_store"

def main():
    print("--- INICIO DEL SCRIPT DE INGESTA ---")

    # --- CARGA DE DOCUMENTOS CORREGIDA ---
    # Creamos un loader para cada tipo de archivo

    # 1. Loader para archivos .pdf
    print("\n1a. Cargando documentos PDF...")
    pdf_loader = DirectoryLoader(
        KNOWLEDGE_BASE_DIR,
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True,
        use_multithreading=True
    )
    pdf_documents = pdf_loader.load()

    # 2. Loader para archivos .txt
    print("\n1b. Cargando documentos de texto (.txt)...")
    txt_loader = DirectoryLoader(
        KNOWLEDGE_BASE_DIR,
        glob="**/*.txt",
        loader_cls=TextLoader, # Usamos el lector de texto simple
        show_progress=True
    )
    txt_documents = txt_loader.load()

    # Combinamos todos los documentos en una sola lista
    documents = pdf_documents + txt_documents

    if not documents:
        print("[ERROR] No se encontraron documentos .txt o .pdf.")
        return
    print(f"\n¡Éxito! Se cargaron un total de {len(documents)} documentos.")

    print("\n2. Dividiendo documentos en chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(documents)
    print(f"Se dividieron en {len(chunks)} chunks.")

    print("\n3. Generando embeddings con el modelo 'multilingual-e5-large'...")
    embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")

    print(f"\n4. Creando base de datos vectorial en '{VECTOR_STORE_DIR}'...")
    
    if os.path.exists(VECTOR_STORE_DIR):
        print(f"Eliminando la antigua base de datos vectorial en '{VECTOR_STORE_DIR}'...")
        shutil.rmtree(VECTOR_STORE_DIR)
        
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=VECTOR_STORE_DIR
    )

    print("\n--- ¡INGESTA COMPLETADA EXITOSAMENTE! ---")

if __name__ == "__main__":
    main()