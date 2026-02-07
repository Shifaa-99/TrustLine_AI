import os
from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

class GPTWrapper:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def invoke(self, messages):
        resp = self.client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            temperature=0.3
        )
        return resp.choices[0].message

def make_llm():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return GPTWrapper(api_key)

def load_rag(index_dir: str = "rag_index"):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return FAISS.load_local(index_dir, embeddings, allow_dangerous_deserialization=True)
