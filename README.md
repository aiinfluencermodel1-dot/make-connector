# Make Connector — NPI Lookup Tool

Reads NPI numbers from your lead scraper or bulk scraper CSV output and fetches full provider details from the **CMS NPPES API** (free, no API key required).

## What It Does

1. Reads NPI numbers from any CSV (lead_scraper, npiscan_scraper, or any CSV with an NPI column)
2. Queries the official CMS NPPES API for each NPI
3. Saves full provider details to a clean CSV

## Output Fields

| Column | Description |
|--------|-------------|
| NPI | 10-digit NPI number |
| Entity Type | Individual or Organization |
| Status | Active / Deactivated |
| First/Middle/Last Name | Provider name |
| Credential | e.g., MD, DO, PA |
| Sex | M / F |
| Enumeration Date | When NPI was assigned |
| Last Updated | Last NPPES update |
| Practice Address | Full practice location |
| Practice Phone/Fax | Contact numbers |
| Mailing Address | Full mailing address |
| Mailing Phone/Fax | Mailing contact |
| Primary Taxonomy | Code + description |
| Other Taxonomies | All additional specialties |
| Other Identifiers | State Medicare IDs, etc. |

## Installation

```bash
cd make_connector
python3 -m venv venv
source venv/bin/activate
```

No pip install needed — uses only Python standard library.

## Usage

```bash
python npi_lookup.py
```

The script will ask you:
1. **Where are your NPI numbers?** — Choose from lead_scraper, npiscan_scraper, any CSV, or manual entry
2. **Which CSV file?** — If multiple files exist, it will list them for you

Or pass a CSV directly:
```bash
python npi_lookup.py path/to/leads.csv
```

### Output

Results are saved to `output/npi_details_YYYY-MM-DD.csv`.

## Data Source

- **CMS NPPES API** — https://npiregistry.cms.hhs.gov/api/
- Free, no API key required
- Official U.S. government healthcare provider data
- Rate limit: ~45 requests/second (be polite, we add 0.3s delay)

## How It Fits

```
lead_scraper/npiscan_scraper.py
        │
        ▼
  output/npiscan_leads_YYYY-MM-DD.csv
        │  (contains NPI numbers)
        ▼
make_connector/npi_lookup.py
        │
        ▼
  output/npi_details_YYYY-MM-DD.csv
        │  (full provider details: phone, address, taxonomy, etc.)
        ▼
  Ready to use for outreach / CRM / billing
```
