"""Streamlit Community Cloud version of the RL Prompt Optimizer.

Runs the optimiser in-process (no FastAPI server needed), so it can be
hosted on share.streamlit.io. The local version that talks to the API is
../streamlit_app.py.

Secrets (Streamlit Cloud -> App settings -> Secrets):
    GEMINI_API_KEY = "..."
    GROQ_API_KEY   = "..."
    NIMA_API       = "..."   # optional, Nvidia
"""
import os
import sys
import tempfile
import types

import streamlit as st

# ── Keys: Streamlit secrets -> environment (what llm_clients reads) ────────
for _k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "NIMA_API"):
    try:
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k]).strip()
    except Exception:  # no secrets file locally
        pass

# ── Import chat_optimizer without rlprompt/__init__.py (which pulls in torch)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if "rlprompt" not in sys.modules:
    _pkg = types.ModuleType("rlprompt")
    _pkg.__path__ = [os.path.join(ROOT, "rlprompt")]
    sys.modules["rlprompt"] = _pkg
from rlprompt.chat_optimizer import StrategyPolicy, execute_and_compare, optimize_prompt  # noqa: E402

CHAT_MODELS = {
    "Gemini": ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"],
    "Groq": ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"],
    "Nvidia": ["meta/llama-3.3-70b-instruct", "meta/llama-3.1-70b-instruct",
               "google/gemma-3-12b-it", "mistralai/mistral-large-2-instruct"],
}
KEY_ENV = {"Gemini": "GEMINI_API_KEY", "Groq": "GROQ_API_KEY", "Nvidia": "NIMA_API"}


@st.cache_resource
def get_policy() -> StrategyPolicy:
    # Shared across sessions; resets when the app restarts (Cloud disk is ephemeral).
    return StrategyPolicy(os.path.join(tempfile.gettempdir(), "rlprompt_cloud.db"))


POLICY = get_policy()

st.set_page_config(page_title="RL Prompt Optimizer", page_icon="🧠", layout="wide")
st.title("🧠 RL Prompt Optimizer")
st.caption("Soft Q-Learning picks which rewrite strategy to try; the best-scoring "
           "rewrite is returned and the policy is updated from the outcome.")

# ── Sidebar ───────────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Model Settings")
available = [p for p in CHAT_MODELS if os.environ.get(KEY_ENV[p])]
if not available:
    st.sidebar.error("No API keys configured. Add GEMINI_API_KEY or GROQ_API_KEY "
                     "in the app's Secrets.")
    st.stop()
provider = st.sidebar.selectbox("Provider", available)
model = st.sidebar.selectbox("Model", CHAT_MODELS[provider])

with st.sidebar.expander("📊 Policy stats (Q-values)", expanded=False):
    st.json(POLICY.stats())
    if st.button("Reset policy"):
        POLICY.reset()
        st.success("Policy reset.")

# ── Prompt ────────────────────────────────────────────────────────────────
st.subheader("1. Enter your prompt")
prompt = st.text_area("Prompt", value="Classify the sentiment of this movie review.", height=80)

if st.button("🚀 Optimise Prompt", use_container_width=True):
    if not prompt.strip():
        st.warning("Please enter a prompt first.")
    else:
        with st.spinner("Running RL optimisation…"):
            try:
                st.session_state["opt"] = optimize_prompt(prompt.strip(), provider, model, POLICY)
                st.session_state.pop("exec", None)
            except Exception as e:
                st.error(f"{type(e).__name__}: {e}")

opt = st.session_state.get("opt")
if opt:
    st.subheader("2. Original vs RL-optimised")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Original** · score {opt.get('original_score')}")
        st.code(opt["original"], language="text")
    with c2:
        st.markdown(f"**Optimised** · {opt.get('strategy_label')} · score {opt.get('optimized_score')}")
        st.code(opt["optimized"], language="text")
    if opt.get("reason"):
        st.caption(opt["reason"])

    if st.button("▶️ Execute & Compare", use_container_width=True):
        with st.spinner("Running both prompts through the model…"):
            try:
                st.session_state["exec"] = execute_and_compare(
                    opt["original"], opt["optimized"], provider, model, opt.get("strategy"), POLICY)
            except Exception as e:
                st.error(f"{type(e).__name__}: {e}")

    if st.session_state.get("exec"):
        st.subheader("3. Results")
        st.json(st.session_state["exec"])

st.divider()
st.caption("Hosted on Streamlit Community Cloud · source: github.com/palaash3115/mlops-rl-optimizer")
