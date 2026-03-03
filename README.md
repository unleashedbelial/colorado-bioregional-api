# 🌊 Colorado River Basin — Open Bioregional Data API

A static JSON API hosted on GitHub Pages that aggregates real-time bioregional data for the **Colorado River Basin**: USGS streamflow, SNOTEL snowpack, OpenAQ air quality, and NASA FIRMS wildfire data.

Updated every **30 minutes** via GitHub Actions.

**Live URL:** https://unleashedbelial.github.io/colorado-bioregional-api/

---

## 📡 API Endpoints

All endpoints return JSON with CORS headers (served via GitHub Pages).

| Endpoint | Description | Source |
|----------|-------------|--------|
| [`/api/data.json`](https://unleashedbelial.github.io/colorado-bioregional-api/api/data.json) | Master file — all datasets + metadata | All sources |
| [`/api/water.json`](https://unleashedbelial.github.io/colorado-bioregional-api/api/water.json) | Streamflow at 4 mainstem gauges | USGS NWIS |
| [`/api/snowpack.json`](https://unleashedbelial.github.io/colorado-bioregional-api/api/snowpack.json) | Snow Water Equivalent (SWE) | USDA SNOTEL |
| [`/api/airquality.json`](https://unleashedbelial.github.io/colorado-bioregional-api/api/airquality.json) | Air quality monitoring stations | OpenAQ v3 |
| [`/api/wildfire.json`](https://unleashedbelial.github.io/colorado-bioregional-api/api/wildfire.json) | Active fires (last 24h) | NASA FIRMS VIIRS |
| [`/api/meta.json`](https://unleashedbelial.github.io/colorado-bioregional-api/api/meta.json) | Metadata, sources, update info | — |

---

## 💧 Water — `water.json`

Real-time streamflow from USGS National Water Information System.

**Gauges:**
| Site ID | Location |
|---------|----------|
| 09380000 | Colorado River at Lees Ferry, AZ |
| 09421500 | Colorado River below Hoover Dam, AZ-NV |
| 09404200 | Colorado River near Grand Canyon, AZ |
| 09095500 | Colorado River near Cameo, CO |

**Example response:**
```json
{
  "source": "USGS National Water Information System",
  "last_updated": "2024-01-15T14:30:00+00:00",
  "unit": "ft3/s (cubic feet per second)",
  "gauges": [
    {
      "site_id": "09380000",
      "site_name": "Colorado River at Lees Ferry, AZ",
      "latitude": 36.8647,
      "longitude": -111.5878,
      "latest": {
        "value": 8240.0,
        "unit": "ft3/s",
        "datetime": "2024-01-15T14:15:00.000-07:00"
      }
    }
  ]
}
```

---

## ❄️ Snowpack — `snowpack.json`

Daily Snow Water Equivalent from USDA NRCS SNOTEL network.

**Station:** 356 — Berthoud Summit, Upper Colorado River Basin

**Example response:**
```json
{
  "source": "USDA Natural Resources Conservation Service SNOTEL",
  "last_updated": "2024-01-15T14:30:00+00:00",
  "stations": [
    {
      "station_id": "356",
      "station_name": "Berthoud Summit",
      "date": "2024-01-15",
      "snow_water_equivalent_inches": 12.3,
      "unit": "inches"
    }
  ]
}
```

---

## 🌬️ Air Quality — `airquality.json`

Air quality monitoring locations within 300km of the basin center (36.5°N, 112.5°W).

**Example response:**
```json
{
  "source": "OpenAQ",
  "coverage": { "center_lat": 36.5, "center_lon": -112.5, "radius_km": 300 },
  "locations": [
    {
      "id": 12345,
      "name": "Grand Canyon NPS",
      "latitude": 36.05,
      "longitude": -112.14,
      "sensors": [
        { "parameter": "pm25", "unit": "µg/m³", "display_name": "PM2.5" }
      ]
    }
  ]
}
```

---

## 🔥 Wildfires — `wildfire.json`

Active fire detections from NASA FIRMS VIIRS satellite data, filtered to the Colorado River Basin bounding box (31–42°N, 107–115°W).

**Example response:**
```json
{
  "source": "NASA FIRMS VIIRS NOAA-20 C2 (24h)",
  "fire_count": 3,
  "fires": [
    {
      "latitude": 35.12,
      "longitude": -110.45,
      "brightness": 312.4,
      "frp": 8.2,
      "confidence": "nominal",
      "acq_date": "2024-01-15",
      "satellite": "VIIRS NOAA-20"
    }
  ]
}
```

---

## 🔧 Usage Examples

### JavaScript / Fetch API
```javascript
// Get all data
const data = await fetch(
  "https://unleashedbelial.github.io/colorado-bioregional-api/api/data.json"
).then(r => r.json());

console.log("Active fires:", data.wildfire.fire_count);
console.log("Lees Ferry flow:", data.water.gauges[0].latest?.value, "ft³/s");
```

### Python
```python
import urllib.request, json

BASE = "https://unleashedbelial.github.io/colorado-bioregional-api"

with urllib.request.urlopen(f"{BASE}/api/water.json") as r:
    water = json.loads(r.read())

for gauge in water["gauges"]:
    flow = gauge["latest"]["value"] if gauge["latest"] else "N/A"
    print(f"{gauge['site_name']}: {flow} ft³/s")
```

### curl
```bash
curl -s https://unleashedbelial.github.io/colorado-bioregional-api/api/meta.json | python3 -m json.tool
```

---

## 🏗️ Architecture

```
GitHub Actions (every 30 min)
       │
       ▼
  fetch_data.py
  ├── USGS NWIS API ──────────▶ api/water.json
  ├── USDA SNOTEL CSV ────────▶ api/snowpack.json
  ├── OpenAQ v3 API ──────────▶ api/airquality.json
  └── NASA FIRMS CSV ─────────▶ api/wildfire.json
                                     │
                                     ▼
                               api/data.json (master)
                               api/meta.json
                                     │
                               git commit + push
                                     │
                               GitHub Pages serves
                               static JSON files
```

---

## 📦 Setup (self-hosting)

1. Fork this repo
2. Enable GitHub Pages: Settings → Pages → Source: main branch, root `/`
3. (Optional) Add `FIRMS_MAP_KEY` secret for NASA FIRMS API access
4. The workflow runs automatically every 30 minutes

---

## 📊 Data Sources

| Source | License | Homepage |
|--------|---------|----------|
| USGS NWIS | Public domain | https://waterservices.usgs.gov/ |
| USDA SNOTEL | Public domain | https://www.nrcs.usda.gov/ |
| OpenAQ | CC BY 4.0 | https://openaq.org/ |
| NASA FIRMS | Public domain | https://firms.modaps.eosdis.nasa.gov/ |

---

## 🤝 Contributing

Issues and PRs welcome. The fetch script is plain Python 3 with no external dependencies.

---

*Built for the open bioregional data commons. Colorado River Basin — 246,000 mi².*
