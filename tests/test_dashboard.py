from fastapi.testclient import TestClient

from openscout.serve import app


def test_health_and_sample_journey() -> None:
    client = TestClient(app)
    assert client.get("/api/health").json() == {"ok": True, "agent": "openscout"}
    sample = client.get("/api/sample-journey").json()["text"]
    assert "Place order" in sample
    assert "text/html" in client.get("/").headers["content-type"]
