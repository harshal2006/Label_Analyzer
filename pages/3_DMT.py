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

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
ADMIN_UPLOADS_ENDPOINT = f"{API_BASE}/admin/uploads"
REPORT_ENDPOINT = f"{API_BASE}/report"

st.set_page_config(
    page_title="Data Management Tool",
    page_icon="🗂️",
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
st.markdown("## 🗂️ Data Management Tool")
st.caption("View, download reports for, or delete your uploaded nutrition labels.")
st.markdown("---")

# ---------------------------------------------------------------------------
# Fetch uploads
# ---------------------------------------------------------------------------
try:
    resp = requests.get(ADMIN_UPLOADS_ENDPOINT, headers=_auth_headers(), timeout=15)
    resp.raise_for_status()
    uploads = resp.json()
except requests.ConnectionError:
    st.error("❌ Could not connect to the backend. Is the FastAPI server running?")
    st.stop()
except requests.HTTPError as exc:
    st.error(f"❌ Failed to load uploads: {exc.response.status_code} — {exc.response.text[:300]}")
    st.stop()
except Exception as exc:
    st.error(f"❌ Unexpected error: {exc}")
    st.stop()

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
if not uploads:
    st.info("No uploads yet. Head to the main page to upload a nutrition label image.")
    st.stop()

# Summary table
import pandas as pd

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
for upload in uploads:
    uid = upload["id"]
    filename = upload["filename"]
    status = upload["status"]

    col_info, col_download, col_delete = st.columns([4, 2, 2])

    with col_info:
        status_icon = "✅" if status == "analysed" else "⏳"
        st.markdown(f"**#{uid}** — {filename}  {status_icon} _{status}_")

    with col_download:
        if status == "analysed":
            if st.button("📄 Download report", key=f"dl_{uid}", use_container_width=True):
                try:
                    report_resp = requests.get(
                        f"{REPORT_ENDPOINT}/{uid}/download",
                        headers=_auth_headers(),
                        timeout=120,
                    )
                    if report_resp.status_code == 200:
                        st.download_button(
                            label="⬇️ Save PDF",
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
        if st.button("🗑️ Delete", key=f"del_{uid}", use_container_width=True):
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
