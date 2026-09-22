from datetime import datetime, timezone

import pytest

from src.airspace import analyze_notam_tfr
from src.feeds import FeedClient
from src.orbits import predict_pass

TLE = """ISS (ZARYA)
1 25544U 98067A   24100.50000000  .00016717  00000+0  30172-3 0  9997
2 25544  51.6416  20.0000 0005000  60.0000  30.0000 15.50000000440000
"""


def test_cache_preserves_retrieval_time() -> None:
    calls = []
    client = FeedClient(lambda url: calls.append(url) or '{"kp":3}')
    first = client.json("fixture")
    second = client.json("fixture")
    assert first[0] == second[0] and first[1] == second[1]
    assert second[2] is True and len(calls) == 1


def test_geometry_and_dateline() -> None:
    feature = analyze_notam_tfr("Q) KZMA/QWALW/IV/M/W/000/999/2825N08036W010")
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["bbox"][0] < -80.6 < feature["bbox"][2]
    assert analyze_notam_tfr("0000N17959E020")["geometry"]["type"] == "MultiPolygon"


@pytest.mark.parametrize("notice", ["unstructured text", "2865N08036W010", "2825N08036W000"])
def test_invalid_notice(notice: str) -> None:
    with pytest.raises(ValueError):
        analyze_notam_tfr(notice)


def test_pass_ordering() -> None:
    result = predict_pass(TLE, 28.4158, -80.6048, datetime(2024, 4, 9, tzinfo=timezone.utc), 48)
    assert result["next_pass"] is not None
    assert result["next_pass"]["set_utc"] > result["next_pass"]["culmination_utc"]
    assert abs(result["epoch_age_days"]) < 2


def test_reject_naive_time() -> None:
    with pytest.raises(ValueError):
        predict_pass(TLE, 28, -80, datetime(2024, 4, 9))
