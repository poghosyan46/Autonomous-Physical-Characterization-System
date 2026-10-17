"""Ossila SMU — Autonomous Physical Characterization Suite (Streamlit frontend).

UI layer only: all backend calls, file paths and data keys are unchanged.
"""

import json
import os

import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Autonomous SMU Physical Characterization Suite",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# The dashboard is an HTTP client only.  FastAPI owns the serial connection
# and starts the agent in a background task, so this process must never launch
# main.py or access COM3 directly.
API_URL = os.getenv("LAB_API_URL", "http://127.0.0.1:8000").rstrip("/")
API_TIMEOUT = (1, 5)  # (connect timeout, read timeout) in seconds
STATUS_POLL_INTERVAL_SECONDS = 1.0

ACCENT_CYAN = "#38BDF8"
ACCENT_EMERALD = "#34D399"
ACCENT_AMBER = "#FBBF24"
ACCENT_RED = "#F87171"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.stApp {
    background:
        radial-gradient(1100px 620px at 8% -12%, rgba(56,189,248,0.12), transparent 62%),
        radial-gradient(900px 520px at 94% -4%, rgba(52,211,153,0.09), transparent 58%),
        radial-gradient(800px 600px at 50% 110%, rgba(251,191,36,0.05), transparent 60%),
        #090D16;
    color: #F3F4F6;
}

header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }

.block-container {
    padding-top: 1.7rem;
    padding-bottom: 3.2rem;
    max-width: 1520px;
}

