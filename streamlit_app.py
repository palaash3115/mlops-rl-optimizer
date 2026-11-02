"""Streamlit UI for the RL Prompt Optimizer."""
import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="RL Prompt Optimizer",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 RL Prompt Optimizer")
st.markdown("*Powered by Soft Q-Learning — optimizes your prompts before sending to LLMs*")

# ── Sidebar: provider / model / policy stats ──────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    # Fetch available models
    try:
        resp = requests.get(f"{API_URL}/api/models", timeout=5)
        providers_data = resp.json()["providers"]
        provider_names = [p["name"] for p in providers_data]
        has_key = {p["name"]: p["has_key"] for p in providers_data}
        models_map = {p["name"]: p["models"] for p in providers_data}
    except Exception:
        st.error("⚠️ Cannot reach API. Make sure the server is running.")
        provider_names = ["Gemini", "Groq", "Nvidia"]
        has_key = {}
        models_map = {
            "Gemini": ["gemini-3.5-flash"],
            "Groq": ["qwen/qwen3.8-27b"],
            "Nvidia": ["meta/llama-3.3-70b-instruct"],
        }

    provider = st.selectbox("Provider", provider_names)
    if has_key.get(provider) is False:
        st.warning(f"No API key set for {provider}")

    model = st.selectbox("Model", models_map.get(provider, []))

    st.divider()
    st.header("📊 RL Policy Stats")
    try:
        stats = requests.get(f"{API_URL}/api/policy", timeout=5).json()
        st.metric("Total Optimizations", stats.get("total_optimizations", 0))
        st.metric("Strategies Learned", stats.get("strategies_count", 0))
        if st.button("🔄 Reset Policy"):
            requests.post(f"{API_URL}/api/policy/reset", timeout=5)
            st.success("Policy reset!")
            st.rerun()
    except Exception:
        st.caption("Policy stats unavailable")

    st.divider()
    st.header("🔗 System Links")
    st.markdown(f"- [API Docs]({API_URL}/docs)")
    st.markdown("- [Prometheus](http://localhost:9090)")
    st.markdown("- [Grafana](http://localhost:3000)")

# ── Main: prompt input and results ───────────────────────────────────────
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Your Prompt")
    user_prompt = st.text_area(
        "Enter your prompt",
        placeholder="e.g. Summarize the key points of quantum computing",
        height=150,
    )
    run_btn = st.button("🚀 Optimize & Execute", type="primary", use_container_width=True)

if run_btn and user_prompt.strip():
    # Step 1: Optimize
    with st.spinner("🧠 RL optimizer rewriting your prompt..."):
        try:
            opt_resp = requests.post(
                f"{API_URL}/api/optimize",
                json={"prompt": user_prompt, "provider": provider, "model": model},
                timeout=30,
            )
            opt_data = opt_resp.json()
        except Exception as e:
            st.error(f"Optimization failed: {e}")
            st.stop()

    original = opt_data.get("original", user_prompt)
    optimized = opt_data.get("optimized", user_prompt)
    strategy = opt_data.get("strategy")

    with col2:
        st.subheader("✨ RL-Optimized Prompt")
        st.info(optimized)
        if strategy:
            st.caption(f"Strategy applied: **{strategy}**")

    # Step 2: Execute both
    st.divider()
    st.subheader("⚡ Side-by-Side Results")
    with st.spinner("Running both prompts through the LLM..."):
        try:
            exec_resp = requests.post(
                f"{API_URL}/api/execute",
                json={
                    "original": original,
                    "optimized": optimized,
                    "provider": provider,
                    "model": model,
                    "strategy": strategy,
                },
                timeout=60,
            )
            exec_data = exec_resp.json()
        except Exception as e:
            st.error(f"Execution failed: {e}")
            st.stop()

    r1, r2 = st.columns(2)
    with r1:
        st.markdown("**Original Response**")
        st.write(exec_data.get("original_response", "No response"))
        orig_tokens = exec_data.get("original_tokens", "—")
        st.caption(f"Tokens: {orig_tokens}")

    with r2:
        st.markdown("**Optimized Response** ✨")
        st.write(exec_data.get("optimized_response", "No response"))
        opt_tokens = exec_data.get("optimized_tokens", "—")
        st.caption(f"Tokens: {opt_tokens}")

    # Efficiency gain
    gain = exec_data.get("efficiency_gain")
    if gain is not None:
        if gain > 0:
            st.success(f"🎯 Efficiency gain: **{gain:.1f}%** fewer tokens with the optimized prompt!")
        else:
            st.info(f"Efficiency delta: {gain:.1f}%")

elif run_btn:
    st.warning("Please enter a prompt first.")
else:
    with col2:
        st.subheader("✨ RL-Optimized Prompt")
        st.markdown("*Your optimized prompt will appear here*")
    st.info("👈 Enter a prompt on the left and click **Optimize & Execute** to see the RL optimizer in action.")
