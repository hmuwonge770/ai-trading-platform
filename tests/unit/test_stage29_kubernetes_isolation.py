from pathlib import Path

import yaml


ROOT = Path(__file__).parents[2] / "k8s" / "stage-29"


def _documents(name: str) -> list[dict]:
    with (ROOT / name).open(encoding="utf-8") as handle:
        return [doc for doc in yaml.safe_load_all(handle) if doc]


def test_all_runtime_namespaces_are_separate() -> None:
    docs = _documents("namespaces.yaml")
    names = {doc["metadata"]["name"] for doc in docs}
    assert {"trading-research", "trading-paper", "trading-testnet", "trading-live"} <= names
    assert len(names) == len(docs)


def test_each_trading_namespace_has_dedicated_service_account() -> None:
    docs = _documents("service-accounts.yaml")
    pairs = {(doc["metadata"]["namespace"], doc["metadata"]["name"]) for doc in docs}
    assert pairs == {
        ("trading-research", "research"),
        ("trading-paper", "paper"),
        ("trading-testnet", "testnet"),
        ("trading-live", "live"),
    }


def test_each_runtime_namespace_has_default_deny_ingress_and_egress() -> None:
    docs = _documents("network-policies.yaml")
    policies = {(doc["metadata"]["namespace"], doc["metadata"]["name"]): doc for doc in docs}
    for namespace in ("trading-research", "trading-paper", "trading-testnet", "trading-live"):
        assert (namespace, "default-deny-ingress") in policies
        assert (namespace, "default-deny-egress") in policies
        assert policies[(namespace, "default-deny-ingress")]["spec"]["podSelector"] == {}
        assert policies[(namespace, "default-deny-egress")]["spec"]["podSelector"] == {}


def test_policy_layer_does_not_grant_broad_external_egress() -> None:
    docs = _documents("policies.yaml")
    for doc in docs:
        assert doc["spec"].get("egress")
        for rule in doc["spec"]["egress"]:
            assert "ipBlock" not in rule


def test_secret_template_contains_placeholders_only() -> None:
    docs = _documents("secrets.template.yaml")
    for doc in docs:
        assert doc["kind"] == "Secret"
        assert doc["type"] == "Opaque"
        assert doc["stringData"]["BINANCE_API_KEY"] == "REPLACE_ME"
        assert doc["stringData"]["BINANCE_API_SECRET"] == "REPLACE_ME"
