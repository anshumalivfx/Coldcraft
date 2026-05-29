# Coldcraft

A Python agent that reads a CSV of leads, scrapes each company's website,
extracts the single best "hook", and writes a personalized cold email using Claude.

Built in public. Follow the journey: @YourHandle

---

## Setup

```bash
# 1. Clone and install
pip install -r requirements.txt
playwright install chromium

# 2. Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Edit leads.csv with your targets

# 4. Run
python main.py

# Options
python main.py --your-name "Anshi" --your-product "Humanoid — AI marketing for SaaS"
python main.py --skip-scrape   # faster, no browser, less personalized
python main.py --csv my_leads.csv
```

---

## How it works

1. **Scrape** — Playwright opens each company homepage, extracts hero text,
   meta description, and about section
2. **Hook extraction** — Claude reads the scraped context and finds the single
   most specific, compelling angle (not generic praise)
3. **Email writing** — Claude writes a 4-5 sentence email built around that hook
4. **Quality gate** — If the personalization score is below 7/10, Claude
   auto-retries with stricter instructions

---

## CSV format

```csv
name,company,role,website,linkedin_url
Sarah Chen,Notion,Head of Growth,https://notion.so,https://linkedin.com/in/sarahchen
```

Required columns: `name`, `company`, `role`, `website`
Optional: `linkedin_url` (used in Week 2 for LinkedIn scraping)

---

## Cost

~$0.006 per lead (claude-sonnet-4-6, 2 API calls per lead)
100 leads ≈ $0.60

---

## Week 2 roadmap

- [ ] Celery + Redis for parallel processing (100 leads in 3 min)
- [ ] LinkedIn scraping for recent posts / activity
- [ ] Django models for lead status tracking
- [ ] Auto-retry until score >= 7
- [ ] SendGrid/SES integration for actual sending

---

## Stack

- Python 3.11+
- Playwright (headless Chrome scraping)
- Anthropic Claude API (claude-sonnet-4-6)
- Rich (terminal output)
