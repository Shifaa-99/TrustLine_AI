import os
from openai import OpenAI

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from src.customer_flow import CustomerSession, handle_customer_message


# ============================================================
# Load LLM (GPT-4.1)
# ============================================================

def load_llm():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    return client


class GPTWrapper:
    def __init__(self, client):
        self.client = client

    def invoke(self, messages):
        response = self.client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            temperature=0.3
        )
        return response.choices[0].message


# ============================================================
# Load RAG Vector Store
# ============================================================

def load_rag():
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )
    return FAISS.load_local(
        "rag_index",
        embeddings,
        allow_dangerous_deserialization=True
    )



# ============================================================
# CLI Customer Chat
# ============================================================

def main():
    print("🤖 AI Customer Support (type 'exit' to quit)\n")

    # Load LLM
    llm_client = load_llm()
    llm = GPTWrapper(llm_client)

    # Load RAG once
    rag_store = load_rag()

    # Initialize session
    session = CustomerSession()
    session.rag = rag_store  # 🔹 attach RAG to session

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("👋 شكراً لتواصلك معنا")
            break

        reply = handle_customer_message(
            user_text=user_input,
            session=session,
            llm=llm
        )

        print("\nAgent:", reply, "\n")


if __name__ == "__main__":
    main()