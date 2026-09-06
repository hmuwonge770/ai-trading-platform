from pathlib import Path


ROOT = Path(__file__).parents[2] / "k8s" / "stage-29"


def _text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_all_runtime_namespaces_are_separate() -> None:
    text = _text("namespaces.yaml")
    names = {line.strip().split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("  name: trading-")}
    assert names == {"trading-research", "trading-paper", "trading-testnet", "trading-live", "trading-monitoring"}
    assert len(names) == 5


def test_each_trading_namespace_has_dedicated_service_account() -> None:
    text = _text("service-accounts.yaml")
    for namespace, account in (
        ("trading-research", "research"),
        ("trading-paper", "paper"),
        ("trading-testnet", "testnet"),
        ("trading-live", "live"),
    ):
        assert f"name: {account}\n  namespace: {namespace}" in text


def test_each_trading_namespace_has_default_deny_ingress_and_egress() -> None:
    text = _text("network-policies.yaml")
    for namespace in ("trading-research", "trading-paper", "trading-testnet", "trading-live"):
        assert text.count(f"namespace: {namespace}") >= 2
        assert f"name: default-deny-ingress\n  namespace: {namespace}" in text
        assert f"name: default-deny-egress\n  namespace: {namespace}" in text


def test_policy_layer_does_not_grant_broad_external_egress() -> None:
    text = _text("policies.yaml")
    assert "ipBlock:" not in text
    assert text.count("port: 53") == 8


def test_secret_template_contains_placeholders_only() -> None:
    text = _text("secrets.template.yaml")
    assert text.count('BINANCE_API_KEY: "REPLACE_ME"') == 2
    assert text.count('BINANCE_API_SECRET: "REPLACE_ME"') == 2
    assert "actual" not in text.lower()
