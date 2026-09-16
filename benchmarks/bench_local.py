"""Measure cached reads and notice parsing without claiming network latency."""

import json
import platform
import statistics
import time
from pathlib import Path

from space_defense_osint.airspace import analyze_notam_tfr
from space_defense_osint.feeds import FeedClient


def main():
    client = FeedClient(lambda _: '{"kp":3}')
    client.get("fixture")
    results = {}
    for name, operation in {
        "cached_feed_read": lambda: client.get("fixture"),
        "json_parse_uncached": lambda: json.loads('{"kp":3}'),
        "q_line_geojson": lambda: analyze_notam_tfr("2825N08036W010"),
    }.items():
        elapsed = []
        for _ in range(1000):
            start = time.perf_counter_ns()
            operation()
            elapsed.append((time.perf_counter_ns() - start) / 1000)
        results[name] = statistics.median(elapsed)
    Path("benchmarks/results.json").write_text(
        json.dumps(
            {
                "platform": platform.platform(),
                "iterations": 1000,
                "median_us": results,
                "network_included": False,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
