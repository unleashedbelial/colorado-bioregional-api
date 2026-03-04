# 🌊 Colorado River Basin — Open Bioregional Data API

Real-time bioregional data for the **Colorado River Basin**: USGS streamflow, SNOTEL snowpack, OpenAQ air quality, and NASA FIRMS wildfire detections.

Two deployment flavors — use whichever fits your use case:

| Flavor | URL | Best for |
|--------|-----|----------|
| **Live FastAPI** | `https://bioregionalapi.belial.lol` | Real-time queries, Swagger UI, low-latency |
| **Static JSON** (GitHub Pages) | `https://unleashedbelial.github.io/colorado-bioregional-api` | No-backend clients, simple GET, caching |

---

## 🚀 Live API — `bioregionalapi.belial.lol`

FastAPI running on a VPS, refreshed on every request (30-min in-memory cache).

**Interactive docs:** [`https://bioregionalapi.belial.lol/docs`](https://bioregionalapi.belial.lol/docs)

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Endpoint index + metadata |
| `GET` | `/health` | Service health + cache status |
| `GET` | `/water` | USGS streamflow gauges |
| `GET` | `/snowpack` | SNOTEL snow water equivalent |
| `GET` | `/airquality` | OpenAQ air quality stations |
| `GET` | `/wildfire` | NASA FIRMS active fires (24h) |
| `GET` | `/all` | All datasets combined |

### Quick start

```bash
# Health check
curl https://bioregionalapi.belial.lol/health

# Water levels
curl https://bioregionalapi.belial.lol/water | python3 -m json.tool

# Everything at once
curl https://bioregionalapi.belial.lol/all | python3 -m json.tool
```

### Python
```python
import httpx

BASE = "https://bioregionalapi.belial.lol"

# All data in one shot
data = httpx.get(f"{BASE}/all").json()

print("Lees Ferry flow:", data["water"]["gauges"][0]["latest"]["value"], "ft³/s")
print("Active fires:", data["wildfire"]["fire_count"])
print("Snowpack (SWE):", data["snowpack"]["stations"][0]["snow_water_equivalent_inches"], "in")
```

### JavaScript
```javascript
const BASE = "https://bioregionalapi.belial.lol";

const { water, snowpack, wildfire } = await fetch(`${BASE}/all`).then(r => r.json());

console.log("Flow:", water.gauges[0].latest?.value, "ft³/s");
console.log("Fires:", wildfire.fire_count);
```

---

## 📦 Static JSON API — GitHub Pages

Refreshed every 30 minutes via GitHub Actions. CORS open. No server needed.

**Base URL:** `https://unleashedbelial.github.io/colorado-bioregional-api`

| Endpoint | Description |
|----------|-------------|
| [`/api/data.json`](https://unleashedbelial.github.io/colorado-bioregional-api/api/data.json) | All datasets combined |
| [`/api/water.json`](https://unleashedbelial.github.io/colorado-bioregional-api/api/water.json) | USGS streamflow |
| [`/api/snowpack.json`](https://unleashedbelial.github.io/colorado-bioregional-api/api/snowpack.json) | SNOTEL snowpack |
| [`/api/airquality.json`](https://unleashedbelial.github.io/colorado-bioregional-api/api/airquality.json) | Air quality |
| [`/api/wildfire.json`](https://unleashedbelial.github.io/colorado-bioregional-api/api/wildfire.json) | Active fires (24h) |
| [`/api/meta.json`](https://unleashedbelial.github.io/colorado-bioregional-api/api/meta.json) | Metadata + last update |

---

## 🛠 Self-hosting the FastAPI

### Requirements

- Python 3.10+
- pip

### Install

```bash
git clone https://github.com/unleashedbelial/colorado-bioregional-api.git
cd colorado-bioregional-api

pip install -r requirements.txt
```

`requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
httpx==0.27.2
```

### Run

```bash
# Development
uvicorn main:app --reload --port 3006

# Production
uvicorn main:app --host 0.0.0.0 --port 3006 --workers 2
```

API available at `http://localhost:3006` · Swagger at `http://localhost:3006/docs`

### Run with PM2 (persistent)

```bash
npm install -g pm2

pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

`ecosystem.config.js` is included in the repo.

### Docker (optional)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
EXPOSE 3006
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3006"]
```

```bash
docker build -t bioregional-api .
docker run -p 3006:3006 bioregional-api
```

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────┐
│               Live FastAPI                  │
│         bioregionalapi.belial.lol           │
│                                             │
│  GET /water ─────▶ USGS NWIS API           │
│  GET /snowpack ──▶ USDA SNOTEL CSV         │
│  GET /airquality ▶ OpenAQ v3 API           │
│  GET /wildfire ──▶ NASA FIRMS CSV          │
│                    (30-min in-memory cache) │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│           Static JSON (GitHub Pages)        │
│                                             │
│  GitHub Actions (*/30 * * * *)              │
│       └─▶ fetch_data.py                     │
│            ├─▶ api/water.json               │
│            ├─▶ api/snowpack.json            │
│            ├─▶ api/airquality.json          │
│            ├─▶ api/wildfire.json            │
│            └─▶ api/data.json (master)       │
│                     │                       │
│               git commit + push             │
│                     │                       │
│            GitHub Pages serves              │
└─────────────────────────────────────────────┘
```

---

## 📊 Data Sources

| Source | Data | License |
|--------|------|---------|
| [USGS NWIS](https://waterservices.usgs.gov/) | Streamflow gauges | Public domain |
| [USDA SNOTEL](https://www.nrcs.usda.gov/wps/portal/wcc/home/) | Snow water equivalent | Public domain |
| [OpenAQ](https://openaq.org/) | Air quality | CC BY 4.0 |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) | Active fire detections | Public domain |

---

## 🌍 Coverage

Colorado River Basin — 246,000 mi² across 7 US states and Mexico.

Bounding box: `31–42°N, 107–115°W`

**Key gauges monitored:**

| USGS Site | Location |
|-----------|----------|
| 09380000 | Colorado River at Lees Ferry, AZ |
| 09421500 | Colorado River below Hoover Dam, AZ-NV |
| 09404200 | Colorado River near Grand Canyon, AZ |
| 09095500 | Colorado River near Cameo, CO |

---

## 🤝 Contributing

Issues and PRs welcome. `fetch_data.py` is pure Python stdlib — no external deps. `main.py` uses FastAPI + httpx.

---

*Built for the open bioregional data commons.*
