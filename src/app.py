import os
import uuid
from pathlib import Path

import streamlit as st
import customer_flow, config, complaint_manager

from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from auth import init_auth_state, login_ui_inline, logout
from ui import app_header
from customer_flow import CustomerSession, handle_customer_message
from config import COMPLAINT_IMAGES_DIR

import re


# =========================
# Language helper (ONLY for uploader text)
# =========================
def _detect_user_lang(messages) -> str:
    """
    Detect language from LAST user message:
    returns: "ar" | "en" | "bi"
    """
    last_user = ""
    for m in reversed(messages or []):
        if m.get("role") == "user":
            last_user = (m.get("content") or "").strip()
            break

    if not last_user:
        return "bi"

    if re.search(r"[\u0600-\u06FF]", last_user):
        return "ar"
    if re.search(r"[A-Za-z]", last_user):
        return "en"
    return "bi"


def _t(lang: str, ar: str, en: str) -> str:
    if lang == "ar":
        return ar
    if lang == "en":
        return en
    return f"{ar} / {en}"


st.sidebar.caption(f"Welcome in mini TrustLine System")
st.sidebar.caption(f"The System will be Coming Soon")
st.sidebar.caption(f"ان شاء الله ❤️❤️❤️")
st.sidebar.caption(f"thank U")

# =========================
# Page Config
# =========================
st.set_page_config(
    page_title="TrustLine AI • Customer Support",
    page_icon="💬",
    layout="wide"
)

init_auth_state()

# =========================
# Branding / Header
# =========================
app_header("TrustLine AI", "Customer Support Assistant")

# =========================
# Helpers: LLM + RAG
# =========================
class GPTWrapper:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def invoke(self, messages):
        resp = self.client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            temperature=0.3
        )
        # customer_flow expects .content
        return resp.choices[0].message

def make_llm():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return GPTWrapper(api_key)

def load_rag():
    # expects rag_index folder exists
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return FAISS.load_local("rag_index", embeddings, allow_dangerous_deserialization=True)

# =========================
# Session init
# =========================
if "llm" not in st.session_state:
    st.session_state.llm = make_llm()

if "rag_store" not in st.session_state:
    try:
        st.session_state.rag_store = load_rag()
    except Exception:
        st.session_state.rag_store = None

if "cs_session" not in st.session_state:
    st.session_state.cs_session = CustomerSession()
    st.session_state.cs_session.rag = st.session_state.rag_store

if "messages" not in st.session_state:
    st.session_state.messages = []

# Detect language from last user message (ONLY for uploader copy)
user_lang = _detect_user_lang(st.session_state.messages)

# =========================
# Sidebar: Admin Login + Admin Link
# =========================
with st.sidebar:
    st.markdown("### Admin Access")

    auth = st.session_state.auth

    if not auth.get("is_logged_in"):
        login_ui_inline()
        st.caption("Admin login only. Customers can use chat without login.")
    else:
        st.success(f"Logged in as: {auth.get('username')} (admin)")
        if st.button("Open Admin Dashboard", type="primary"):
            st.switch_page("pages/1_🧑‍💼_Admin_Dashboard.py")

        if st.button("Logout"):
            logout()
            st.rerun()

    st.divider()
    st.write("**LLM:**", "✅ connected" if st.session_state.llm else "❌ missing OPENAI_API_KEY")
    st.write("**RAG:**", "✅ loaded" if st.session_state.rag_store else "❌ not loaded")
    from config import COMPLAINTS_FILE
    st.sidebar.write("Complaints file:", str(COMPLAINTS_FILE))

# =========================
# Main: Customer Chat (always)
# =========================
st.markdown("### 💬 Customer Chat")

# عرض الرسائل
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])

# =========================
# Attach Images (ONLY when needed)
# =========================
cs = st.session_state.cs_session

order_status = (cs.order_data or {}).get("status", "") or ""
cs_state = getattr(cs.state, "value", cs.state)

awaiting_images = bool(getattr(cs, "awaiting_images", False))
pending_images = (getattr(cs, "pending_image_paths", []) or [])

should_show_uploader = (
    cs_state == "verified"
    and order_status == "delivered"
    and awaiting_images
    and not pending_images
)

if should_show_uploader:
    st.markdown("### 📎 Attach Images (for damage/missing complaints)")
    st.caption(_t(
        user_lang,
        "ارفق صور (PNG/JPG) ثم اكتب (تأكيد/تم) لإرسال الشكوى.",
        "Attach images (PNG/JPG), then type (confirm/yes) to submit the complaint."
    ))

    COMPLAINT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    uploads = st.file_uploader(
        _t(user_lang, "ارفق صور (PNG/JPG)", "Attach images (PNG/JPG)"),
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="complaint_uploader"
    )

    if uploads:
        saved_paths = []
        for f in uploads:
            ext = Path(f.name).suffix.lower()
            filename = f"{uuid.uuid4().hex}{ext}"
            out_path = COMPLAINT_IMAGES_DIR / filename
            with open(out_path, "wb") as w:
                w.write(f.getbuffer())
            saved_paths.append(str(out_path))

        cs.pending_image_paths = saved_paths

        st.success(_t(
            user_lang,
            f"✅ تم إرفاق {len(saved_paths)} صورة. الآن اكتب (تأكيد/تم) لإرسال الشكوى.",
            f"✅ {len(saved_paths)} image(s) attached. Now type (confirm/yes) to submit."
        ))

    st.divider()


# إدخال الشات
prompt = st.chat_input("اكتب رسالتك هنا… / Type your message…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    if st.session_state.llm is None:
        reply = "⚠️ OPENAI_API_KEY غير موجود. رجاءً ضيفه بالبيئة."
    else:
        reply = handle_customer_message(
            user_text=prompt,
            session=st.session_state.cs_session,
            llm=st.session_state.llm
        )

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
