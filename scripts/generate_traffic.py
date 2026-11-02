"""Generate synthetic traffic to populate Prometheus / Grafana metrics.

    python scripts/generate_traffic.py

Sends a stream of /health, /api/models, /api/policy and /api/optimize
requests to the running chat_server (default http://localhost:8000).
Watch the Grafana dashboard live at http://localhost:3000 while this runs.
"""

import random
import time

import requests

BASE = "http://localhost:8000"

SAMPLE_PROMPTS = [
    "Classify the sentiment of this movie review.",
    "Does this product review express satisfaction?",
    "Is the following tweet positive or negative?",
    "Summarise the main point of this paragraph.",
    "Translate the following sentence to formal English.",
    "Extract the named entities from this text.",
    "Detect the language of the following text.",
    "Identify whether this news headline is factual or opinion.",
]


def hit(path: str, method: str = "GET", json=None):
    try:
        if method == "GET":
            requests.get(f"{BASE}{path}", timeout=5)
        else:
            requests.post(f"{BASE}{path}", json=json, timeout=10)
    except Exception as e:
        print(f"  ✗ {method} {path} → {e}")


def main():
    print(f"Generating traffic against {BASE}  (Ctrl-C to stop)")
    iteration = 0
    while True:
        iteration += 1
        print(f"\n── Batch {iteration} ──────────────────────────────")

        # Health checks (high frequency)
        for _ in range(random.randint(3, 8)):
            hit("/health")
        print(f"  /health × {_+1}")

        # Model listing
        hit("/api/models")
        print("  /api/models")

        # Policy stats
        hit("/api/policy")
        print("  /api/policy")

        # Root page
        hit("/")
        print("  /")

        # Simulate an optimize request (without real API keys — will get 400,
        # which still increments the request counter)
        prompt = random.choice(SAMPLE_PROMPTS)
        provider = random.choice(["Gemini", "Groq", "Nvidia"])
        hit(
            "/api/optimize",
            method="POST",
            json={"prompt": prompt, "provider": provider, "model": "demo"},
        )
        print(f"  /api/optimize  provider={provider}")

        delay = random.uniform(1.0, 3.0)
        print(f"  sleeping {delay:.1f}s…")
        time.sleep(delay)


if __name__ == "__main__":
    main()
