# AI HOT Integration

The project now uses AI HOT public endpoints as its content source.

It generates two independent page types:

- `daily`: the curated AI HOT daily digest
- `all`: the full AI HOT activity page

Because each mode writes a different title, slug, and Markdown filename, Notion and the site will treat them as two separate pages.

## Endpoints

Default daily mode tries:

- `GET /api/public/daily/{date}`
- fallback: `GET /api/public/daily?date=YYYY-MM-DD`
- fallback: `GET /api/public/daily`

Dynamic feed modes use:

- `GET /api/public/items?mode=selected`
- `GET /api/public/items?mode=all`

## Environment Variables

All AI HOT variables are optional and do not require any token:

- `AIHOT_SOURCE_MODE`
  One of `daily`, `selected`, `all`. Default: `daily`
- `AIHOT_TIMEZONE`
  Default: `Asia/Shanghai`
- `AIHOT_LOOKBACK_DAYS`
  Used by `selected` and `all`. Default: `3`
- `AIHOT_MAX_ITEMS`
  Max number of items written into the page. Default: `12`
- `AIHOT_BASE_URL`
  Default: `https://aihot.virxact.com`
- `AIHOT_USER_AGENT`
  Optional custom user agent

## Local Usage

Generate the curated daily digest:

```powershell
$env:AIHOT_SOURCE_MODE="daily"
python .\sources\daily_paper.py
```

Generate a selected rolling feed:

```powershell
$env:AIHOT_SOURCE_MODE="selected"
$env:AIHOT_LOOKBACK_DAYS="3"
python .\sources\daily_paper.py
```

Generate the full activity page:

```powershell
$env:AIHOT_SOURCE_MODE="all"
$env:AIHOT_LOOKBACK_DAYS="1"
$env:AIHOT_MAX_ITEMS="20"
python .\sources\daily_paper.py
```

## GitHub Actions

The repository now has two separate scheduled workflows:

- `AI HOT Daily Sync`
  Runs every day at `UTC 01:00`, which is `09:00` China Standard Time
- `AI HOT All Sync`
  Runs every day at `UTC 01:30`, which is `09:30` China Standard Time

This makes the site naturally publish two different pages:

- one daily digest page
- one full activity page

## CI

`validate-pipeline.yml` sets `AIHOT_OFFLINE_MODE=1` so validation can run without depending on the external AI HOT service.
