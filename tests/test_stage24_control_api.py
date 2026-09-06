from apps.control_api.main import app


def test_promotion_control_api_is_registered():
    paths = set(app.openapi().get("paths", {}))
    assert "/promotions" in paths
    assert "/promotions/{promotion_id}" in paths
    assert "/promotions/{promotion_id}/approve" in paths
    assert "/promotions/{promotion_id}/activate" in paths
    assert "/promotions/{promotion_id}/authorization" in paths
    assert "/promotions/{promotion_id}/halt" in paths
