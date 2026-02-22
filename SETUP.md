# 🎯 LeadGen India — Setup Guide

## Files
```
leadgen/
├── app.py              ← Streamlit dashboard
├── pipeline.py         ← Main orchestrator
├── cron_job.py         ← Daily scheduled run
├── requirements.txt
├── render.yaml         ← Render deployment config
└── core/
    ├── scraper.py      ← SerpAPI + website scraping
    ├── scorer.py       ← Rule-based + AI scoring
    └── sheets.py       ← Google Sheets + Hunter.io
```

---

## Step 1 — Google Sheets (Service Account)

OAuth se problem ho raha tha, **Service Account** use karo instead:

1. Google Cloud Console → https://console.cloud.google.com
2. **New Project** banao → "LeadGen"
3. **APIs & Services** → Enable karo:
   - Google Sheets API
   - Google Drive API
4. **Credentials** → Create Credentials → **Service Account**
   - Name: `leadgen-sa`
   - Role: Editor
5. Service account par click karo → **Keys** tab → **Add Key** → JSON
6. JSON file download hogi — yeh `GOOGLE_SERVICE_ACCOUNT_JSON` mein jaayega
7. Apni Google Sheet open karo → Share karo service account email pe (Editor access)
   - Email looks like: `leadgen-sa@your-project.iam.gserviceaccount.com`

---

## Step 2 — Local Test

```bash
cd leadgen

# Install dependencies
pip install -r requirements.txt

# Setup .env file
cp .env.example .env
# Edit .env and add your API keys

# Add your service account JSON file
# Option 1: Save as service_account.json in project root
# Option 2: Add full JSON to .env as GOOGLE_SERVICE_ACCOUNT_JSON

# Test configuration
python config.py

# Test cron job
python cron_job.py

# Test Streamlit
streamlit run app.py
```

### Service Account JSON Setup

You have 2 options:

**Option 1: Use JSON file (Recommended for local development)**
1. Save your downloaded JSON file as `service_account.json` in project root
2. File will be auto-loaded by config.py
3. File is gitignored for security

**Option 2: Use environment variable (Required for Render deployment)**
1. Open your service_account.json file
2. Copy the entire JSON content
3. Add to .env file: `GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'`
4. Or set as environment variable on Render

---

## Step 3 — Render Deploy

### Option A: render.yaml (recommended)
1. GitHub repo mein push karo saari files
2. Render → **New** → **Blueprint** → repo connect karo
3. render.yaml automatically dono services banayega

### Option B: Manual
**Streamlit Dashboard:**
- New Web Service → Python
- Build: `pip install -r requirements.txt`
- Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`

**Cron Job:**
- New Cron Job → Python
- Schedule: `30 0 * * *` (6 AM IST)
- Command: `python cron_job.py`

### Environment Variables (dono services mein add karo):
| Variable | Value |
|----------|-------|
| `SERPAPI_KEY` | badad92336... |
| `OPENROUTER_KEY` | sk-or-v1-edb5... |
| `HUNTER_KEY` | d324598798... |
| `SHEET_ID` | 1TJE2gs4J19L6Fh... |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON string (service account) |
| `MIN_SCORE` | 7 |

---

## Step 4 — Google Sheets Setup

Sheet mein 2 tabs banana:
1. **Leads** — leads store honge
2. **Errors** — errors log honge

Headers automatically create ho jaayenge first run mein.

---

## How It Works

```
SerpAPI Maps Search (5 queries × 20 results = ~100 leads)
    ↓
Global Dedup (by name)
    ↓
Concurrent Website Scraping (5 at a time)
    ↓
Rule-Based Fast Filter
  • No website → Score 10, skip AI
  • Instagram only → Score 9, skip AI  
  • Has website → Score 1-8 by missing signals
    ↓
AI Scoring (only for rule_score ≥ 5)
  • OpenRouter / Gemini Flash
  • Retry on 429 (3 attempts)
  • Fallback to rule score if AI fails
    ↓
Filter (score ≥ 7)
    ↓
Hunter.io Email Enrichment
    ↓
Google Sheets (dedup by name+phone)
```

## Expected Output Per Run
- ~100 raw leads scraped
- ~60 after dedup
- ~25-35 rule_score ≥ 5 (sent to AI)
- ~15-20 final qualified leads (score ≥ 7)
- ~35-40 after 7 day rotation (new queries daily)

## Cron Schedule (Weekly Rotation)
- Monday: Healthcare (dental, skin, physio)
- Tuesday: Wedding industry
- Wednesday: Fitness & wellness
- Thursday: Finance & legal
- Friday: Interior design & home
- Saturday: Education & coaching
- Sunday: Food & restaurants
