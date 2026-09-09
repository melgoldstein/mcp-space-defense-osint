"""SGP4 topocentric pass prediction from CelesTrak TLE records."""

import math
from datetime import datetime, timedelta, timezone

from skyfield.api import EarthSatellite, load, wgs84


def predict_pass(
    tle: str,
    latitude: float,
    longitude: float,
    start: datetime,
    hours: float = 24,
    elevation: float = 10,
) -> dict[str, object]:
    if not all(math.isfinite(value) for value in (latitude, longitude, hours, elevation)):
        raise ValueError("Coordinates and search parameters must be finite")
    if (
        not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
        or not 0 < hours <= 72
        or not 0 <= elevation < 90
    ):
        raise ValueError("Invalid coordinates, horizon or minimum elevation")
    if start.tzinfo is None:
        raise ValueError("Start time must be timezone-aware")
    lines = [line.strip() for line in tle.splitlines() if line.strip()]
    if len(lines) != 3 or not lines[1].startswith("1 ") or not lines[2].startswith("2 "):
        raise ValueError("Expected one named two-line element record")
    timescale = load.timescale(builtin=True)
    satellite = EarthSatellite(lines[1], lines[2], lines[0], timescale)
    if not satellite.model.no_kozai > 0:
        raise ValueError("Invalid TLE mean motion")
    observer = wgs84.latlon(latitude, longitude)
    beginning = timescale.from_datetime(start)
    ending = timescale.from_datetime(start + timedelta(hours=hours))
    instants, events = satellite.find_events(
        observer, beginning, ending, altitude_degrees=elevation
    )
    altitude = float((satellite - observer).at(beginning).altaz()[0].degrees)
    ongoing = altitude >= elevation
    current: dict[str, object] | None = (
        {"rise_utc": None, "ongoing_at_start": True} if ongoing else None
    )
    next_pass = None
    for instant, event in zip(instants, events, strict=True):
        stamp = instant.utc_datetime().isoformat()
        if event == 0:
            current = {"rise_utc": stamp, "ongoing_at_start": False}
        elif event == 1 and current is not None:
            current.update(
                {
                    "culmination_utc": stamp,
                    "max_elevation_deg": float(
                        (satellite - observer).at(instant).altaz()[0].degrees
                    ),
                }
            )
        elif event == 2 and current is not None:
            current["set_utc"] = stamp
            next_pass = current
            break
    if next_pass is None and current is not None:
        current["set_utc"] = None
        current["truncated_by_search_window"] = True
        next_pass = current
    epoch = satellite.epoch.utc_datetime()
    return {
        "satellite": satellite.name,
        "tle_epoch": epoch.isoformat(),
        "epoch_age_days": (start.astimezone(timezone.utc) - epoch).total_seconds() / 86400,
        "observer": {"latitude": latitude, "longitude": longitude},
        "minimum_elevation_deg": elevation,
        "search_start": start.isoformat(),
        "search_hours": hours,
        "next_pass": next_pass,
    }
