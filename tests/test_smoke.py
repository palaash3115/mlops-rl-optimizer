"""
Lightweight smoke tests — no torch, no ML deps.
These run in CI with: pytest tests/test_smoke.py -q
"""
import os
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
    assert "Deployment" in kinds, f"No Deployment found, got: {kinds}"
    assert "Service" in kinds, f"No Service found, got: {kinds}"


def test_prometheus_config_is_valid_yaml():
    for candidate in ["monitoring/prometheus.yml", "prometheus/prometheus.yml", "prometheus.yml"]:
        cfg = ROOT / candidate
        if cfg.exists():
            data = yaml.safe_load(cfg.read_text())
            assert "scrape_configs" in data, f"{candidate} missing scrape_configs"
            return
    # not present — skip


def test_docker_compose_has_api_service():
    for name in ["docker-compose.yml", "docker-compose.yaml"]:
        dc = ROOT / name
        if dc.exists():
            data = yaml.safe_load(dc.read_text())
            services = data.get("services", {})
            assert services, f"{name} has no services"
            ports_flat = " ".join(
                str(p)
                for s in services.values()
                for p in s.get("ports", [])
            )
            assert "8000" in ports_flat, f"No service exposes port 8000; ports: {ports_flat}"
            return
    assert False, "docker-compose.yml not found"


# ── File presence checks ───────────────────────────────────────────────────────

def test_required_project_files_exist():
    required = [
        "Dockerfile",
        "requirements.txt",
        "chat_server.py",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f"Missing project files: {missing}"


def test_github_actions_workflow_exists():
    # Check via os.path to handle hidden directories on all OS
    wf = os.path.join(str(ROOT), ".github", "workflows", "ci-cd.yml")
    assert os.path.exists(wf), f"CI workflow not found at {wf}"


def test_terraform_main_exists():
    tf_dir = ROOT / "terraform"
    assert tf_dir.is_dir(), "terraform/ directory missing"
    tf_files = list(tf_dir.glob("*.tf"))
    assert tf_files, "No .tf files in terraform/"


# ── Lightweight logic tests (stdlib only) ─────────────────────────────────────

def test_zscore_pure_python():
    """Reproduce zscore logic without torch."""
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
    """Mirrors parse_label() — longest-label-first matching."""
    def parse_label(text, labels):
        tl = text.strip().lower()
        # Sort by length descending so longer labels win over shorter substrings
        for i, lab in sorted(enumerate(labels), key=lambda x: -len(x[1])):
            if lab in tl:
                return i
        return None

    assert parse_label("Answer: Negative.", ["positive", "negative"]) == 1
    assert parse_label("not sure", ["positive", "negative"]) is None
    assert parse_label("very positive", ["positive", "very positive"]) == 1
