import os
import uuid
import streamlit as st
from pathlib import Path
from config import COMPLAINT_IMAGES_DIR


def _safe_read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def app_header(title: str, subtitle: str = ""):
    base_dir = os.path.dirname(__file__)
    assets_dir = os.path.join(base_dir, "assets")

    css_path = os.path.join(assets_dir, "style.css")
    st.markdown(f"<style>{_safe_read(css_path)}</style>", unsafe_allow_html=True)

    logo_candidates = [
        os.path.join(assets_dir, "TrustLine AI ChatBot.png"),
        os.path.join(assets_dir, "TrustLine AI ChatBot.jpg"),
        os.path.join(assets_dir, "TrustLine AI ChatBot.jpeg"),
        os.path.join(assets_dir, "TrustLine AI ChatBot.svg"),
    ]
    logo_path = next((p for p in logo_candidates if os.path.exists(p)), None)

    c1, c2 = st.columns([1, 6])
    with c1:
        if logo_path:
            st.image(logo_path, use_container_width=True)
    with c2:
        st.markdown(f"## {title}")
        if subtitle:
            st.caption(subtitle)

def sidebar_shell(section_title: str, username: str = "", role: str = ""):
    with st.sidebar:
        st.markdown(f"### {section_title}")
        if username:
            st.write(f"👤 **{username}**")
        if role:
            st.caption(f"Role: {role}")
        st.divider()
