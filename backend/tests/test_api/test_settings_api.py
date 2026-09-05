def test_get_scoring_config_returns_defaults(client):
    resp = client.get("/api/settings/scoring")
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_signal_score"] == 70.0
    assert sum(data["weights"].values()) == 100.0


def test_update_scoring_config_persists(client):
    resp = client.put("/api/settings/scoring", json={"min_signal_score": 55})
    assert resp.status_code == 200
    assert resp.json()["min_signal_score"] == 55

    resp2 = client.get("/api/settings/scoring")
    assert resp2.json()["min_signal_score"] == 55


def test_list_patterns_returns_18_entries(client):
    resp = client.get("/api/settings/patterns")
    assert resp.status_code == 200
    assert len(resp.json()) == 18
    keys = {p["key"] for p in resp.json()}
    assert "bullish_engulfing" in keys
    assert "doji" in keys


def test_notification_preferences_default_and_update(client):
    resp = client.get("/api/settings/notifications")
    assert resp.status_code == 200
    channels = {p["channel"] for p in resp.json()}
    assert {"in_app", "email", "telegram"} <= channels

    resp2 = client.put("/api/settings/notifications/email", json={"enabled": False})
    assert resp2.status_code == 200
    assert resp2.json()["enabled"] is False
