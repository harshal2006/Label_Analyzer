"""
Supabase Auth login / signup page for Streamlit.

Provides ``show_auth_page()`` which renders a sign-in / create-account
form using plain Streamlit components.  On successful authentication the
access token, user ID, and user email are stored in ``st.session_state``
and the app is rerun so the main page renders.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import logging

import streamlit as st
from supabase import create_client

logger = logging.getLogger(__name__)

def get_secret(key):
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.getenv(key)

SUPABASE_URL: str = get_secret("SUPABASE_URL") or ""
SUPABASE_ANON_KEY: str = get_secret("SUPABASE_ANON_KEY") or ""

# Debug: confirm env vars are loaded (remove after fix is confirmed)
logger.info("SUPABASE_URL first 10: %s", SUPABASE_URL[:10])
logger.info("SUPABASE_ANON_KEY first 10: %s", SUPABASE_ANON_KEY[:10])


def _get_supabase_client():
    """Return a Supabase client initialised with the anon key."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        st.error("WARNING: SUPABASE_URL and SUPABASE_ANON_KEY must be set in Streamlit secrets or .env")
        st.stop()
    # Debug: log what we're passing to create_client
    logger.info("Creating Supabase client with URL=%s... KEY=%s...", SUPABASE_URL[:10], SUPABASE_ANON_KEY[:10])
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return client


def show_auth_page():
    """Render the login / signup page and block further execution."""
    st.write("SUPABASE_URL from secrets:", bool(st.secrets.get("SUPABASE_URL")))
    st.write("SUPABASE_ANON_KEY from secrets:", bool(st.secrets.get("SUPABASE_ANON_KEY")))
    st.write("SUPABASE_URL from env:", bool(os.getenv("SUPABASE_URL")))

    # ── Centered header ──
    st.markdown(
        """
        <div style="text-align: center; padding: 3rem 0 1rem;">
            <h1 style="font-size: 2.4rem; font-weight: 800; color: var(--primary);">
                Nutrition Label Analyzer
            </h1>
            <p style="color: var(--text-color); font-size: 1.05rem;">Sign in to continue</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Tabs ──
    tab_signin, tab_signup = st.tabs(["Sign in", "Create account"])

    # ────────────────────────────── Sign In ──────────────────────────────
    with tab_signin:
        with st.form("signin_form"):
            email = st.text_input("Email", key="signin_email")
            password = st.text_input("Password", type="password", key="signin_password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                try:
                    client = _get_supabase_client()
                    resp = client.auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )
                    session = resp.session
                    user = resp.user
                    if session and user:
                        st.session_state["access_token"] = session.access_token
                        st.session_state["user_id"] = user.id
                        st.session_state["user_email"] = user.email
                        st.rerun()
                    else:
                        st.error("Sign-in failed — no session returned.")
                except Exception as exc:
                    st.error(f"Sign-in failed: {exc}")

    # ────────────────────────────── Sign Up ──────────────────────────────
    with tab_signup:
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input(
                "Confirm password", type="password", key="signup_confirm"
            )
            signup_submitted = st.form_submit_button(
                "Create account", use_container_width=True
            )

        if signup_submitted:
            if not new_email or not new_password:
                st.error("Please fill in all fields.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    client = _get_supabase_client()
                    client.auth.sign_up(
                        {"email": new_email, "password": new_password}
                    )
                    st.success("Account created! Please sign in.")
                except Exception as exc:
                    st.error(f"Sign-up failed: {exc}")
