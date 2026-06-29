"""
Data Management Tool (DMT) – Streamlit page.

Lists all uploads for the authenticated user, lets them download
PDF reports or delete uploads via the FastAPI backend.
"""

from dotenv import load_dotenv
load_dotenv()

import os

import requests
import streamlit as st
import pandas as pd

def get_secret(key):
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.getenv(key)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE = get_secret("BACKEND_URL") or "http://127.0.0.1:8000"
ADMIN_UPLOADS_ENDPOINT = f"{API_BASE}/admin/uploads"
REPORT_ENDPOINT = f"{API_BASE}/report"

st.set_page_config(
    page_title="Data Management Tool",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Auth guard — redirect to main page if not logged in
# ---------------------------------------------------------------------------
if not st.session_state.get("access_token") or not st.session_state.get("user_id"):
    st.warning("Please sign in from the main page first.")
    st.stop()


def _auth_headers() -> dict:
    """Return the Authorization header dict."""
    return {"Authorization": f"Bearer {st.session_state['access_token']}"}


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.markdown("""
<div style="text-align: center; padding: 1.5rem 0 1rem;">
    <h1 style="font-size: 2.6rem; font-weight: 800; color: var(--primary); margin-bottom: 0.3rem;">Data Management Tool</h1>
    <p style="color: var(--text-color); font-size: 1.1rem; font-weight: 400;">View, download reports for, or delete your uploaded nutrition labels.</p>
</div>
<div style="height: 2px; background: linear-gradient(90deg, transparent, #66BB6A, transparent); margin: 1rem 0 2rem 0;"></div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Fetch uploads
# ---------------------------------------------------------------------------
col_title, col_refresh = st.columns([5, 1])
with col_refresh:
    # Adding a refresh button at the top right
    st.button("Refresh Data", use_container_width=True)

try:
    resp = requests.get(ADMIN_UPLOADS_ENDPOINT, headers=_auth_headers(), timeout=15)
    resp.raise_for_status()
    uploads = resp.json()
except requests.ConnectionError:
    st.error("Could not connect to the backend. Is the FastAPI server running?")
    st.stop()
except requests.HTTPError as exc:
    st.error(f"Failed to load uploads: {exc.response.status_code} — {exc.response.text[:300]}")
    st.stop()
except Exception as exc:
    st.error(f"Unexpected error: {exc}")
    st.stop()

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
if not uploads:
    st.info("No uploads yet. Head to the main page to upload a nutrition label image.")
    st.stop()

# ---------------------------------------------------------------------------
# Summary row
# ---------------------------------------------------------------------------
total_uploads = len(uploads)
total_reports = sum(1 for u in uploads if u["status"] == "analysed")

m1, m2 = st.columns(2)
m1.metric("Total Uploads", total_uploads)
m2.metric("Reports Generated", total_reports)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
st.markdown("### Uploads History")
df = pd.DataFrame(
    [
        {
            "ID": u["id"],
            "Filename": u["filename"],
            "Date": u["created_at"],
            "Status": u["status"],
        }
        for u in uploads
    ]
)
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Per-upload actions
# ---------------------------------------------------------------------------
st.markdown("### Actions")
for upload in uploads:
    uid = upload["id"]
    filename = upload["filename"]
    status = upload["status"]

    col_info, col_download, col_delete = st.columns([4, 2, 2])

    with col_info:
        status_icon = "[Analysed]" if status == "analysed" else "[Pending]"
        st.markdown(f"**#{uid}** — {filename}  {status_icon} _{status}_")

    with col_download:
        if status == "analysed":
            if st.button("Download report", key=f"dl_{uid}", use_container_width=True):
                try:
                    report_resp = requests.get(
                        f"{REPORT_ENDPOINT}/{uid}/download",
                        headers=_auth_headers(),
                        timeout=120,
                    )
                    if report_resp.status_code == 200:
                        st.download_button(
                            label="Save PDF",
                            data=report_resp.content,
                            file_name=f"report_{uid}.pdf",
                            mime="application/pdf",
                            key=f"save_pdf_{uid}",
                        )
                    else:
                        st.error(f"Failed: {report_resp.status_code}")
                except Exception as exc:
                    st.error(f"Error: {exc}")
        else:
            st.caption("Analysis pending")

    with col_delete:
        if st.button("Delete", key=f"del_{uid}", use_container_width=True):
            try:
                del_resp = requests.delete(
                    f"{ADMIN_UPLOADS_ENDPOINT}/{uid}",
                    headers=_auth_headers(),
                    timeout=15,
                )
                if del_resp.status_code == 204:
                    st.success(f"Deleted upload #{uid}")
                    st.rerun()
                else:
                    st.error(f"Delete failed: {del_resp.status_code}")
            except Exception as exc:
                st.error(f"Error: {exc}")
