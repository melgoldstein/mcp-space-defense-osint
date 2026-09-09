"""MCP stdio server for public orbital and space-weather context."""

import argparse
import json
import sys
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from .airspace import analyze_notam_tfr as parse_notice
from .feeds import FeedClient
from .orbits import predict_pass

server = FastMCP("space-defense-osint")
feeds = FeedClient()
KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
ALERTS_URL = "https://services.swpc.noaa.gov/products/alerts.json"


@server.tool()
def fetch_celestrak_tle(
    catalog_id: int = 25544,
    latitude: float = 28.4158,
    longitude: float = -80.6048,
    horizon_hours: float = 24,
    minimum_elevation_deg: float = 10,
) -> dict[str, object]:
    """Fetch one TLE and predict the next topocentric pass; returns source and epoch age."""
    if not 1 <= catalog_id <= 99999:
        raise ValueError("Legacy TLE catalog ID must be in [1,99999]")
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={catalog_id}&FORMAT=TLE"
    tle, retrieved, cached = feeds.get(url, 3600)
    result = predict_pass(
        tle, latitude, longitude, datetime.now(timezone.utc), horizon_hours, minimum_elevation_deg
    )
    return {**result, "tle": tle, "source_url": url, "retrieved_at": retrieved, "cached": cached}


@server.tool()
def query_noaa_swpc_kp() -> dict[str, object]:
    """Fetch observed planetary Kp and current SWPC alerts with retrieval timestamps."""
    observations, retrieved, cached = feeds.json(KP_URL, 60)
    alerts, alerts_retrieved, alerts_cached = feeds.json(ALERTS_URL, 60)
    if not isinstance(observations, list) or not observations or not isinstance(alerts, list):
        raise ValueError("Unexpected SWPC response schema")
    if isinstance(observations[0], dict):
        records = observations
    elif isinstance(observations[0], list) and len(observations) > 1:
        records = [dict(zip(observations[0], row, strict=True)) for row in observations[1:]]
    else:
        raise ValueError("Unexpected SWPC observation layout")
    if not all(isinstance(row, dict) and "time_tag" in row and "Kp" in row for row in records):
        raise ValueError("Missing SWPC time_tag or Kp")
    latest = max(records, key=lambda row: row["time_tag"])
    observation_time = datetime.fromisoformat(latest["time_tag"].replace("Z", "+00:00"))
    if observation_time.tzinfo is None:
        observation_time = observation_time.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - observation_time).total_seconds()
    return {
        "latest_observation": latest,
        "alerts": alerts,
        "source_url": KP_URL,
        "alerts_url": ALERTS_URL,
        "retrieved_at": retrieved,
        "cached": cached,
        "alerts_retrieved_at": alerts_retrieved,
        "alerts_cached": alerts_cached,
        "observation_age_seconds": age,
        "stale": age > 6 * 3600,
    }


@server.tool()
def analyze_notam_tfr(notice: str) -> dict[str, object]:
    """Convert an ICAO Q-line center/radius to a GeoJSON bounding envelope."""
    return parse_notice(notice)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Check local parser without networking"
    )
    arguments = parser.parse_args()
    if arguments.check:
        sys.stdout.write(json.dumps(parse_notice("2825N08036W010")) + "\n")
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
