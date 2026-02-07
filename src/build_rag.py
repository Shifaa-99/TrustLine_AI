from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


def build_rag_index():
    kb_path = Path("data/knowledge_base.txt")

    if not kb_path.exists():
        raise FileNotFoundError("knowledge_base.txt not found")

    text = kb_path.read_text(encoding="utf-8")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50
    )

    documents = splitter.create_documents([text])

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    vector_store = FAISS.from_documents(documents, embeddings)

    vector_store.save_local("rag_index")

    print("✅ RAG index built successfully.")
    print(f"📄 Chunks created: {len(documents)}")


if __name__ == "__main__":
    build_rag_index()
