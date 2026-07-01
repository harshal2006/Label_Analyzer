"""
Streamlit UI for the Nutrition Label Analyzer.

Run with:
    streamlit run streamlit_app.py

Make sure the FastAPI backend is running on http://127.0.0.1:8000.
"""

import os
import re

import requests
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def get_secret(key):
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError, Exception):
        return os.getenv(key)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE = get_secret("BACKEND_URL") or "http://127.0.0.1:8000"
UPLOAD_ENDPOINT = f"{API_BASE}/upload"
HEALTH_ENDPOINT = f"{API_BASE}/health"
REPORT_ENDPOINT = f"{API_BASE}/report"

ALLOWED_TYPES = ["jpg", "jpeg", "png", "webp"]

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Nutrition Label Analyzer",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — editorial clinical-warm palette
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* ── Google Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Root variables (Charcoal + Terracotta) ── */
    :root {
        --primary: #C2553A;
        --primary-light: #D4785C;
        --primary-dark: #9E3F27;
        --accent: #D4785C;
        --accent-dark: #9E3F27;

        --text-heading: #1C1C1E;
        --text-body: #3A3A3C;
        --text-muted: #8E8E93;
        --surface: #F5F3F0;
        --surface-warm: #FBF7F4;
        --border-subtle: rgba(28, 28, 30, 0.08);

        --success: #2D7D46;
        --error: #C23838;
        --warning: #D4883A;
    }

    /* ── Global typography ── */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--text-body);
    }

    h1, h2, h3, h4, h5, h6,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3 {
        font-family: 'DM Sans', sans-serif !important;
        color: var(--text-heading);
    }

    /* ── Sidebar Branding ── */
    .sidebar-brand {
        font-family: 'DM Sans', sans-serif;
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--primary);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.15rem;
    }
    .sidebar-tagline {
        font-family: 'Inter', sans-serif;
        font-size: 0.82rem;
        color: var(--text-muted);
        font-weight: 400;
        margin-bottom: 1.5rem;
        letter-spacing: 0.01em;
    }

    /* ── Main header ── */
    .main-header {
        text-align: center;
        padding: 2rem 0 1rem;
    }
    .main-header h1 {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 2.4rem;
        font-weight: 700;
        color: var(--text-heading);
        margin-bottom: 0.4rem;
        letter-spacing: -0.01em;
    }
    .main-header p {
        color: var(--text-muted);
        font-size: 1.05rem;
        font-weight: 400;
    }

    /* ── Status badge ── */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.3rem 0.75rem;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        font-family: 'Inter', sans-serif;
    }
    .status-online {
        background: rgba(45, 125, 70, 0.08);
        color: var(--success);
        border: 1px solid rgba(45, 125, 70, 0.25);
    }
    .status-offline {
        background: rgba(194, 56, 56, 0.08);
        color: var(--error);
        border: 1px solid rgba(194, 56, 56, 0.25);
    }

    /* ── Info box ── */
    .info-box {
        background: var(--surface-warm);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin: 0.8rem 0;
        font-size: 0.95rem;
        color: var(--text-body);
    }

    /* ── Upload area styling ── */
    [data-testid="stFileUploader"] {
        border-radius: 10px;
        border: 1.5px dashed rgba(194, 85, 58, 0.3);
        padding: 1rem;
        background-color: var(--surface-warm);
    }

    /* ── Sidebar styling ── */
    [data-testid="stSidebar"] {
        border-right: 1px solid var(--border-subtle);
    }

    /* ── Divider ── */
    .styled-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--border-subtle), rgba(194, 85, 58, 0.2), var(--border-subtle), transparent);
        margin: 1rem 0 2rem 0;
    }

    .sidebar-divider {
        height: 1px;
        background: var(--border-subtle);
        margin: 1.5rem 0;
    }

    /* ── Streamlit metric overrides ── */
    [data-testid="stMetricLabel"] {
        font-family: 'Inter', sans-serif !important;
        color: var(--text-muted) !important;
        font-size: 0.82rem !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    [data-testid="stMetricValue"] {
        font-family: 'DM Sans', sans-serif !important;
        color: var(--text-heading) !important;
    }

    /* ── Button refinements ── */
    .stButton > button[kind="primary"] {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600;
        letter-spacing: 0.01em;
        border-radius: 8px;
    }

    /* ── Streamlit tab overrides ── */
    .stTabs [data-baseweb="tab"] {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Auth gate — show login page if not authenticated
# ---------------------------------------------------------------------------
if not st.session_state.get("access_token") or not st.session_state.get("user_id"):
    from auth_page import show_auth_page
    show_auth_page()
    st.stop()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _auth_headers() -> dict:
    """Return the Authorization header dict."""
    return {"Authorization": f"Bearer {st.session_state['access_token']}"}


def check_backend_health() -> bool:
    """Ping the FastAPI /health endpoint."""
    try:
        resp = requests.get(HEALTH_ENDPOINT, timeout=3)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


def upload_image(file_bytes: bytes, filename: str) -> dict:
    """POST the image to the FastAPI /upload endpoint."""
    files = {"file": (filename, file_bytes)}
    resp = requests.post(UPLOAD_ENDPOINT, files=files, headers=_auth_headers(), timeout=120)
    resp.raise_for_status()
    return resp.json()

def parse_nutrient_value(value_str: str | float) -> tuple[str, str | None]:
    """
    Split a string like '25g 10% DV' into ('25g', '10% DV')
    """
    value_str = str(value_str) if value_str is not None else ""
    match = re.search(r'([\d.,]+(?:mcg|mg|g|kcal|%))?\s*(\d+%\s*DV)?', value_str, re.IGNORECASE)
    if match:
        val = match.group(1) or value_str
        dv = match.group(2)
        if dv:
            # Clean up the original string by removing the DV part to get just the value
            val = value_str.replace(dv, "").strip()
            return val, dv
    return value_str, None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="sidebar-brand">Label Analyzer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-tagline">AI-Powered Nutrition Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # Backend status
    is_healthy = check_backend_health()
    if is_healthy:
        st.markdown(
            '<span class="status-badge status-online">Backend Online</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="status-badge status-offline">Backend Offline</span>',
            unsafe_allow_html=True,
        )
        st.warning("Start the FastAPI server first:\n```\nuvicorn app.main:app --reload\n```")

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    
    # Navigation happens automatically via pages/ directory in Streamlit

    # Bottom footer area (using empty containers to push it down if needed, but Streamlit sidebar flows top-to-bottom)
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    user_email = st.session_state.get("user_email", "Unknown")
    st.markdown(f"**Signed in as:**<br>`{user_email}`", unsafe_allow_html=True)
    if st.button("Sign Out", use_container_width=True):
        for key in ("access_token", "user_id", "user_email"):
            st.session_state.pop(key, None)
        st.rerun()

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.caption("Powered by Groq + PaddleOCR")


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <h1>Nutrition Label Analyzer</h1>
    <p>Upload a product label to get instant AI-powered nutritional insights</p>
</div>
<div class="styled-divider"></div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Two-column layout
# ---------------------------------------------------------------------------
col_upload, col_settings = st.columns([1, 1], gap="large")

with col_upload:
    st.markdown("### Upload Label")
    uploaded_file = st.file_uploader(
        "Choose a nutrition label image",
        type=ALLOWED_TYPES,
        help="Supported formats: JPG, JPEG, PNG, WebP"
    )

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded label", use_container_width=True)

with col_settings:
    st.markdown("### Analysis Settings")
    st.info("**What the Analyzer Checks:**\n\n- OCR text extraction from the label image\n- Nutrient table parsing (Calories, Macros, Micros)\n- AI ingredient breakdown & health scoring\n- Identification of common allergens\n- Detection of harmful additives")
    
    analyze_btn = False
    if uploaded_file is not None:
        analyze_btn = st.button("Analyze Label", type="primary", use_container_width=True)
    else:
        st.button("Analyze Label", type="primary", use_container_width=True, disabled=True)

# ---------------------------------------------------------------------------
# Results Section
# ---------------------------------------------------------------------------
if analyze_btn and uploaded_file is not None:
    if not is_healthy:
        st.error("WARNING: The backend server is not running. Please start it first.")
    else:
        with st.spinner("Analyzing label... This may take 30-60 seconds"):
            try:
                file_bytes = uploaded_file.getvalue()
                result = upload_image(file_bytes, uploaded_file.name)

                if result.get("success"):
                    st.session_state["analysis_result"] = result
                else:
                    detail = result.get("detail", "Unknown error")
                    st.error(f"ERROR: The server returned an unsuccessful response: {detail}")

            except requests.HTTPError as exc:
                st.error(f"ERROR: Server error: {exc.response.status_code}")
            except requests.ConnectionError:
                st.error("ERROR: Could not connect to the backend.")
            except Exception as exc:
                st.error(f"ERROR: Unexpected error: {exc}")

if "analysis_result" in st.session_state:
    st.markdown("---")
    st.markdown("## Analysis Results")
    
    result = st.session_state["analysis_result"]
    analysis = result.get("analysis", {})
    nutrients = result.get("nutrients", [])
    current_upload_id = result.get("upload_id")

    # 1. Product Summary
    summary = analysis.get("summary", "")
    if summary:
        st.success(f"**Product Summary:** {summary}")

    # 2. Nutrients section
    if nutrients:
        st.markdown("### Key Nutrients")
        # Target specific nutrients to display prominently
        target_keys = ["Calories", "Protein", "Carbohydrate", "Fat", "Sodium", "Fiber"]
        
        # Build a map of found nutrients
        nutrient_map = {n["name"].lower(): n["value"] for n in nutrients}
        
        cols = st.columns(3)
        col_idx = 0
        for tk in target_keys:
            # Try to find a fuzzy match for the target key
            found_key = next((k for k in nutrient_map.keys() if tk.lower() in k), None)
            if found_key:
                raw_val = nutrient_map[found_key]
                val, dv = parse_nutrient_value(raw_val)
                cols[col_idx % 3].metric(label=tk, value=val, delta=dv, delta_color="off")
                col_idx += 1
                
        # If we found less than 3 things, just show the first few from the array
        if col_idx == 0:
            for i, n in enumerate(nutrients[:6]):
                val, dv = parse_nutrient_value(n["value"])
                cols[i % 3].metric(label=n["name"], value=val, delta=dv, delta_color="off")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Allergens
    ingredients_list = analysis.get("ingredients", [])
    allergens_found = [ing["name"] for ing in ingredients_list if ing.get("is_allergen")]
    
    if allergens_found:
        st.error(f"WARNING: **Allergens Detected:** {', '.join(allergens_found)}")
    else:
        st.success("**No common allergens detected**")

    # Warnings
    warnings = analysis.get("warnings", [])
    if warnings:
        for w in warnings:
            st.warning(f"WARNING: {w}")

    # 4. Ingredients
    if ingredients_list:
        with st.expander("View All Ingredients"):
            # Create a dataframe for nice tabular display
            df_ing = pd.DataFrame(ingredients_list)
            # Filter and rename columns for display
            if not df_ing.empty:
                display_cols = {"name": "Ingredient", "purpose": "Purpose"}
                if "is_allergen" in df_ing.columns:
                    display_cols["is_allergen"] = "Allergen?"
                df_ing_display = df_ing[list(display_cols.keys())].rename(columns=display_cols)
                st.table(df_ing_display)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 5. Download Report button
    if current_upload_id:
        if (
            "report_pdf" in st.session_state
            and st.session_state.get("report_upload_id") == current_upload_id
        ):
            st.download_button(
                label="Download PDF Report",
                data=st.session_state["report_pdf"],
                file_name=f"report_{current_upload_id}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_pdf_btn",
            )
        else:
            if st.button(
                "Generate & Download Report",
                type="primary",
                use_container_width=True,
                key="generate_report_btn",
            ):
                with st.spinner("Generating PDF report…"):
                    try:
                        report_resp = requests.get(
                            f"{REPORT_ENDPOINT}/{current_upload_id}/download",
                            headers=_auth_headers(),
                            timeout=120,
                        )
                        if report_resp.status_code == 200:
                            st.session_state["report_pdf"] = report_resp.content
                            st.session_state["report_upload_id"] = current_upload_id
                            st.rerun()
                        else:
                            st.error(f"ERROR: Report generation failed: {report_resp.text}")
                    except Exception as report_exc:
                        st.error(f"ERROR: {report_exc}")
