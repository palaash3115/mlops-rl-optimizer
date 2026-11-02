"""Streamlit front-end for the RL Prompt Optimizer API.

    streamlit run streamlit_app.py

Requires the FastAPI chat_server to be running:
    python chat_server.py   # http://localhost:8000
"""

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="RL Prompt Optimizer",
    page_icon="🧠",
    layout="wide",
)

# ── Title ──────────────────────────────────────────────────────────────────
st.title("🧠 RL Prompt Optimizer")
st.caption(
    "Uses Soft Q-Learning to find extra prompt tokens that boost LLM accuracy "
    "on your task — based on _RLPrompt_ (Deng et al., EMNLP 2022)."
)

# ── Sidebar: provider / model ──────────────────────────────────────────────
st.sidebar.header("⚙️ Model Settings")

@st.cache_data(ttl=60)
def fetch_providers():
    try:
        data = requests.get(f"{API_BASE}/api/models", timeout=5).json()
        return data.get("providers", [])
    except Exception:
        return []

providers = fetch_providers()
provider_names = [p["name"] for p in providers] if providers else ["Gemini", "Groq", "Nvidia"]
provider = st.sidebar.selectbox("Provider", provider_names)

model_options = []
for p in providers:
    if p["name"] == provider:
        model_options = p["models"]
        break
if not model_options:
    model_options = ["(no models available)"]

model = st.sidebar.selectbox("Model", model_options)

# ── Policy stats ───────────────────────────────────────────────────────────
with st.sidebar.expander("📊 Policy stats", expanded=False):
    try:
        stats = requests.get(f"{API_BASE}/api/policy", timeout=5).json()
        st.json(stats)
    except Exception as e:
        st.warning(f"Could not reach API: {e}")

    if st.button("Reset policy"):
        try:
            requests.post(f"{API_BASE}/api/policy/reset", timeout=5)
            st.success("Policy reset.")
        except Exception as e:
            st.error(str(e))

# ── Main: prompt input ─────────────────────────────────────────────────────
st.subheader("1. Enter your prompt")
prompt = st.text_area(
    "Prompt",
    value="Classify the sentiment of this movie review.",
    height=80,
)

col_opt, col_exec = st.columns([1, 1])

# ── Optimise ──────────────────────────────────────────────────────────────
with col_opt:
    if st.button("🚀 Optimise Prompt", use_container_width=True):
        if not prompt.strip():
            st.warning("Please enter a prompt first.")
        else:
            with st.spinner("Running RL optimisation…"):
                try:
                    resp = requests.post(
                        f"{API_BASE}/api/optimize",
                        json={"prompt": prompt, "provider": provider, "model": model},
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state["optimized"] = data.get("optimized", "")
                        st.session_state["original"] = data.get("original", prompt)
                        st.success("Optimisation complete!")
                    else:
                        st.error(f"API error {resp.status_code}: {resp.text}")
                except Exception as e:
                    st.error(f"Could not reach API: {e}")

# ── Results ────────────────────────────────────────────────────────────────
if "original" in st.session_state:
    st.subheader("2. Results")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Original prompt**")
        st.code(st.session_state["original"], language="text")
    with c2:
        st.markdown("**RL-optimised prompt**")
        st.code(st.session_state["optimized"], language="text")

    # ── Execute both ──────────────────────────────────────────────────────
    if st.button("▶️ Execute & Compare", use_container_width=True):
        with st.spinner("Running both prompts through the model…"):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/execute",
                    json={
                        "original": st.session_state["original"],
                        "optimized": st.session_state["optimized"],
                        "provider": provider,
                        "model": model,
                    },
                    timeout=60,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    st.json(result)
                else:
                    st.error(f"API error {resp.status_code}: {resp.text}")
            except Exception as e:
                st.error(f"Could not reach API: {e}")

# ── Footer ─────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "API running at http://localhost:8000 · "
    "Metrics at http://localhost:8000/metrics · "
    "Grafana at http://localhost:3000"
)
