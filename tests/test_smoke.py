"""
Lightweight smoke tests — no torch, no ML deps.
These run in CI with: pytest tests/test_smoke.py -q
"""
import os
import json
import yaml
import pathlib

ROOT = pathlib.Path(__file__).parent.parent


# ── YAML / JSON structure checks ──────────────────────────────────────────────

def test_k8s_manifests_are_valid_yaml():
    k8s_dir = ROOT / "k8s"
    yaml_files = list(k8s_dir.glob("*.yaml")) + list(k8s_dir.glob("*.yml"))
    assert yaml_files, "No Kubernetes YAML files found in k8s/"
    for f in yaml_files:
        docs = list(yaml.safe_load_all(f.read_text()))
        assert docs, f"{f.name} parsed to empty"


def test_k8s_manifests_have_required_kinds():
    k8s_dir = ROOT / "k8s"
    kinds = set()
    for f in list(k8s_dir.glob("*.yaml")) + list(k8s_dir.glob("*.yml")):
        for doc in yaml.safe_load_all(f.read_text()):
            if doc and "kind" in doc:
                kinds.add(doc["kind"])
    # Expect at least a Deployment and a Service
    assert "Deployment" in kinds, f"No Deployment found, got: {kinds}"
    assert "Service" in kinds, f"No Service found, got: {kinds}"


def test_prometheus_config_is_valid_yaml():
    cfg = ROOT / "monitoring" / "prometheus.yml"
    if not cfg.exists():
        cfg = ROOT / "prometheus.yml"
    if not cfg.exists():
        return  # optional — skip if not present
    data = yaml.safe_load(cfg.read_text())
    assert "scrape_configs" in data, "prometheus.yml missing scrape_configs"


def test_docker_compose_has_api_service():
    dc = ROOT / "docker-compose.yml"
    if not dc.exists():
        dc = ROOT / "docker-compose.yaml"
    assert dc.exists(), "docker-compose.yml not found"
    data = yaml.safe_load(dc.read_text())
    services = data.get("services", {})
    assert services, "docker-compose.yml has no services"
    # At least one service should expose port 8000 (the API)
    ports_flat = " ".join(
        str(p)
        for s in services.values()
        for p in s.get("ports", [])
    )
    assert "8000" in ports_flat, f"No service exposes port 8000; ports: {ports_flat}"


# ── File presence checks ───────────────────────────────────────────────────────

def test_required_project_files_exist():
    required = [
        "Dockerfile",
        "requirements.txt",
        "chat_server.py",
        ".github/workflows/ci-cd.yml",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f"Missing project files: {missing}"


def test_terraform_main_exists():
    tf_dir = ROOT / "terraform"
    assert tf_dir.is_dir(), "terraform/ directory missing"
    tf_files = list(tf_dir.glob("*.tf"))
    assert tf_files, "No .tf files in terraform/"


# ── Lightweight logic tests (stdlib only) ─────────────────────────────────────

def test_zscore_pure_python():
    """Reproduce zscore logic without torch to prove the math is right."""
    import math

    def zscore(values):
        n = len(values)
        mean = sum(values) / n
        std = math.sqrt(sum((x - mean) ** 2 for x in values) / n)
        if std < 1e-8:
            return [0.0] * n
        return [(x - mean) / std for x in values]

    z = zscore([1.0, 2.0, 3.0])
    assert abs(sum(z)) < 1e-9
    assert abs(sum(zi ** 2 for zi in z) / len(z) - 1.0) < 1e-9


def test_parse_label_logic():
    """Mirrors parse_label() without importing rlprompt."""
    def parse_label(text, labels):
        tl = text.strip().lower()
        for i, lab in enumerate(labels):
            if lab in tl:
                return i
        return None

    assert parse_label("Answer: Negative.", ["positive", "negative"]) == 1
    assert parse_label("not sure", ["positive", "negative"]) is None
    assert parse_label("very positive", ["positive", "very positive"]) == 1
