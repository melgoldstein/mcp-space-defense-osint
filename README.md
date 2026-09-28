# mcp-space-defense-osint

A stdio MCP server for public orbital context, geomagnetic conditions and structured
airspace envelopes. Built on the official MCP SDK, Skyfield/SGP4 and HTTPX.
MIT licensed; Python 3.11+. No API keys required.

## Quickstart (30 Seconds)

```bash
git clone https://github.com/cankaan120/mcp-space-defense-osint.git
cd mcp-space-defense-osint
python -m venv .venv
.venv/bin/python -m pip install '.[dev]'
.venv/bin/space-defense-osint --check
```

Windows equivalents are `.venv\Scripts\python.exe` and
`.venv\Scripts\space-defense-osint.exe`. `--check` performs a local parser check.
Without arguments the CLI serves MCP over stdio; logs go to stderr.

## Claude Desktop configuration

Add this to `claude_desktop_config.json`, selecting the absolute Python path of the
environment where the package is installed. Restart the host after saving.

```json
{
  "mcpServers": {
    "space-defense-osint": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "space_defense_osint.server"]
    }
  }
}
```

Windows command example: `C:\\Users\\you\\tools\\.venv\\Scripts\\python.exe`.
Configuration paths: `%APPDATA%\Claude\claude_desktop_config.json` on Windows and
`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS.
Cursor accepts the same `mcpServers` entry in `.cursor/mcp.json`.
See the [SDK host guide](https://py.sdk.modelcontextprotocol.io/get-started/real-host/)
and [Cursor documentation](https://docs.cursor.com/context/model-context-protocol).

## Tools

| Tool | Inputs | Result |
| --- | --- | --- |
| `fetch_celestrak_tle` | Catalog ID, location, horizon, minimum elevation | TLE, epoch age, next pass, source and retrieval timestamp |
| `query_noaa_swpc_kp` | None | Latest observed Kp, SWPC alerts, age and cache metadata |
| `analyze_notam_tfr` | Notice with ICAO center/radius | GeoJSON bounding envelope, bbox, center and radius |

Pass defaults: Cape Canaveral `28.4158, -80.6048`, ISS 25544, 24-hour horizon and
10-degree minimum elevation. The horizon is bounded to 72 hours. Results identify ongoing
passes and truncated search windows. A null pass means no qualifying pass was found.
These are geometric passes, not optical-visibility forecasts.

TLE requests are cached for one hour, NOAA for 60 seconds. Cache hits retain original
retrieval timestamps. Requests have a 15-second timeout and two-megabyte body budget.
Errors do not silently substitute stale results. NOAA observation age is reported
separately; values older than six hours are marked stale. Current object-based and
legacy table-based Kp layouts are both supported.

The NOTAM parser supports Q-line coordinates such as `2825N08036W010` with radius
in nautical miles. Dateline crossings produce a MultiPolygon. This is a bounding
envelope, not a legal TFR boundary. Arbitrary polygons and free-form descriptions are
rejected. The tool parses supplied notices; it does not fetch current airspace restrictions.

## Python API

```python
from space_defense_osint.server import fetch_celestrak_tle
from space_defense_osint.airspace import analyze_notam_tfr

geometry = analyze_notam_tfr("Q) KZMA/QWALW/IV/M/W/000/999/2825N08036W010")
pass_context = fetch_celestrak_tle(catalog_id=25544)
```

## Benchmark comparison

Local medians over 1,000 iterations on Windows x64:

| Operation | Median, us | Network included |
| --- | ---: | --- |
| Cached feed read | 0.30 | No |
| Reparse small JSON fixture | 0.90 | No |
| Q-line to GeoJSON | 2.80 | No |

Caching avoids repeated decoding and upstream requests. These operations differ in
semantics; their timings do not estimate live-feed or orbital-prediction latency.
Run `python benchmarks/bench_local.py`. [Results](benchmarks/results.json) record the platform.

## Validation and sources

`python -m pytest` runs offline geometry, caching, Kp-layout, pass-ordering and real MCP
stdio handshake/tool-call tests. Live NOAA and CelesTrak checks also passed during development.
Live availability varies; consumers should inspect TLE epoch age before using predictions.
Legacy TLE catalog identifiers above 99999 require an OMM interface and are not supported.

- [CelesTrak GP interface](https://celestrak.org/NORAD/documentation/gp-data-formats.php)
- [Skyfield passes](https://rhodesmill.org/skyfield/earth-satellites.html)
- [NOAA SWPC products](https://services.swpc.noaa.gov/products/)
- [FAA Q-line reference](https://www.faa.gov/air_traffic/flight_info/aeronav/notams/media/ICAO_NOTAM_Format_Example.pdf)
