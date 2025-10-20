import requests

def test_root():
    res = requests.get("http://127.0.0.1:8000/")
    assert res.status_code == 200
    # Check the HTML title from your dashboard
    assert ("AI Money Web Backend is alive" in res.text) or ("<title>AI Money Web" in res.text)

def test_alpaca_status():
    res = requests.get("http://127.0.0.1:8000/api/alpaca_status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "connected"
    assert "equity" in data
    assert "cash" in data
