"""
Label Compliance Checker Streamlit Page.

Provides a quick pass/fail compliance check against mandatory label requirements.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import requests
import streamlit as st

def get_secret(key):
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.getenv(key)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE = get_secret("BACKEND_URL") or "http://127.0.0.1:8000"
CHECK_ENDPOINT = f"{API_BASE}/check-label"
ALLOWED_TYPES = ["jpg", "jpeg", "png", "webp"]

st.set_page_config(
    page_title="Label Compliance Checker",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Auth guard — redirect to main page if not logged in
# ---------------------------------------------------------------------------
if not st.session_state.get("access_token") or not st.session_state.get("user_id"):
    st.warning("Please sign in from the main page to use this feature.")
    st.stop()


def _auth_headers() -> dict:
    """Return the Authorization header dict."""
    return {"Authorization": f"Bearer {st.session_state['access_token']}"}


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.markdown("""
<div style="text-align: center; padding: 1.5rem 0 1rem;">
    <h1 style="font-size: 2.6rem; font-weight: 800; color: var(--primary); margin-bottom: 0.3rem;">Label Compliance Checker</h1>
    <p style="color: var(--text-color); font-size: 1.1rem; font-weight: 400;">Check if your nutrition label meets mandatory declaration requirements</p>
</div>
""", unsafe_allow_html=True)
st.divider()

# ---------------------------------------------------------------------------
# Upload Section
# ---------------------------------------------------------------------------
col_upload, col_preview = st.columns([1, 1], gap="large")

with col_upload:
    st.markdown("### Upload Label")
    uploaded_file = st.file_uploader(
        "Choose a nutrition label image",
        type=ALLOWED_TYPES,
        help="Supported formats: JPG, JPEG, PNG, WebP"
    )

    analyze_btn = False
    if uploaded_file is not None:
        analyze_btn = st.button("Check Label", type="primary", use_container_width=True)
    else:
        st.button("Check Label", type="primary", use_container_width=True, disabled=True)

with col_preview:
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded label", use_container_width=True)
    else:
        st.info("Upload an image to see the preview here.")

# ---------------------------------------------------------------------------
# API Call and Results
# ---------------------------------------------------------------------------
if analyze_btn and uploaded_file is not None:
    st.divider()
    st.markdown("## Compliance Results")
    
    with st.spinner("Checking label compliance..."):
        try:
            file_bytes = uploaded_file.getvalue()
            files = {"file": (uploaded_file.name, file_bytes)}
            resp = requests.post(CHECK_ENDPOINT, files=files, headers=_auth_headers(), timeout=120)
            
            if resp.status_code == 200:
                result = resp.json()
                
                summary = result.get("summary", "")
                fields = result.get("fields", [])
                
                # 1. Summary
                if summary:
                    st.info(summary)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # 2. Side-by-side columns
                col_found, col_missing = st.columns(2)
                
                with col_found:
                    st.markdown("#### Found on this label")
                    found_fields = [f for f in fields if f.get("found")]
                    if found_fields:
                        for f in found_fields:
                            st.markdown(f"- **{f.get('name')}**: {f.get('note')}")
                    else:
                        st.markdown("_None_")
                        
                with col_missing:
                    st.markdown("#### Not visible in this image")
                    missing_fields = [f for f in fields if not f.get("found")]
                    if missing_fields:
                        for f in missing_fields:
                            st.markdown(f"- **{f.get('name')}** - not visible in this image")
                    else:
                        st.markdown("_None_")
                
                # 4. Divider and caption
                st.divider()
                st.caption("Note: Fields marked as not visible may appear on other sides of the product packaging.")
                
            else:
                try:
                    err_detail = resp.json().get("detail", resp.text)
                except:
                    err_detail = resp.text
                st.error(f"Error: {err_detail}")
                
        except requests.ConnectionError:
            st.error("Could not connect to the backend. Is the FastAPI server running?")
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