/* ---------- Hero ---------- */
.hero {
    position: relative;
    overflow: hidden;
    border-radius: 24px;
    padding: 32px 34px 28px;
    background: linear-gradient(135deg, rgba(56,189,248,0.16) 0%, rgba(52,211,153,0.07) 42%, rgba(15,23,42,0.55) 100%);
    border: 1px solid rgba(148,163,184,0.17);
    box-shadow: 0 30px 70px -40px rgba(0,0,0,0.95), inset 0 1px 0 rgba(255,255,255,0.05);
    margin-bottom: 20px;
}
.hero::after {
    content: "";
    position: absolute;
    top: -170px; right: -90px;
    width: 430px; height: 430px;
    background: radial-gradient(circle, rgba(56,189,248,0.28), transparent 68%);
    filter: blur(12px);
    pointer-events: none;
}
.hero-kicker {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 2.4px;
    text-transform: uppercase;
    color: #38BDF8;
    margin-bottom: 12px;
}
.hero h1 {
    font-size: 2.1rem;
    line-height: 1.16;
    font-weight: 700;
    letter-spacing: -0.7px;
    margin: 0 0 8px 0;
    color: #F3F4F6;
}
.hero p {
    margin: 0;
    max-width: 860px;
    font-size: 0.96rem;
    line-height: 1.6;
    color: #94A3B8;
}
.hero-badges { margin-top: 18px; display: flex; flex-wrap: wrap; gap: 9px; }
.hero-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.9px;
    padding: 5px 11px;
    border-radius: 999px;
    border: 1px solid rgba(148,163,184,0.22);
    background: rgba(9,13,22,0.55);
    color: #CBD5E1;
}
.hero-badge.cyan { border-color: rgba(56,189,248,0.45); color: #7DD3FC; }
.hero-badge.emerald { border-color: rgba(52,211,153,0.45); color: #6EE7B7; }
.hero-badge.amber { border-color: rgba(251,191,36,0.45); color: #FCD34D; }

/* ---------- Glass cards ---------- */
.glass-card {
    background: rgba(15,23,42,0.55);
    backdrop-filter: blur(18px) saturate(140%);
    -webkit-backdrop-filter: blur(18px) saturate(140%);
    border: 1px solid rgba(148,163,184,0.14);
    border-radius: 18px;
    padding: 20px 22px;
    box-shadow: 0 22px 50px -32px rgba(0,0,0,0.95), inset 0 1px 0 rgba(255,255,255,0.035);
    margin-bottom: 16px;
    color: #F3F4F6;
}
.glass-card p { color: #CBD5E1; font-size: 0.9rem; line-height: 1.65; margin: 0 0 8px 0; }
.glass-card p:last-child { margin-bottom: 0; }
.card-cyan { border-left: 3px solid #38BDF8; box-shadow: 0 22px 55px -34px rgba(56,189,248,0.55), inset 0 1px 0 rgba(255,255,255,0.035); }
.card-emerald { border-left: 3px solid #34D399; box-shadow: 0 22px 55px -34px rgba(52,211,153,0.55), inset 0 1px 0 rgba(255,255,255,0.035); }
.card-amber { border-left: 3px solid #FBBF24; box-shadow: 0 22px 55px -34px rgba(251,191,36,0.5), inset 0 1px 0 rgba(255,255,255,0.035); }
.card-indigo { border-left: 3px solid #F87171; box-shadow: 0 22px 55px -34px rgba(248,113,113,0.5), inset 0 1px 0 rgba(255,255,255,0.035); }
.card-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 1.6px;
    color: #94A3B8;
    font-weight: 600;
    margin-bottom: 12px;
}
.card-value { font-size: 1.5rem; font-weight: 600; color: #F3F4F6; letter-spacing: -0.4px; }
.card-note { font-size: 0.8rem; color: #94A3B8; margin-top: 6px; }

/* ---------- Tables ---------- */
.custom-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.86rem;
    overflow: hidden;
    border-radius: 12px;
}
.custom-table thead th {
    text-align: left;
    padding: 11px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    font-weight: 600;
    color: #94A3B8;
    background: rgba(9,13,22,0.72);
    border-bottom: 1px solid rgba(148,163,184,0.18);
}
.custom-table td {
    padding: 10px 14px;
    color: #F3F4F6;
    border-bottom: 1px solid rgba(148,163,184,0.08);
    vertical-align: top;
    line-height: 1.55;
}
.custom-table tbody tr:hover td { background: rgba(56,189,248,0.06); }
.custom-table tbody tr:last-child td { border-bottom: none; }
.custom-table code, .mono {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #7DD3FC;
    background: rgba(56,189,248,0.09);
    border: 1px solid rgba(56,189,248,0.18);
    border-radius: 6px;
    padding: 1px 6px;
}
.proto-block {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    line-height: 1.85;
    color: #A5F3FC;
    background: rgba(2,6,23,0.78);
    border: 1px solid rgba(148,163,184,0.16);
    border-radius: 12px;
    padding: 16px 18px;
    white-space: pre-wrap;
}

/* ---------- Status badges ---------- */
.status-badge-online, .status-badge-offline {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 6px 13px;
    border-radius: 999px;
    margin-bottom: 6px;
}
.status-badge-online {
    color: #6EE7B7;
    background: rgba(52,211,153,0.12);
    border: 1px solid rgba(52,211,153,0.4);
    box-shadow: 0 0 22px -8px rgba(52,211,153,0.75);
}
.status-badge-offline {
    color: #FCA5A5;
    background: rgba(248,113,113,0.12);
    border: 1px solid rgba(248,113,113,0.4);
    box-shadow: 0 0 22px -8px rgba(248,113,113,0.7);
}
.status-badge-online::before, .status-badge-offline::before {
    content: "";
    width: 7px; height: 7px;
    border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 8px currentColor;
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(11,17,29,0.97), rgba(9,13,22,0.99));
    border-right: 1px solid rgba(148,163,184,0.12);
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.4rem; }
.side-head {
    font-size: 1.05rem;
    font-weight: 600;
    letter-spacing: -0.2px;
    color: #F3F4F6;
    margin-bottom: 2px;
}
.side-rule {
    height: 1px;
    margin: 14px 0 4px 0;
    background: linear-gradient(90deg, rgba(56,189,248,0.55), rgba(148,163,184,0.05));
}
.side-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.66rem;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: #64748B;
    margin: 14px 0 6px 0;
}

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button {
    width: 100%;
    border-radius: 11px;
    border: 1px solid rgba(56,189,248,0.32);
    background: linear-gradient(135deg, rgba(56,189,248,0.22), rgba(56,189,248,0.07));
    color: #E0F2FE;
    font-weight: 600;
    font-size: 0.86rem;
    letter-spacing: 0.2px;
    padding: 0.55rem 1rem;
    transition: all 0.18s ease;
    box-shadow: 0 12px 28px -20px rgba(56,189,248,0.9);
}
.stButton > button:hover, .stDownloadButton > button:hover {
    border-color: rgba(56,189,248,0.7);
    background: linear-gradient(135deg, rgba(56,189,248,0.32), rgba(56,189,248,0.12));
    transform: translateY(-1px);
    box-shadow: 0 18px 34px -20px rgba(56,189,248,1);
}
.stButton > button:disabled {
    opacity: 0.42;
    border-color: rgba(148,163,184,0.18);
    background: rgba(148,163,184,0.08);
    color: #94A3B8;
    box-shadow: none;
    transform: none;
}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: rgba(15,23,42,0.6);
    border: 1px solid rgba(148,163,184,0.12);
    border-radius: 14px;
    padding: 6px;
    margin-bottom: 18px;
}
.stTabs [data-baseweb="tab"] {
    height: auto;
    padding: 9px 16px;
    border-radius: 9px;
    color: #94A3B8;
    font-size: 0.84rem;
    font-weight: 500;
    background: transparent;
    border: none;
}
.stTabs [data-baseweb="tab"]:hover { color: #E2E8F0; background: rgba(56,189,248,0.07); }
.stTabs [aria-selected="true"] {
    color: #E0F2FE !important;
    background: linear-gradient(135deg, rgba(56,189,248,0.24), rgba(56,189,248,0.08)) !important;
    box-shadow: inset 0 0 0 1px rgba(56,189,248,0.35);
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

/* ---------- Metrics ---------- */
div[data-testid="stMetric"] {
    background: rgba(15,23,42,0.55);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(148,163,184,0.14);
    border-top: 2px solid rgba(56,189,248,0.55);
    border-radius: 16px;
    padding: 14px 16px 12px 16px;
    box-shadow: 0 20px 44px -32px rgba(0,0,0,0.95);
}
div[data-testid="stMetricLabel"] p {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.66rem !important;
    letter-spacing: 1.3px;
    text-transform: uppercase;
    color: #94A3B8 !important;
}
div[data-testid="stMetricValue"] {
    color: #F3F4F6;
    font-weight: 600;
    letter-spacing: -0.5px;
}

/* ---------- Alerts / info ---------- */
div[data-testid="stAlert"] {
    background: rgba(15,23,42,0.62);
    border: 1px solid rgba(148,163,184,0.16);
    border-radius: 13px;
    color: #CBD5E1;
    backdrop-filter: blur(12px);
}

/* ---------- Slider ---------- */
.stSlider [data-baseweb="slider"] div[role="slider"] {
    background: #38BDF8;
    border: 3px solid #0B1120;
    box-shadow: 0 0 0 1px rgba(56,189,248,0.6), 0 0 16px rgba(56,189,248,0.55);
}
.stSlider [data-baseweb="slider"] > div > div { background: rgba(56,189,248,0.35); }

/* ---------- Chat ---------- */
.chat-human, .chat-ai, .chat-tool {
    border-radius: 14px;
    padding: 13px 16px;
    margin-bottom: 10px;
    font-size: 0.88rem;
    line-height: 1.62;
    border: 1px solid rgba(148,163,184,0.13);
    background: rgba(15,23,42,0.55);
    backdrop-filter: blur(12px);
}
.chat-human {
    border-left: 3px solid #38BDF8;
    background: linear-gradient(135deg, rgba(56,189,248,0.12), rgba(15,23,42,0.55));
}
.chat-ai {
    border-left: 3px solid #34D399;
    background: linear-gradient(135deg, rgba(52,211,153,0.11), rgba(15,23,42,0.55));
}
.chat-tool {
    border-left: 3px solid #FBBF24;
    background: linear-gradient(135deg, rgba(251,191,36,0.10), rgba(15,23,42,0.55));
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
}
.chat-role {
    display: block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.64rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #94A3B8;
    margin-bottom: 6px;
}

/* ---------- Timeline ---------- */
.timeline { position: relative; margin: 4px 0 0 6px; padding-left: 26px; }
.timeline::before {
    content: "";
    position: absolute;
    left: 7px; top: 6px; bottom: 8px;
    width: 1px;
    background: linear-gradient(180deg, rgba(56,189,248,0.7), rgba(52,211,153,0.25), transparent);
}
.tl-item { position: relative; margin-bottom: 16px; }
.tl-item::before {
    content: "";
    position: absolute;
    left: -24px; top: 6px;
    width: 9px; height: 9px;
    border-radius: 50%;
    background: #38BDF8;
    box-shadow: 0 0 12px rgba(56,189,248,0.9);
}
.tl-step {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.66rem;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: #38BDF8;
}
.tl-title { font-size: 0.95rem; font-weight: 600; color: #F3F4F6; margin: 2px 0 3px 0; }
.tl-desc { font-size: 0.85rem; color: #94A3B8; line-height: 1.6; }

/* ---------- Misc ---------- */
.section-title {
    font-size: 1.02rem;
    font-weight: 600;
    color: #F3F4F6;
    letter-spacing: -0.2px;
    margin: 4px 0 12px 0;
}
.muted { color: #94A3B8; font-size: 0.84rem; }
.chip-row { display: flex; flex-wrap: wrap; gap: 14px; margin: 10px 0 14px 0; }
.chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #CBD5E1;
    background: rgba(15,23,42,0.55);
    border: 1px solid rgba(148,163,184,0.14);
    border-radius: 999px;
    padding: 5px 12px 5px 9px;
}
.chip-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
hr { border: none; border-top: 1px solid rgba(148,163,184,0.12); margin: 18px 0; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — FastAPI control panel
# ---------------------------------------------------------------------------
def _json_response(response):
    """Raise for HTTP errors and ensure every API response is an object."""
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Backend returned an unexpected response format.")
    return payload


def _render_control_panel():
    """Render and periodically refresh the UI without blocking the experiment."""
    try:
        hardware = _json_response(
            requests.get(f"{API_URL}/api/v1/hardware/status", timeout=API_TIMEOUT)
        )
        is_connected = bool(hardware.get("connected"))
        hardware_message = hardware.get("message", "")
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        is_connected = False
        hardware_message = f"Backend unavailable: {exc}"

    try:
        agent = _json_response(
            requests.get(f"{API_URL}/api/v1/agent/status", timeout=API_TIMEOUT)
        )
        agent_state = agent.get("status", "unknown")
        agent_message = agent.get("message", "No status message")
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        agent_state = "offline"
        agent_message = f"Backend unavailable: {exc}"

    # A completed background run needs one full-page rerun to load its new JSON
    # and report files.  This happens once; polling itself remains non-blocking.
    previous_state = st.session_state.get("agent_state")
    st.session_state["agent_state"] = agent_state
    if agent_state in {"completed", "error"} and previous_state != agent_state:
        st.session_state["pipeline_notice"] = {
            "state": agent_state,
            "message": agent_message,
        }
        st.rerun()

    st.markdown('<div class="side-head">🔬 Control Panel</div>', unsafe_allow_html=True)
    st.caption("Ossila SMU · Autonomous Physical Characterization")
    st.markdown('<div class="side-rule"></div>', unsafe_allow_html=True)

    st.markdown('<div class="side-label">Hardware Link</div>', unsafe_allow_html=True)
    if is_connected:
        st.markdown('<div class="status-badge-online">SMU Connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge-offline">SMU Disconnected</div>', unsafe_allow_html=True)
    if hardware_message:
        st.markdown(f'<div class="muted">{hardware_message}</div>', unsafe_allow_html=True)

    st.markdown('<div class="side-label">Agent State</div>', unsafe_allow_html=True)
    agent_running = agent_state == "running"
    if agent_running:
        st.markdown('<div class="status-badge-online">Agent Running</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge-offline">Agent Idle</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="muted">{agent_message}</div>', unsafe_allow_html=True)

    notice = st.session_state.pop("pipeline_notice", None)
    if notice:
        if notice["state"] == "completed":
            st.success(notice["message"])
        else:
            st.error(f"Pipeline error: {notice['message']}")

    st.markdown('<div class="side-rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="side-label">Autonomous Run</div>', unsafe_allow_html=True)

    if agent_running:
        st.info("Experiment is running in FastAPI. This dashboard is polling its progress.")

    if st.button("▶ Start Full Characterization", width="stretch", disabled=agent_running):
        try:
            result = _json_response(
                requests.post(f"{API_URL}/api/v1/agent/run", timeout=API_TIMEOUT)
            )
            if result.get("status") not in {"initiated", "already_running"}:
                raise RuntimeError(result.get("message", "Backend did not start the agent."))
            st.session_state["agent_state"] = "running"
            agent_running = True
            agent_message = result.get("message", "Agent execution started.")
            st.info(agent_message)
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            st.error(f"Could not start the agent: {exc}")

    st.markdown('<div class="side-rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="side-label">🎛️ Manual Hardware Bias Test</div>', unsafe_allow_html=True)

    v_manual = st.slider("Voltage Bias (V)", -1.2, 1.2, 0.5, 0.05)

    if st.button("Execute Single Point Test", width="stretch", disabled=agent_running):
        try:
            with st.spinner("Applying bias and sampling current..."):
                data_m = _json_response(
                    requests.post(
                        f"{API_URL}/api/v1/hardware/measure",
                        json={"voltage": v_manual},
                        timeout=API_TIMEOUT,
                    )
                )
            st.session_state["manual_v"] = data_m.get("voltage_V", 0)
            st.session_state["manual_i"] = data_m.get("current_A", 0) * 1e3
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            st.error(f"Measurement request failed: {exc}")

    mc1, mc2 = st.columns(2)
    mc1.metric("Bias (V)", f"{st.session_state.get('manual_v', 0.0):.3f}")
    mc2.metric("Current (mA)", f"{st.session_state.get('manual_i', 0.0):.5f}")


# Streamlit fragments rerun independently, so status updates do not freeze the
# rest of the dashboard.  The fallback keeps the app usable on an old install.
_fragment = getattr(st, "fragment", getattr(st, "experimental_fragment", None))
if _fragment is not None:
    render_control_panel = _fragment(run_every=STATUS_POLL_INTERVAL_SECONDS)(
        _render_control_panel
    )
else:
    render_control_panel = _render_control_panel

with st.sidebar:
    render_control_panel()


# ---------------------------------------------------------------------------
# Hero banner
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">Ossila SMU · Autonomous Characterization</div>
        <h1>⚡ Autonomous Physical Characterization Dashboard</h1>
        <p>Closed-loop electrical characterization of a 5 nm Ag/Silicon planar two-probe device:
        sweep acquisition, transport-regime classification, regression-based physics extraction
        and automated PDF reporting — driven by an autonomous reasoning agent.</p>
        <div class="hero-badges">
            <span class="hero-badge cyan">COM3 · 115200 baud</span>
            <span class="hero-badge emerald">±1.2 V clamp</span>
            <span class="hero-badge amber">pA sensitivity</span>
            <span class="hero-badge">5 nm Ag / Si / SiO₂</span>
            <span class="hero-badge">FastAPI · Streamlit</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
data = {}
try:
    with open(os.path.join("data", "experiment_data.json"), "r") as fh:
        data = json.load(fh)
except Exception:
    data = {}

physics = {}
try:
    with open(os.path.join("data", "physics_summary.json"), "r") as fh:
        physics = json.load(fh)
except Exception:
    physics = {}

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_curves, tab_hw, tab_sample, tab_physics, tab_agent = st.tabs(
    [
        "📈 Interactive Scientific Curves",
        "🔌 Ossila SMU Hardware Architecture & Specs",
        "🧪 Active Experiment & Sample Specs",
        "🔬 Extracted Physics & Regression Parameters",
        "🤖 AI Agent Live Reasoning & PDF Report",
    ]
)


# ===========================================================================
# TAB 1 — Scientific curves
# ===========================================================================
with tab_curves:
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "I–V Sweep (linear)",
            "Adaptive Fine Sweep",
            "Hysteresis Loop",
            "Time Series I(t)",
        ),
        horizontal_spacing=0.09,
        vertical_spacing=0.14,
    )

    plotted_any = False

    iv = data.get("iv_sweep", {})
    if iv.get("status") == "success":
        pts = iv["data"]
        fig.add_trace(
            go.Scatter(
                x=[p.get("voltage_V", 0) for p in pts],
                y=[p.get("current_A", 0) * 1e3 for p in pts],
                mode="lines+markers",
                line=dict(color=ACCENT_CYAN, width=2.5),
                marker=dict(size=4, color=ACCENT_CYAN),
                name="I–V",
            ),
            row=1,
            col=1,
        )
        plotted_any = True

    fine = data.get("adaptive_fine_sweep", {})
    if fine.get("status") == "success":
        pts = fine["data"]
        fig.add_trace(
            go.Scatter(
                x=[p.get("voltage_V", 0) for p in pts],
                y=[p.get("current_A", 0) * 1e3 for p in pts],
                mode="lines+markers",
                line=dict(color=ACCENT_EMERALD, width=2.5),
                marker=dict(size=4, color=ACCENT_EMERALD),
                name="Fine sweep",
            ),
            row=1,
            col=2,
        )
        plotted_any = True

    hyst = data.get("hysteresis", {})
    if hyst.get("status") == "success":
        pts = hyst["data"]
        fig.add_trace(
            go.Scatter(
                x=[p.get("voltage_V", 0) for p in pts],
                y=[p.get("current_A", 0) * 1e3 for p in pts],
                mode="lines+markers",
                line=dict(color=ACCENT_AMBER, width=2.5),
                marker=dict(size=4, color=ACCENT_AMBER),
                name="Hysteresis",
            ),
            row=2,
            col=1,
        )
        plotted_any = True

    ts = data.get("time_series_it", {})
    if ts.get("status") == "success":
        pts = ts["data"]
        fig.add_trace(
            go.Scatter(
                x=[p.get("time_sec", idx) for idx, p in enumerate(pts)],
                y=[p.get("current_A", 0) * 1e3 for p in pts],
                mode="lines",
                line=dict(color=ACCENT_RED, width=2.5),
                name="I(t)",
            ),
            row=2,
            col=2,
        )
        plotted_any = True

    fig.update_layout(
        height=660,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.6)",
        font=dict(color="#F3F4F6", family="Inter, sans-serif", size=12),
        hovermode="x unified",
        showlegend=False,
        margin=dict(l=60, r=30, t=64, b=50),
    )
    fig.update_xaxes(title_text="Voltage (V)", gridcolor="#334155", zerolinecolor="#475569", linecolor="#334155")
    fig.update_yaxes(title_text="Current (mA)", gridcolor="#334155", zerolinecolor="#475569", linecolor="#334155")
    fig.update_xaxes(title_text="Time (s)", gridcolor="#334155", zerolinecolor="#475569", linecolor="#334155", row=2, col=2)
    fig.update_annotations(font=dict(color="#94A3B8", size=12))

    st.plotly_chart(fig, width="stretch")

    st.markdown(
        """
        <div class="chip-row">
            <span class="chip"><span class="chip-dot" style="background:#38BDF8; box-shadow:0 0 10px #38BDF8;"></span>I–V sweep</span>
            <span class="chip"><span class="chip-dot" style="background:#34D399; box-shadow:0 0 10px #34D399;"></span>Adaptive fine sweep</span>
            <span class="chip"><span class="chip-dot" style="background:#FBBF24; box-shadow:0 0 10px #FBBF24;"></span>Hysteresis loop</span>
            <span class="chip"><span class="chip-dot" style="background:#F87171; box-shadow:0 0 10px #F87171;"></span>Time series I(t)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not plotted_any:
        st.info("No active experiment data. Run a characterization sweep to populate the curves.")


# ===========================================================================
# TAB 2 — Hardware architecture and specs
# ===========================================================================
with tab_hw:
    st.markdown('<div class="section-title">Ossila Source-Measure Unit — hardware configuration</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="glass-card card-cyan">
            <div class="card-title">Physical link &amp; electrical envelope</div>
            <table class="custom-table">
                <thead>
                    <tr><th>Parameter</th><th>Value</th><th>Notes</th></tr>
                </thead>
                <tbody>
                    <tr><td>Instrument</td><td><code>Ossila Dual-Channel SMU</code></td><td>Two independent source-measure channels, channel 1 addressed as <code>smu1</code></td></tr>
                    <tr><td>Host interface</td><td><code>USB UART bridge</code></td><td>USB&nbsp;UART bridge driven from Python via PySerial, exposed as a virtual COM port</td></tr>
                    <tr><td>Serial port</td><td><code>COM3</code></td><td><code>115200</code> baud, 8 data bits, no parity, 1 stop bit</td></tr>
                    <tr><td>Voltage envelope</td><td><code>±10 V</code> → <code>±1.2 V clamp</code></td><td>Instrument range is ±10 V; the application clamps the setpoint to ±1.2 V</td></tr>
                    <tr><td>Current sensitivity</td><td><code>pA</code></td><td>Sub-nanoamp resolution on the low range</td></tr>
                    <tr><td>Current compliance</td><td><code>150 mA</code></td><td>Hard trip; output disabled above the limit</td></tr>
                    <tr><td>Relay switching delay</td><td><code>50–150 ms</code></td><td>Settling window before every measurement</td></tr>
                    <tr><td>Command framing</td><td><code>ASCII</code></td><td>Line oriented, <code>\\n</code> terminated, echoed responses</td></tr>
                    <tr><td>Response timeout</td><td><code>1.0 s</code></td><td><code>readline()</code> deadline per command</td></tr>
                </tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.markdown(
            """
            <div class="glass-card card-emerald">
                <div class="card-title">ASCII command protocol</div>
                <div class="proto-block">smu1 set voltage &lt;v&gt;
smu1 measure
smu1 set enabled 1
smu1 set enabled 0</div>
                <p style="margin-top:14px;">Each command is written as a single line and acknowledged with an
                <code>OK</code> response. Measurements return a structured line holding the applied voltage
                and the measured current, parsed with a <code>readline()</code> deadline of <code>1.0 s</code>.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_right:
        st.markdown(
            """
            <div class="glass-card card-amber">
                <div class="card-title">Connection lifecycle</div>
                <table class="custom-table">
                    <thead>
                        <tr><th>Stage</th><th>Action</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Open</td><td>Serial port opened at <code>COM3</code>, <code>115200</code></td></tr>
                        <tr><td>Handshake</td><td>Identity query, buffer flush</td></tr>
                        <tr><td>Enable</td><td><code>smu1 set enabled 1</code>, relay closes</td></tr>
                        <tr><td>Cycle</td><td>Set bias → settle 50–150 ms → measure</td></tr>
                        <tr><td>Close</td><td><code>smu1 set enabled 0</code>, port released</td></tr>
                    </tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title" style="margin-top:8px;">Relay control, arc suppression &amp; safety interlocks</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="glass-card card-indigo">
            <div class="card-title">Relay control &amp; arc suppression</div>
            <p>The mechanical relay is closed only after the bias has been driven to zero. Switching at zero
            volts suppresses arcing across the contacts and extends the service life of the relay.</p>
            <p>A <code>50–100 ms</code> settling delay is held after every close and every open, which avoids
            contact bounce and the inrush transient that would otherwise contaminate the first sample.</p>
            <p>The port is opened through a single shared object, <code>get_shared_connector()</code>, so the
            same serial port can never be opened in parallel by two processes.</p>
            <p>If the measured current exceeds the <code>150 mA</code> compliance limit, the protection layer
            disables the output immediately and latches an emergency state.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
# TAB 3 — Sample and experiment
# ===========================================================================
with tab_sample:
    st.markdown('<div class="section-title">Device under test — 5 nm Ag / Silicon</div>', unsafe_allow_html=True)

    s_left, s_right = st.columns([1, 1])

    with s_left:
        st.markdown(
            """
            <div class="glass-card card-cyan">
                <div class="card-title">Sample stack</div>
                <table class="custom-table">
                    <thead>
                        <tr><th>Layer / property</th><th>Value</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Top electrode</td><td>Ag, <code>5 nm</code> evaporated film</td></tr>
                        <tr><td>Substrate</td><td>Si (100) with native / thermal <code>SiO2</code></td></tr>
                        <tr><td>Contact geometry</td><td>Planar two-probe, coplanar pads</td></tr>
                        <tr><td>Expected resistance</td><td><code>4 Ω – 50 Ω</code></td></tr>
                        <tr><td>Bias envelope</td><td><code>±1.2 V</code></td></tr>
                        <tr><td>Ambient</td><td>Room temperature, unshielded bench</td></tr>
                    </tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with s_right:
        st.markdown(
            """
            <div class="glass-card card-emerald">
                <div class="card-title">Transport regimes under test</div>
                <table class="custom-table">
                    <thead>
                        <tr><th>Regime</th><th>Signature</th><th>Exponent</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Ohmic</td><td>Linear I–V, constant resistance</td><td><code>I = V / R</code></td></tr>
                        <tr><td>SCLC</td><td>Space-charge limited rise</td><td><code>I ∝ V^n</code>, <code>n &gt; 1.5</code></td></tr>
                        <tr><td>Fowler–Nordheim</td><td>Tunneling through a barrier</td><td><code>ln(I/V²) ∝ −1/V</code></td></tr>
                        <tr><td>Memristive</td><td>Hysteretic loop, history dependence</td><td><code>∮ I dV</code> &gt; 0</td></tr>
                    </tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title" style="margin-top:8px;">Autonomous characterization protocol</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="glass-card card-amber">
            <div class="timeline">
                <div class="tl-item">
                    <div class="tl-step">Step 01</div>
                    <div class="tl-title">Device bring-up and link verification</div>
                    <div class="tl-desc">The serial port is opened on COM3 at 115200 baud, the relay is closed
                    after a settling delay, and the current compliance limit is verified.</div>
                </div>
                <div class="tl-item">
                    <div class="tl-step">Step 02</div>
                    <div class="tl-title">Coarse I–V sweep</div>
                    <div class="tl-desc">The bias is swept from −1.2 V to +1.2 V while the current is recorded
                    at every point, giving a first estimate of the conduction order.</div>
                </div>
                <div class="tl-item">
                    <div class="tl-step">Step 03</div>
                    <div class="tl-title">Adaptive fine sweep</div>
                    <div class="tl-desc">Where the current changes sharply the step size is reduced, so that
                    the non-linear transitions are resolved precisely.</div>
                </div>
                <div class="tl-item">
                    <div class="tl-step">Step 04</div>
                    <div class="tl-title">Regime classification and regression</div>
                    <div class="tl-desc">The exponent n is taken from the log I – log V slope, Fowler–Nordheim
                    and SCLC regressions are fitted, and the hysteresis loop area is integrated.</div>
                </div>
                <div class="tl-item">
                    <div class="tl-step">Step 05</div>
                    <div class="tl-title">Report generation</div>
                    <div class="tl-desc">Results are persisted to JSON files, the figures are rendered, and the
                    final PDF report is assembled.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
# TAB 4 — Extracted physics
# ===========================================================================
with tab_physics:
    def _num(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    fn_block = physics.get("fowler_nordheim", {}) or {}
    barrier_height = _num(fn_block.get("barrier_height_eV", 0.45), 0.45)
    sclc_n = _num(physics.get("sclc_exponent_n", 0), 0.0)
    regime_label = "Fowler-Nordheim Tunneling" if sclc_n > 1.5 else "Ohmic Transport"

    m1, m2, m3 = st.columns(3)
    m1.metric("Baseline Resistance (Ω)", f"{_num(physics.get('baseline_resistance_Ohm', 0)):.3f}")
    m2.metric("SCLC Exponent n", f"{sclc_n:.4f}")
    m3.metric("FN Barrier Height (eV)", f"{barrier_height:.4f}")

    m4, m5, m6 = st.columns(3)
    m4.metric("Hysteresis Loop Area (V·A)", f"{_num(physics.get('hysteresis_loop_area_VA', 0)):.6e}")
    m5.metric("1/f PSD Mean (A²/Hz)", f"{_num(physics.get('noise_1overf_psd_mean', 0)):.4e}")
    m6.metric("Transport Regime", regime_label)

    if not physics:
        st.info("No physics summary found. Run a characterization sweep to extract regression parameters.")

    st.markdown('<div class="section-title" style="margin-top:10px;">Parameter definitions &amp; governing equations</div>', unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)

    with p1:
        st.markdown(
            """
            <div class="glass-card card-cyan">
                <div class="card-title">Baseline resistance</div>
                <div class="card-value">R = V / I</div>
                <p>Low-bias slope of the I–V characteristic, taken from the linear window near zero bias.
                It sets the reference for every subsequent regime test and for the compliance headroom check.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="glass-card card-amber">
                <div class="card-title">Hysteresis loop area</div>
                <div class="card-value">A = ∮ V dI</div>
                <p>Enclosed area of the forward and reverse sweeps. A non-zero area indicates memory effects
                and is the primary memristive fingerprint of the silver filament.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with p2:
        st.markdown(
            """
            <div class="glass-card card-emerald">
                <div class="card-title">SCLC exponent</div>
                <div class="card-value">I ∝ V^n</div>
                <p>Slope of log I versus log V. Values near 1 indicate Ohmic conduction, values between
                1 and 2 indicate space-charge-limited current, and values above 1.5 with a good
                Fowler–Nordheim fit indicate tunnelling injection.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="glass-card card-indigo">
                <div class="card-title">1/f noise PSD</div>
                <div class="card-value">S(f) ∝ 1/f^α</div>
                <p>Mean power spectral density of the current noise. Elevated broadband density points to
                contact instability, while a clean 1/f slope confirms a stable percolation path.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with p3:
        st.markdown(
            """
            <div class="glass-card card-cyan">
                <div class="card-title">Fowler–Nordheim barrier</div>
                <div class="card-value">ln(I/V²) vs 1/V</div>
                <p>Linear regression of the Fowler–Nordheim coordinates yields a slope proportional to
                φ^(3/2); the extracted barrier height defaults to 0.45 eV when the fit is not significant.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="glass-card card-emerald">
                <div class="card-title">Regime decision rule</div>
                <div class="card-value">n &gt; 1.5 ?</div>
                <p>A fitted exponent above 1.5 labels the device as Fowler–Nordheim tunnelling; otherwise
                the transport is classified as Ohmic. The rule is applied to the same fitted value shown above.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ===========================================================================
# TAB 5 — Agent reasoning and report
# ===========================================================================
with tab_agent:
    st.markdown('<div class="section-title">Agent reasoning trace</div>', unsafe_allow_html=True)

    chat_log = data.get("agent_chat_log", [])

    if not chat_log:
        st.info("No agent activity recorded yet. Start a characterization run to stream the reasoning trace.")

    for entry in chat_log:
        entry_type = entry.get("type", "")
        content = str(entry.get("content", "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

        if entry_type == "human":
            st.markdown(
                f'<div class="chat-human"><span class="chat-role">Human operator</span>{content}</div>',
                unsafe_allow_html=True,
            )
        elif entry_type == "ai":
            st.markdown(
                f'<div class="chat-ai"><span class="chat-role">Autonomous agent</span>{content}</div>',
                unsafe_allow_html=True,
            )
        elif entry_type == "tool":
            tool_calls = entry.get("tool_calls", []) or []
            names = ", ".join([str(tc.get("name")) for tc in tool_calls]) if tool_calls else "tool"
            st.markdown(
                f'<div class="chat-tool"><span class="chat-role">Tool · {names}</span>{content}</div>',
                unsafe_allow_html=True,
            )
            for tc in tool_calls:
                with st.expander(f"🛠️ {tc.get('name')} — arguments", expanded=False):
                    args = tc.get("args")
                    if isinstance(args, (dict, list)):
                        st.json(args)
                    else:
                        st.code(str(args))
        else:
            st.markdown(
                f'<div class="chat-ai"><span class="chat-role">Log</span>{content}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="side-rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Characterization report</div>', unsafe_allow_html=True)

    report_path = os.path.join("data", "report.pdf")

    r_col, r_side = st.columns([2, 1])

    with r_col:
        if os.path.exists(report_path):
            with open(report_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
            st.markdown(
                """
                <div class="glass-card card-emerald">
                    <div class="card-title">Report ready</div>
                    <p>The full characterization report has been generated: sample description, raw sweeps,
                    regression fits, extracted physics parameters and the agent's conclusions.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.download_button(
                label="📥 Download PDF Report",
                data=pdf_bytes,
                file_name="Characterization_Report_AgSi_5nm.pdf",
                mime="application/pdf",
                width="stretch",
            )
        else:
            st.info("No report available yet. Complete a characterization run to generate the PDF report.")

    with r_side:
        st.markdown(
            """
            <div class="glass-card card-cyan">
                <div class="card-title">Report contents</div>
                <p>· Device and sample metadata</p>
                <p>· Coarse and adaptive sweep data</p>
                <p>· Transport regime classification</p>
                <p>· Regression parameters and fits</p>
                <p>· Agent narrative summary</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown(
    '<div class="muted" style="margin-top:26px; text-align:center;">Ossila SMU · Autonomous Physical Characterization Suite — '
    'FastAPI backend at 127.0.0.1:8000</div>',
    unsafe_allow_html=True,
)










