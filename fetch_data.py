#!/usr/bin/env python3
"""
Colorado River Basin Bioregional Data Aggregator
Fetches data from USGS, SNOTEL, OpenAQ, and NASA FIRMS
Outputs static JSON files to api/ directory
"""

import json
import os
import sys
import csv
import io
import re
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

API_DIR = os.path.join(os.path.dirname(__file__), "api")
os.makedirs(API_DIR, exist_ok=True)

NOW = datetime.now(timezone.utc).isoformat()

USGS_SITES = {
    "09380000": "Colorado River at Lees Ferry, AZ",
    "09421500": "Colorado River below Hoover Dam, AZ-NV",
    "09404200": "Colorado River near Grand Canyon, AZ",
    "09095500": "Colorado River near Cameo, CO",
}

FIRMS_MAP_KEY = os.environ.get("FIRMS_MAP_KEY", "")
OPENAQ_API_KEY = os.environ.get("OPENAQ_API_KEY", "")


def fetch_url(url, headers=None, timeout=30):
    req = Request(url, headers=headers or {"User-Agent": "BioregionalAPI/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except HTTPError as e:
        print(f"  HTTP {e.code} for {url}", file=sys.stderr)
        return None
    except URLError as e:
        print(f"  URL error for {url}: {e.reason}", file=sys.stderr)
        return None
    except (TimeoutError, OSError) as e:
        print(f"  Timeout/OS error for {url}: {e}", file=sys.stderr)
        return None


# ── USGS Streamflow ──────────────────────────────────────────────────────────

def fetch_water():
    print("Fetching USGS streamflow...")
    sites = ",".join(USGS_SITES.keys())
    url = (
        f"https://waterservices.usgs.gov/nwis/iv/"
        f"?sites={sites}&parameterCd=00060&format=json&siteStatus=all"
    )
    raw = fetch_url(url)
    gauges = []
    if raw:
        try:
            data = json.loads(raw)
            for ts in data.get("value", {}).get("timeSeries", []):
                site_code = ts["sourceInfo"]["siteCode"][0]["value"]
                site_name = ts["sourceInfo"]["siteName"]
                values = ts.get("values", [{}])[0].get("value", [])
                latest = None
                if values:
                    v = values[-1]
                    val = v.get("value")
                    try:
                        val = float(val) if val not in (None, "-999999") else None
                    except (ValueError, TypeError):
                        val = None
                    latest = {
                        "value": val,
                        "unit": "ft3/s",
                        "datetime": v.get("dateTime"),
                        "qualifiers": v.get("qualifiers", []),
                    }
                gauges.append({
                    "site_id": site_code,
                    "site_name": USGS_SITES.get(site_code, site_name),
                    "latitude": ts["sourceInfo"]["geoLocation"]["geogLocation"]["latitude"],
                    "longitude": ts["sourceInfo"]["geoLocation"]["geogLocation"]["longitude"],
                    "parameter": "Streamflow",
                    "latest": latest,
                })
        except (KeyError, json.JSONDecodeError, IndexError) as e:
            print(f"  Parse error: {e}", file=sys.stderr)

    result = {
        "source": "USGS National Water Information System",
        "source_url": "https://waterservices.usgs.gov/",
        "description": "Real-time streamflow for Colorado River Basin gauges",
        "unit": "ft3/s (cubic feet per second)",
        "last_updated": NOW,
        "gauges": gauges,
    }
    _write("water.json", result)
    print(f"  ✓ {len(gauges)} gauges")
    return result


# ── SNOTEL Snowpack ──────────────────────────────────────────────────────────

def fetch_snowpack():
    print("Fetching SNOTEL snowpack...")
    url = (
        "https://wcc.sc.egov.usda.gov/reportGenerator/view_csv/"
        "customSingleStationReport/daily/356:CO:SNOTEL|name,wteq::value"
    )
    raw = fetch_url(url)
    stations = []
    if raw:
        try:
            lines = [l for l in raw.splitlines() if not l.startswith("#") and l.strip()]
            reader = csv.reader(io.StringIO("\n".join(lines)))
            headers = None
            rows = []
            for row in reader:
                if headers is None:
                    headers = [h.strip() for h in row]
                else:
                    rows.append(row)

            # Most recent row
            if rows:
                latest_row = rows[-1]
                record = dict(zip(headers, [v.strip() for v in latest_row]))
                date_str = record.get("Date", "")
                swe_raw = None
                for k, v in record.items():
                    if "Snow Water Equivalent" in k or "WTEQ" in k.upper() or (k != "Date" and k != "Station Name"):
                        try:
                            swe_raw = float(v)
                            break
                        except (ValueError, TypeError):
                            pass

                # Try a simple positional approach if parsing failed
                if swe_raw is None and len(latest_row) >= 2:
                    for v in latest_row[1:]:
                        try:
                            swe_raw = float(v.strip())
                            break
                        except (ValueError, TypeError):
                            pass

                stations.append({
                    "station_id": "356",
                    "station_name": "Berthoud Summit",
                    "network": "SNOTEL",
                    "state": "CO",
                    "basin": "Upper Colorado River Basin",
                    "date": date_str,
                    "snow_water_equivalent_inches": swe_raw,
                    "unit": "inches",
                })
        except Exception as e:
            print(f"  Parse error: {e}", file=sys.stderr)

    result = {
        "source": "USDA Natural Resources Conservation Service SNOTEL",
        "source_url": "https://www.nrcs.usda.gov/wps/portal/wcc/home/",
        "description": "Snow Water Equivalent (SWE) for Upper Colorado River Basin SNOTEL stations",
        "last_updated": NOW,
        "stations": stations,
    }
    _write("snowpack.json", result)
    print(f"  ✓ {len(stations)} station(s)")
    return result


# ── OpenAQ Air Quality ───────────────────────────────────────────────────────

def fetch_airquality():
    print("Fetching air quality...")
    locations = []
    source_used = "OpenAQ"
    note = None

    # Try OpenAQ v3 with API key if available
    if OPENAQ_API_KEY:
        url = (
            "https://api.openaq.org/v3/locations"
            "?coordinates=36.5,-112.5&radius=300000&limit=20"
        )
        raw = fetch_url(url, headers={
            "User-Agent": "BioregionalAPI/1.0",
            "Accept": "application/json",
            "X-API-Key": OPENAQ_API_KEY,
        })
        if raw:
            try:
                data = json.loads(raw)
                for loc in data.get("results", []):
                    sensors = []
                    for sensor in loc.get("sensors", []):
                        sensors.append({
                            "parameter": sensor.get("parameter", {}).get("name"),
                            "unit": sensor.get("parameter", {}).get("units"),
                            "display_name": sensor.get("parameter", {}).get("displayName"),
                        })
                    locations.append({
                        "id": loc.get("id"),
                        "name": loc.get("name"),
                        "locality": loc.get("locality"),
                        "country": loc.get("country", {}).get("code"),
                        "latitude": loc.get("coordinates", {}).get("latitude"),
                        "longitude": loc.get("coordinates", {}).get("longitude"),
                        "is_monitor": loc.get("isMonitor"),
                        "sensors": sensors,
                        "last_updated": (
                            loc.get("datetimeLast", {}).get("utc")
                            if isinstance(loc.get("datetimeLast"), dict)
                            else loc.get("datetimeLast")
                        ),
                    })
                source_used = "OpenAQ v3"
            except (KeyError, json.JSONDecodeError) as e:
                print(f"  OpenAQ parse error: {e}", file=sys.stderr)
    else:
        note = "OPENAQ_API_KEY not set; add as GitHub Actions secret for live data"
        print(f"  ⚠ {note}", file=sys.stderr)

    # Fallback: AirNow monitoring stations near basin (public, no key for station list)
    if not locations:
        # Use AirNow API (requires free API key, but reportingArea endpoint is public)
        airnow_url = (
            "https://www.airnowapi.org/aq/observation/zipCode/current/"
            "?format=application/json&zipCode=86023&distance=200&API_KEY=test"
        )
        # Note: AirNow also needs a key, so we use a static fallback with known monitoring sites
        locations = _static_airquality_stations()
        if locations:
            source_used = "Static monitoring station index (OpenAQ key required for live data)"

    result = {
        "source": source_used,
        "source_url": "https://openaq.org/",
        "description": "Air quality monitoring locations within 300km of Colorado River Basin center (36.5°N, 112.5°W)",
        "note": note,
        "coverage": {
            "center_lat": 36.5,
            "center_lon": -112.5,
            "radius_km": 300,
        },
        "last_updated": NOW,
        "locations": locations,
    }
    _write("airquality.json", result)
    print(f"  ✓ {len(locations)} location(s)")
    return result


def _static_airquality_stations():
    """Known EPA/OpenAQ monitoring stations in or near the Colorado River Basin.
    These are real stations; live readings require an OpenAQ API key."""
    return [
        {"name": "Grand Canyon NPS", "latitude": 36.0544, "longitude": -112.1401,
         "locality": "Grand Canyon", "country": "US",
         "sensors": [{"parameter": "pm25", "unit": "µg/m³", "display_name": "PM2.5"},
                     {"parameter": "ozone", "unit": "ppb", "display_name": "Ozone"}]},
        {"name": "Flagstaff", "latitude": 35.1983, "longitude": -111.6513,
         "locality": "Flagstaff", "country": "US",
         "sensors": [{"parameter": "pm25", "unit": "µg/m³", "display_name": "PM2.5"},
                     {"parameter": "pm10", "unit": "µg/m³", "display_name": "PM10"}]},
        {"name": "Moab", "latitude": 38.5733, "longitude": -109.5498,
         "locality": "Moab", "country": "US",
         "sensors": [{"parameter": "pm25", "unit": "µg/m³", "display_name": "PM2.5"}]},
        {"name": "Las Vegas - East Charleston", "latitude": 36.1699, "longitude": -115.1398,
         "locality": "Las Vegas", "country": "US",
         "sensors": [{"parameter": "pm25", "unit": "µg/m³", "display_name": "PM2.5"},
                     {"parameter": "no2", "unit": "ppb", "display_name": "NO2"}]},
        {"name": "St. George", "latitude": 37.0965, "longitude": -113.5684,
         "locality": "St. George", "country": "US",
         "sensors": [{"parameter": "pm25", "unit": "µg/m³", "display_name": "PM2.5"}]},
        {"name": "Page", "latitude": 36.9147, "longitude": -111.4424,
         "locality": "Page", "country": "US",
         "sensors": [{"parameter": "pm25", "unit": "µg/m³", "display_name": "PM2.5"},
                     {"parameter": "ozone", "unit": "ppb", "display_name": "Ozone"}]},
    ]


# ── Wildfire (NASA FIRMS or USFS public) ────────────────────────────────────

def fetch_wildfire():
    print("Fetching wildfire data...")
    fires = []
    source_used = None

    # Try NASA FIRMS with API key if available
    if FIRMS_MAP_KEY:
        # Bounding box: Colorado River Basin roughly (31-42°N, 107-115°W)
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{FIRMS_MAP_KEY}/VIIRS_SNPP_NRT/-115,31,-107,42/1"
        )
        raw = fetch_url(url)
        if raw and "latitude" in raw.lower():
            try:
                reader = csv.DictReader(io.StringIO(raw))
                for row in reader:
                    fires.append({
                        "latitude": float(row.get("latitude", 0)),
                        "longitude": float(row.get("longitude", 0)),
                        "brightness": _safe_float(row.get("bright_ti4") or row.get("brightness")),
                        "frp": _safe_float(row.get("frp")),
                        "confidence": row.get("confidence"),
                        "acq_date": row.get("acq_date"),
                        "acq_time": row.get("acq_time"),
                        "satellite": row.get("satellite", "VIIRS SNPP"),
                    })
                source_used = "NASA FIRMS VIIRS SNPP NRT"
            except Exception as e:
                print(f"  FIRMS parse error: {e}", file=sys.stderr)

    # Fallback: NASA FIRMS public world fire CSV (no key needed, last 24h)
    if not fires:
        url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv"
        raw = fetch_url(url)
        if raw and "latitude" in raw.lower():
            try:
                reader = csv.DictReader(io.StringIO(raw))
                # Filter for Colorado River Basin bounding box
                for row in reader:
                    lat = _safe_float(row.get("latitude"))
                    lon = _safe_float(row.get("longitude"))
                    if lat and lon and 31 <= lat <= 42 and -115 <= lon <= -107:
                        fires.append({
                            "latitude": lat,
                            "longitude": lon,
                            "brightness": _safe_float(row.get("bright_ti4") or row.get("brightness")),
                            "frp": _safe_float(row.get("frp")),
                            "confidence": row.get("confidence"),
                            "acq_date": row.get("acq_date"),
                            "acq_time": row.get("acq_time"),
                            "satellite": row.get("satellite", "VIIRS NOAA-20"),
                        })
                source_used = "NASA FIRMS VIIRS NOAA-20 C2 (24h)"
            except Exception as e:
                print(f"  FIRMS public parse error: {e}", file=sys.stderr)

    result = {
        "source": source_used or "NASA FIRMS",
        "source_url": "https://firms.modaps.eosdis.nasa.gov/",
        "description": "Active wildfires in the Colorado River Basin (31-42°N, 107-115°W), last 24 hours",
        "coverage_bbox": {
            "min_lat": 31, "max_lat": 42,
            "min_lon": -115, "max_lon": -107,
        },
        "last_updated": NOW,
        "fire_count": len(fires),
        "fires": fires,
    }
    _write("wildfire.json", result)
    print(f"  ✓ {len(fires)} fire detection(s)")
    return result


# ── Master + Meta ────────────────────────────────────────────────────────────

def build_master(water, snowpack, airquality, wildfire):
    result = {
        "last_updated": NOW,
        "coverage": {
            "region": "Colorado River Basin",
            "bbox": {"min_lat": 31, "max_lat": 42, "min_lon": -115, "max_lon": -107},
            "description": "Includes Colorado, Utah, Nevada, Arizona, California, New Mexico, Wyoming",
        },
        "endpoints": {
            "data": "/api/data.json",
            "water": "/api/water.json",
            "snowpack": "/api/snowpack.json",
            "airquality": "/api/airquality.json",
            "wildfire": "/api/wildfire.json",
            "meta": "/api/meta.json",
        },
        "water": water,
        "snowpack": snowpack,
        "airquality": airquality,
        "wildfire": wildfire,
    }
    _write("data.json", result)

    meta = {
        "last_updated": NOW,
        "update_frequency": "every 30 minutes via GitHub Actions",
        "region": "Colorado River Basin",
        "sources": [
            {
                "name": "USGS NWIS",
                "url": "https://waterservices.usgs.gov/",
                "endpoint": "/api/water.json",
                "parameters": ["streamflow (ft3/s)"],
            },
            {
                "name": "USDA SNOTEL",
                "url": "https://www.nrcs.usda.gov/wps/portal/wcc/home/",
                "endpoint": "/api/snowpack.json",
                "parameters": ["snow water equivalent (inches)"],
            },
            {
                "name": "OpenAQ",
                "url": "https://openaq.org/",
                "endpoint": "/api/airquality.json",
                "parameters": ["PM2.5", "PM10", "O3", "NO2", "CO"],
            },
            {
                "name": "NASA FIRMS",
                "url": "https://firms.modaps.eosdis.nasa.gov/",
                "endpoint": "/api/wildfire.json",
                "parameters": ["fire radiative power (MW)", "brightness temperature (K)"],
            },
        ],
        "license": "Public domain / open data",
        "maintainer": "unleashedbelial",
        "github": "https://github.com/unleashedbelial/colorado-bioregional-api",
    }
    _write("meta.json", meta)
    print("  ✓ data.json + meta.json written")


def _write(filename, data):
    path = os.path.join(API_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


if __name__ == "__main__":
    print(f"=== Colorado River Basin Data Fetch — {NOW} ===\n")
    water = fetch_water()
    snowpack = fetch_snowpack()
    airquality = fetch_airquality()
    wildfire = fetch_wildfire()
    build_master(water, snowpack, airquality, wildfire)
    print("\n✅ All done.")
