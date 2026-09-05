def test_add_list_update_delete_watchlist_item(client):
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    assert resp.json() == []

    resp = client.post("/api/watchlist", json={"symbol": "nvda", "timeframes": ["15m", "1h"]})
    assert resp.status_code == 201
    item = resp.json()
    assert item["symbol"] == "NVDA"  # normalized to uppercase

    resp = client.get("/api/watchlist")
    assert len(resp.json()) == 1

    resp = client.patch(f"/api/watchlist/{item['id']}", json={"min_score_override": 65, "enabled": False})
    assert resp.status_code == 200
    assert resp.json()["min_score_override"] == 65
    assert resp.json()["enabled"] is False

    resp = client.delete(f"/api/watchlist/{item['id']}")
    assert resp.status_code == 204
    assert client.get("/api/watchlist").json() == []


def test_duplicate_symbol_rejected(client):
    client.post("/api/watchlist", json={"symbol": "AMD"})
    resp = client.post("/api/watchlist", json={"symbol": "AMD"})
    assert resp.status_code == 409


def test_unknown_pattern_key_rejected(client):
    resp = client.post("/api/watchlist", json={"symbol": "AAPL", "enabled_patterns": ["not_a_real_pattern"]})
    assert resp.status_code == 422


def test_update_missing_item_returns_404(client):
    resp = client.patch("/api/watchlist/99999", json={"enabled": False})
    assert resp.status_code == 404
