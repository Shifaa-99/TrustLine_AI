import streamlit as st
from src.config import ADMIN_USERS

ROLE_ADMIN = "admin"


def init_auth_state():
    if "auth" not in st.session_state:
        st.session_state.auth = {
            "is_logged_in": False,
            "role": None,
            "username": None,
        }


def is_logged_in() -> bool:
    init_auth_state()
    return bool(st.session_state.auth.get("is_logged_in"))


def current_user():
    init_auth_state()
    return st.session_state.auth


def logout():
    init_auth_state()
    st.session_state.auth = {"is_logged_in": False, "role": None, "username": None}
    st.toast("Logged out ✅")


def logout_button(label: str = "Logout"):
    init_auth_state()
    if is_logged_in():
        if st.button(label):
            logout()
            st.rerun()


def _do_login(username: str, password: str) -> bool:
    users = ADMIN_USERS or {}
    return (username in users) and (users[username] == password)


def login_ui(title: str = "🔐 Admin Login", subtitle: str = "Authorized personnel only"):
    """
    Full-size login UI (can be used on a dedicated area).
    """
    init_auth_state()

    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)

    st.markdown("**Role:** Admin")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", type="primary", key="login_submit"):
        if _do_login(username.strip(), password):
            st.session_state.auth = {"is_logged_in": True, "role": ROLE_ADMIN, "username": username.strip()}
            st.success("Welcome Admin ✅")
            st.rerun()
        else:
            st.error("Invalid username or password.")


def login_ui_inline():
    """
    Compact login UI to be placed inside right panel/card.
    """
    init_auth_state()

    st.markdown("**Login**")
    username = st.text_input("Username", key="login_username_inline")
    password = st.text_input("Password", type="password", key="login_password_inline")

    if st.button("Login", type="primary", key="login_submit_inline"):
        if _do_login(username.strip(), password):
            st.session_state.auth = {"is_logged_in": True, "role": ROLE_ADMIN, "username": username.strip()}
            st.success("Welcome Admin ✅")
            st.rerun()
        else:
            st.error("Invalid username or password.")
    
            


def require_role(*roles) -> bool:
    """
    Guard function: stops execution if user is not logged in / not allowed.
    DOES NOT render login UI (UI should decide where to show login).
    """
    init_auth_state()
    auth = st.session_state.auth

    if not auth.get("is_logged_in"):
        st.error("Admin access requires login.")
        st.stop()

    if roles and auth.get("role") not in roles:
        st.error("You do not have access to this section.")
        st.stop()

    return True
