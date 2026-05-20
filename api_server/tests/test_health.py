from importlib import util
from pathlib import Path

from fastapi.testclient import TestClient


API_MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
spec = util.spec_from_file_location("api_server_main_test_health", API_MAIN_PATH)
assert spec is not None and spec.loader is not None
api_main = util.module_from_spec(spec)
spec.loader.exec_module(api_main)
app = api_main.app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["server"] == "api"
