import json

import pytest

from src import server
from src.feeds import FeedClient


def test_noaa_observation_and_alerts(monkeypatch):
    responses = {
        server.KP_URL: [
            ["time_tag", "Kp"],
            ["2026-10-29 03:00:00", "3"],
            ["2026-10-29 00:00:00", "2"],
        ],
        server.ALERTS_URL: [{"product_id": "K04A", "message": "Test alert"}],
    }
    monkeypatch.setattr(server, "feeds", FeedClient(lambda url: json.dumps(responses[url])))
    result = server.query_noaa_swpc_kp()
    assert result["latest_observation"]["Kp"] == "3"
    assert result["alerts"][0]["product_id"] == "K04A"
    assert server.query_noaa_swpc_kp()["cached"]


def test_noaa_schema_failure(monkeypatch):
    monkeypatch.setattr(server, "feeds", FeedClient(lambda _: "[]"))
    with pytest.raises(ValueError):
        server.query_noaa_swpc_kp()


def test_current_noaa_object_layout(monkeypatch):
    responses = {
        server.KP_URL: [{"time_tag": "2026-10-29T03:00:00", "Kp": 3.0}],
        server.ALERTS_URL: [],
    }
    monkeypatch.setattr(server, "feeds", FeedClient(lambda url: json.dumps(responses[url])))
    assert server.query_noaa_swpc_kp()["latest_observation"]["Kp"] == 3.0
