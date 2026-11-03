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
# Always overwrite, so edited Secrets take effect on the next rerun.
for _k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "NIMA_API"):
    try:
        if _k in st.secrets:
            os.environ[_k] = str(st.secrets[_k]).strip().strip("'\"")
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

# ── Helpers ───────────────────────────────────────────────────────────────
DIMS = ["relevance", "completeness", "accuracy", "clarity", "overall"]


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _fmt(x, nd=1):
    v = _num(x)
    return "–" if v is None else f"{v:.{nd}f}".rstrip("0").rstrip(".")


def _delta(a, b):
    a, b = _num(a), _num(b)
    return None if a is None or b is None else round(b - a, 2)


def prompt_card(title, text, caption=None, badge=None):
    with st.container(border=True):
        st.markdown(f"**{title}**" + (f"  ·  :blue-background[{badge}]" if badge else ""))
        st.markdown(f"> {text}".replace("\n", "\n> "))
        if caption:
            st.caption(caption)


def response_card(title, r, highlight=False):
    with st.container(border=True):
        head = f"**{title}**" + ("  ·  :green-background[🏆 winner]" if highlight else "")
        st.markdown(head)
        if r.get("error"):
            st.error(r["error"])
        else:
            st.markdown(r.get("text") or "_(empty response)_")
        lat = _num(r.get("latency"))
        st.caption(
            f"⏱ {lat:.2f}s" if lat is not None else "⏱ –"
            f"  ·  🔤 {r.get('prompt_tokens', '–')} in / {r.get('response_tokens', '–')} out tokens"
        )


def render_results(res, opt):
    o, p = res.get("original", {}), res.get("optimized", {})
    scores = res.get("scores") or {}
    so, sp = scores.get("original") or {}, scores.get("optimized") or {}
    learn = res.get("learning") or {}

    # winner
    winner = None
    a, b = _num(so.get("overall")), _num(sp.get("overall"))
    if a is not None and b is not None:
        winner = "optimized" if b > a else "original" if a > b else "tie"

    # ── headline metrics
    st.markdown("#### 🏁 Headline")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Original score", _fmt(a) if a is not None else "–")
    m2.metric("Optimised score", _fmt(b) if b is not None else "–", delta=_delta(a, b))
    lo, lp = _num(o.get("latency")), _num(p.get("latency"))
    m3.metric("Optimised latency", f"{lp:.2f}s" if lp is not None else "–",
              delta=None if lo is None or lp is None else f"{lp - lo:+.2f}s", delta_color="inverse")
    m4.metric("Strategy used", (opt.get("strategy_label") or opt.get("strategy") or "–"))

    if winner == "optimized":
        st.success("🏆 The RL-optimised prompt produced the better answer.")
    elif winner == "original":
        st.warning("The original prompt scored higher this time — the agent will learn from that.")
    elif winner == "tie":
        st.info("Both prompts scored the same.")
    else:
        st.warning("⚠️ The LLM judge could not score this run, so no winner was declared. "
                   "Try Execute & Compare again.")
    if res.get("same_prompt"):
        st.caption("The optimiser kept your original prompt (no rewrite beat it).")

    # ── responses side by side
    st.markdown("#### 💬 Model responses")
    r1, r2 = st.columns(2)
    with r1:
        response_card("Original prompt", o, highlight=winner == "original")
    with r2:
        response_card("Optimised prompt", p, highlight=winner == "optimized")

    # ── judge scores
    st.markdown("#### 🧑‍⚖️ Judge scores")
    if so and sp:
        import pandas as pd
        df = pd.DataFrame(
            {"Original": [_num(so.get(d)) for d in DIMS],
             "Optimised": [_num(sp.get(d)) for d in DIMS]},
            index=[d.capitalize() for d in DIMS],
        )
        t1, t2 = st.columns([1, 1])
        with t1:
            st.dataframe(df.style.format("{:.1f}", na_rep="–"), use_container_width=True)
        with t2:
            st.bar_chart(df, height=260)
    else:
        st.info("No judge scores available for this run.")
    if res.get("verdict"):
        st.info(f"**Judge verdict:** {res['verdict']}")

    # ── what RL learned
    st.markdown("#### 🧠 What the RL agent learned")
    if learn:
        l1, l2, l3, l4 = st.columns(4)
        old_q, new_q = _num(learn.get("old_q")), _num(learn.get("new_q"))
        l1.metric("Strategy updated", str(learn.get("strategy", "–")).replace("_", " "))
        l2.metric("Reward", _fmt(learn.get("reward"), 2))
        l3.metric("Q-value", _fmt(new_q, 3), delta=_delta(old_q, new_q))
        l4.metric("Times tried", str(learn.get("n", "–")))
        rw = _num(learn.get("reward"))
        if rw is not None:
            st.caption("Positive reward → this strategy becomes more likely next time. "
                       "Negative reward → it becomes less likely."
                       if rw != 0 else "Zero reward → policy unchanged for this strategy.")
    else:
        st.caption("No policy update this run (judge failed or prompt unchanged).")

    pol = res.get("policy") or {}
    if pol:
        import pandas as pd
        pdf = pd.DataFrame(
            [{"Strategy": v.get("label", k), "Q-value": _num(v.get("q")),
              "Selection probability": _num(v.get("prob")), "Tries": v.get("n", 0)}
             for k, v in pol.items()]
        ).set_index("Strategy")
        p1, p2 = st.columns(2)
        with p1:
            st.caption("Selection probability per strategy")
            st.bar_chart(pdf[["Selection probability"]], height=240)
        with p2:
            st.caption("Learned Q-value per strategy")
            st.bar_chart(pdf[["Q-value"]], height=240)
        with st.expander("Policy table"):
            st.dataframe(pdf, use_container_width=True)

    with st.expander("🔧 Raw JSON"):
        st.json(res)


# ── Prompt ────────────────────────────────────────────────────────────────
st.subheader("1. Enter your prompt")
prompt = st.text_area("Prompt", value="Classify the sentiment of this movie review.", height=80)

if st.button("🚀 Optimise Prompt", use_container_width=True, type="primary"):
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
        prompt_card("Original", opt["original"], badge=f"score {_fmt(opt.get('original_score'))}")
    with c2:
        prompt_card("Optimised", opt["optimized"],
                    badge=f"{opt.get('strategy_label')} · score {_fmt(opt.get('optimized_score'))}")
    if opt.get("reason"):
        st.caption(f"💡 {opt['reason']}")

    cands = opt.get("candidates") or []
    if cands:
        with st.expander(f"🔍 All {len(cands)} candidate rewrites the agent tried"):
            for c in cands:
                sc = c.get("score")
                st.markdown(f"**{c.get('label', c.get('strategy'))}**"
                            + (f" · score {_fmt(sc)}" if sc is not None else ""))
                st.code(c.get("prompt", ""), language="text")

    if st.button("▶️ Execute & Compare", use_container_width=True, type="primary"):
        with st.spinner("Running both prompts through the model…"):
            try:
                st.session_state["exec"] = execute_and_compare(
                    opt["original"], opt["optimized"], provider, model, opt.get("strategy"), POLICY)
            except Exception as e:
                st.error(f"{type(e).__name__}: {e}")

    if st.session_state.get("exec"):
        st.subheader("3. Results")
        render_results(st.session_state["exec"], opt)

st.divider()
st.caption("Hosted on Streamlit Community Cloud · source: github.com/palaash3115/mlops-rl-optimizer")
