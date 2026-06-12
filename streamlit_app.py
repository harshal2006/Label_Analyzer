"""
Streamlit UI for the Nutrition Label Analyzer.

Run with:
    streamlit run streamlit_app.py

Make sure the FastAPI backend is running on http://127.0.0.1:8000.
"""

import re

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE = "http://127.0.0.1:8000"
UPLOAD_ENDPOINT = f"{API_BASE}/upload"
HEALTH_ENDPOINT = f"{API_BASE}/health"

ALLOWED_TYPES = ["jpg", "jpeg", "png", "webp"]

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Nutrition Label Analyzer",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for a premium look
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* ── Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Root variables ── */
    :root {
        --primary: #6366f1;
        --primary-light: #818cf8;
        --primary-dark: #4f46e5;
        --accent: #06d6a0;
        --accent-dark: #05b384;
        --bg-dark: #0f0f1a;
        --bg-card: #1a1a2e;
        --bg-card-hover: #22223a;
        --text-primary: #f0f0f5;
        --text-secondary: #a0a0b8;
        --border: #2a2a42;
        --success: #22c55e;
        --error: #ef4444;
        --warning: #f59e0b;
    }

    /* ── Global ── */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif !important;
    }

    /* ── Main header ── */
    .main-header {
        text-align: center;
        padding: 2rem 0 1rem;
    }
    .main-header h1 {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, var(--primary-light), var(--accent));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .main-header p {
        color: var(--text-secondary);
        font-size: 1.1rem;
        font-weight: 300;
    }

    /* ── Status badge ── */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.35rem 0.85rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .status-online {
        background: rgba(34, 197, 94, 0.15);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.25);
    }
    .status-offline {
        background: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.25);
    }

    /* ── Result card ── */
    .result-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .result-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(99, 102, 241, 0.12);
    }
    .result-card h3 {
        margin: 0 0 0.8rem;
        font-weight: 700;
        font-size: 1.15rem;
    }

    /* ── Nutrition table ── */
    .nutrition-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--border);
    }
    .nutrition-table th {
        padding: 0.75rem 1rem;
        text-align: left;
        font-weight: 600;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        background: rgba(99, 102, 241, 0.1);
        color: var(--primary-light);
    }
    .nutrition-table td {
        padding: 0.7rem 1rem;
        font-size: 0.95rem;
        border-top: 1px solid var(--border);
    }
    .nutrition-table tr:hover td {
        background: rgba(99, 102, 241, 0.04);
    }

    /* ── Info box ── */
    .info-box {
        background: rgba(99, 102, 241, 0.08);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin: 0.8rem 0;
        font-size: 0.92rem;
    }
    .info-box strong {
        color: var(--primary-light);
    }

    /* ── Upload area styling ── */
    [data-testid="stFileUploader"] {
        border-radius: 16px;
    }

    /* ── Sidebar styling ── */
    [data-testid="stSidebar"] {
        border-right: 1px solid var(--border);
    }

    /* ── Metric cards ── */
    .metric-row {
        display: flex;
        gap: 0.8rem;
        margin: 0.5rem 0;
        flex-wrap: wrap;
    }
    .metric-card {
        flex: 1;
        min-width: 100px;
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.9rem 1rem;
        text-align: center;
    }
    .metric-card .label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-secondary);
        margin-bottom: 0.25rem;
    }
    .metric-card .value {
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--accent);
    }

    /* ── Divider ── */
    .styled-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--border), transparent);
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

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
    resp = requests.post(UPLOAD_ENDPOINT, files=files, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_nutrition_values(ocr_text: str) -> list[dict]:
    """Extract nutrient-value pairs from OCR text using regex heuristics."""
    nutrients = []
    lines = ocr_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.lower().startswith("ingredients") or line.lower().startswith("contains"):
            continue
        # Match patterns like "Protein 24g" or "Calories 120"
        match = re.match(r"^(.+?)\s+([\d.,]+\s*[a-zA-Z%]*)\s*$", line)
        if match:
            nutrients.append({
                "nutrient": match.group(1).strip(),
                "value": match.group(2).strip(),
            })
    return nutrients


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.markdown("---")

    # Backend status
    is_healthy = check_backend_health()
    if is_healthy:
        st.markdown(
            '<span class="status-badge status-online">● Backend Online</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="status-badge status-offline">● Backend Offline</span>',
            unsafe_allow_html=True,
        )
        st.warning("Start the FastAPI server first:\n```\nuvicorn app.main:app --reload\n```")

    st.markdown("---")

    st.markdown("### 📋 About")
    st.markdown(
        "Upload a photo of a **nutrition / supplement label** and the "
        "system will extract the text using OCR."
    )

    st.markdown("---")
    st.markdown("### 🛠️ API Endpoints")
    st.code("POST  /upload\nGET   /health\nGET   /docs", language="text")

    st.markdown("---")
    st.caption("Nutrition Label Analyzer v0.1.0")


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <h1>🏷️ Nutrition Label Analyzer</h1>
    <p>Upload a nutrition label image · Get instant OCR extraction</p>
</div>
<div class="styled-divider"></div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Two-column layout
# ---------------------------------------------------------------------------
col_upload, col_result = st.columns([1, 1], gap="large")

with col_upload:
    st.markdown("### 📤 Upload Image")
    uploaded_file = st.file_uploader(
        "Choose a nutrition label image",
        type=ALLOWED_TYPES,
        help="Supported formats: JPG, JPEG, PNG, WebP",
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        st.image(uploaded_file, caption=f"📎 {uploaded_file.name}", use_container_width=True)

        st.markdown(f"""
        <div class="info-box">
            <strong>File:</strong> {uploaded_file.name}<br>
            <strong>Size:</strong> {uploaded_file.size / 1024:.1f} KB<br>
            <strong>Type:</strong> {uploaded_file.type}
        </div>
        """, unsafe_allow_html=True)

        analyze_btn = st.button(
            "🔍  Analyze Label",
            type="primary",
            use_container_width=True,
        )
    else:
        analyze_btn = False
        st.markdown("""
        <div class="info-box" style="text-align: center; padding: 2rem;">
            <p style="font-size: 2.5rem; margin-bottom: 0.5rem;">📷</p>
            <p style="margin: 0;">Drag & drop or click to upload a nutrition label image</p>
        </div>
        """, unsafe_allow_html=True)

with col_result:
    st.markdown("### 📊 Analysis Results")

    if analyze_btn and uploaded_file is not None:
        if not is_healthy:
            st.error("⚠️ The backend server is not running. Please start it first.")
        else:
            with st.spinner("🔬 Analyzing your nutrition label…"):
                try:
                    file_bytes = uploaded_file.getvalue()
                    result = upload_image(file_bytes, uploaded_file.name)

                    if result.get("success"):
                        st.success("✅ Analysis complete!")

                        # ── Metrics row ──
                        ocr_text = result.get("ocr_text", "")
                        nutrients = parse_nutrition_values(ocr_text)

                        m1, m2, m3 = st.columns(3)
                        m1.metric("Upload ID", f"#{result.get('upload_id', '—')}")
                        m2.metric("Lines Found", len(ocr_text.strip().split("\n")) if ocr_text else 0)
                        m3.metric("Nutrients", len(nutrients))

                        st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

                        # ── Nutrition table ──
                        if nutrients:
                            st.markdown("#### 🧪 Parsed Nutrients")
                            table_rows = "".join(
                                f"<tr><td>{n['nutrient']}</td><td><strong>{n['value']}</strong></td></tr>"
                                for n in nutrients
                            )
                            st.markdown(f"""
                            <table class="nutrition-table">
                                <thead>
                                    <tr><th>Nutrient</th><th>Value</th></tr>
                                </thead>
                                <tbody>{table_rows}</tbody>
                            </table>
                            """, unsafe_allow_html=True)

                        st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

                        # ── Raw OCR text ──
                        st.markdown("#### 📝 Raw OCR Text")
                        st.code(ocr_text, language="text")

                        # ── Additional details ──
                        with st.expander("🗂️ Full API Response"):
                            st.json(result)

                    else:
                        st.error("❌ The server returned an unsuccessful response.")
                        st.json(result)

                except requests.HTTPError as exc:
                    st.error(f"❌ Server error: {exc.response.status_code}")
                    try:
                        st.json(exc.response.json())
                    except Exception:
                        st.text(exc.response.text)
                except requests.ConnectionError:
                    st.error("❌ Could not connect to the backend. Is the FastAPI server running?")
                except Exception as exc:
                    st.error(f"❌ Unexpected error: {exc}")
    else:
        st.markdown("""
        <div class="result-card" style="text-align: center; padding: 3rem 1.5rem;">
            <p style="font-size: 3rem; margin-bottom: 0.5rem;">🔬</p>
            <h3 style="margin-bottom: 0.5rem;">Ready to Analyze</h3>
            <p style="color: var(--text-secondary); font-size: 0.95rem;">
                Upload an image and click <strong>"Analyze Label"</strong> to extract nutrition data.
            </p>
        </div>
        """, unsafe_allow_html=True)


