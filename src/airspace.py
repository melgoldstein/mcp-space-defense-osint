"""ICAO Q-line center/radius to antimeridian-aware GeoJSON bounding envelopes."""

import math
import re

COORDINATES = re.compile(r"(?<!\d)(\d{2})(\d{2})([NS])\s*(\d{3})(\d{2})([EW])\s*(\d{3})(?!\d)")


def analyze_notam_tfr(notice: str) -> dict[str, object]:
    if len(notice) > 100_000:
        raise ValueError("Notice exceeds 100,000 characters")
    match = COORDINATES.search(notice.upper())
    if not match:
        raise ValueError("Expected ICAO center/radius, for example 2825N08036W010")
    latitude_deg, latitude_min, ns, longitude_deg, longitude_min, ew, radius = match.groups()
    lat = int(latitude_deg) + int(latitude_min) / 60
    lon = int(longitude_deg) + int(longitude_min) / 60
    if (
        int(latitude_min) >= 60
        or int(longitude_min) >= 60
        or lat > 90
        or lon > 180
        or int(radius) == 0
    ):
        raise ValueError("Invalid center or radius")
    lat *= -1 if ns == "S" else 1
    lon *= -1 if ew == "W" else 1
    angular = int(radius) * 1852 / 6371008.8
    delta_lat = math.degrees(angular)
    south, north = max(-90, lat - delta_lat), min(90, lat + delta_lat)
    if south == -90 or north == 90:
        west, east = -180.0, 180.0
    else:
        delta_lon = math.degrees(math.asin(min(1, math.sin(angular) / math.cos(math.radians(lat)))))
        west, east = (lon - delta_lon + 180) % 360 - 180, (lon + delta_lon + 180) % 360 - 180

    def ring(left: float, right: float) -> list[list[float]]:
        return [[left, south], [right, south], [right, north], [left, north], [left, south]]

    geometry = (
        {"type": "Polygon", "coordinates": [ring(west, east)]}
        if west <= east
        else {"type": "MultiPolygon", "coordinates": [[ring(west, 180)], [ring(-180, east)]]}
    )
    return {
        "type": "Feature",
        "bbox": [west, south, east, north],
        "geometry": geometry,
        "properties": {
            "center": [lon, lat],
            "radius_nm": int(radius),
            "geometry_role": "Q-line bounding envelope; not the legal restriction boundary",
        },
    }
