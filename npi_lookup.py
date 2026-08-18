#!/usr/bin/env python3
"""
NPI Lookup — Read NPIs from lead scraper CSV, fetch full details from CMS NPPES API,
and save to CSV.

Usage:
    python npi_lookup.py                    # Interactive — asks for input CSV
    python npi_lookup.py input.csv          # Pass input CSV as argument
"""

import csv
import json
import os
import sys
import time
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


CMS_API_BASE = "https://npiregistry.cms.hhs.gov/api/"
API_VERSION = "2.1"

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

CSV_HEADERS = [
    "NPI",
    "Entity Type",
    "Status",
    "First Name",
    "Middle Name",
    "Last Name",
    "Name Prefix",
    "Name Suffix",
    "Credential",
    "Sex",
    "Enumeration Date",
    "Last Updated",
    "Sole Proprietor",
    "Practice Address 1",
    "Practice Address 2",
    "Practice City",
    "Practice State",
    "Practice ZIP",
    "Practice Country",
    "Practice Phone",
    "Practice Fax",
    "Mailing Address 1",
    "Mailing Address 2",
    "Mailing City",
    "Mailing State",
    "Mailing ZIP",
    "Mailing Country",
    "Mailing Phone",
    "Mailing Fax",
    "Primary Taxonomy Code",
    "Primary Taxonomy Description",
    "Primary Taxonomy State",
    "Primary Taxonomy License",
    "Other Taxonomy Codes",
    "Other Taxonomy Descriptions",
    "Other Identifiers",
    "Endpoint Count",
]


def find_npi_column(headers):
    """Find the column index containing NPI numbers."""
    candidates = ["npi", "npi_number", "npinumber", "npi number", "np_i_number"]
    headers_lower = [h.strip().lower() for h in headers]
    for candidate in candidates:
        for i, h in enumerate(headers_lower):
            if candidate in h:
                return i
    return None


def read_npis_from_csv(filepath):
    """Read NPI numbers from a CSV file."""
    npis = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if not headers:
            print("Error: CSV file is empty.")
            return []

        npi_col = find_npi_column(headers)
        if npi_col is None:
            print(f"Error: Could not find NPI column in CSV.")
            print(f"Columns found: {headers}")
            return []

        print(f"Found NPI column: '{headers[npi_col].strip()}' (column {npi_col + 1})")

        for row in reader:
            if npi_col < len(row):
                npi = row[npi_col].strip().replace("-", "")
                if npi and len(npi) == 10 and npi.isdigit():
                    npis.append(npi)

    return npis


def query_npi_api(npi_number):
    """Query CMS NPPES API for a single NPI."""
    url = f"{CMS_API_BASE}?version={API_VERSION}&number={npi_number}"
    req = Request(url, headers={"User-Agent": "NPI-Lookup-Tool/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("result_count", 0) > 0:
                return data["results"][0]
            return None
    except HTTPError as e:
        if e.code == 429:
            print(f"  Rate limited. Waiting 5 seconds...")
            time.sleep(5)
            return query_npi_api(npi_number)
        print(f"  HTTP Error {e.code} for NPI {npi_number}")
        return None
    except URLError as e:
        print(f"  Network error for NPI {npi_number}: {e.reason}")
        return None
    except Exception as e:
        print(f"  Error for NPI {npi_number}: {e}")
        return None


def flatten_result(r):
    """Flatten a CMS API result into a single CSV row."""
    basic = r.get("basic", {})
    addrs = r.get("addresses", [])
    taxonomies = r.get("taxonomies", [])
    identifiers = r.get("identifiers", [])
    endpoints = r.get("endpoints", [])

    practice = {}
    mailing = {}
    for a in addrs:
        if a.get("address_purpose") == "LOCATION":
            practice = a
        elif a.get("address_purpose") == "MAILING":
            mailing = a

    if not practice and addrs:
        practice = addrs[0]
    if not mailing and len(addrs) > 1:
        mailing = addrs[1]

    primary_tax = {}
    other_taxes = []
    for t in taxonomies:
        if t.get("primary"):
            primary_tax = t
        else:
            other_taxes.append(t)

    other_tax_descs = "; ".join(
        f"{t.get('code', '')} ({t.get('desc', '')})" for t in other_taxes
    )

    other_ids = "; ".join(
        f"{i.get('desc', '')}: {i.get('identifier', '')} ({i.get('state', '')})"
        for i in identifiers
    )

    entity_type = r.get("enumeration_type", "")
    if entity_type == "NPI-1":
        entity_label = "Individual"
    elif entity_type == "NPI-2":
        entity_label = "Organization"
    else:
        entity_label = entity_type

    return [
        r.get("number", ""),
        entity_label,
        basic.get("status", ""),
        basic.get("first_name", ""),
        basic.get("middle_name", ""),
        basic.get("last_name", ""),
        basic.get("name_prefix", ""),
        basic.get("name_suffix", ""),
        basic.get("credential", ""),
        basic.get("sex", ""),
        basic.get("enumeration_date", ""),
        basic.get("last_updated", ""),
        basic.get("sole_proprietor", ""),
        practice.get("address_1", ""),
        practice.get("address_2", ""),
        practice.get("city", ""),
        practice.get("state", ""),
        practice.get("postal_code", ""),
        practice.get("country_name", ""),
        practice.get("telephone_number", ""),
        practice.get("fax_number", ""),
        mailing.get("address_1", ""),
        mailing.get("address_2", ""),
        mailing.get("city", ""),
        mailing.get("state", ""),
        mailing.get("postal_code", ""),
        mailing.get("country_name", ""),
        mailing.get("telephone_number", ""),
        mailing.get("fax_number", ""),
        primary_tax.get("code", ""),
        primary_tax.get("desc", ""),
        primary_tax.get("state", ""),
        primary_tax.get("license", ""),
        other_tax_descs,
        other_ids,
        len(endpoints),
    ]


def main():
    print("=" * 60)
    print("NPI LOOKUP — Fetch Provider Details from CMS NPPES")
    print("=" * 60)

    npis = []

    if len(sys.argv) > 1:
        input_csv = sys.argv[1]
        print(f"\nReading NPIs from: {input_csv}")
        npis = read_npis_from_csv(input_csv)
    else:
        print("\nWhere are your NPI numbers?")
        print("  1. From lead_scraper output CSV")
        print("  2. From npiscan_scraper output CSV")
        print("  3. From any CSV with an NPI column")
        print("  4. Enter NPIs manually")
        choice = input("\nChoice (1-4): ").strip()

        if choice == "4":
            manual_input = input("Enter NPI numbers separated by commas: ").strip()
            npis = [n.strip().replace("-", "") for n in manual_input.split(",") if n.strip()]
            input_csv = None
        else:
            if choice == "1":
                input_csv = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..", "lead_scraper", "output"
                )
            elif choice == "2":
                input_csv = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..", "npiscan_scraper", "output"
                )
            else:
                input_csv = input("Enter path to CSV file: ").strip()

            if os.path.isdir(input_csv):
                csv_files = [f for f in os.listdir(input_csv) if f.endswith(".csv")]
                if not csv_files:
                    print(f"No CSV files found in {input_csv}")
                    return
                if len(csv_files) == 1:
                    input_csv = os.path.join(input_csv, csv_files[0])
                else:
                    print(f"\nCSV files found in {input_csv}:")
                    for i, f in enumerate(csv_files, 1):
                        print(f"  {i}. {f}")
                    pick = input(f"Pick (1-{len(csv_files)}): ").strip()
                    try:
                        input_csv = os.path.join(input_csv, csv_files[int(pick) - 1])
                    except (ValueError, IndexError):
                        print("Invalid choice.")
                        return

            print(f"\nReading NPIs from: {input_csv}")
            npis = read_npis_from_csv(input_csv)

    if not npis:
        print("No valid NPI numbers found.")
        return

    npis = list(dict.fromkeys(npis))
    print(f"\nFound {len(npis)} unique NPI(s) to look up.")

    today = datetime.now().strftime("%Y-%m-%d")
    output_csv = os.path.join(OUTPUT_DIR, f"npi_details_{today}.csv")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Output will be saved to: {output_csv}")
    print(f"\nQuerying CMS NPPES API...")
    print("-" * 60)

    found = 0
    not_found = 0
    errors = 0

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)

        for i, npi in enumerate(npis, 1):
            print(f"[{i}/{len(npis)}] Looking up NPI: {npi}...", end=" ", flush=True)
            result = query_npi_api(npi)
            if result:
                row = flatten_result(result)
                writer.writerow(row)
                name = f"{result.get('basic', {}).get('first_name', '')} {result.get('basic', {}).get('last_name', '')}".strip()
                print(f"Found: {name}")
                found += 1
            else:
                print("Not found")
                not_found += 1

            if i < len(npis):
                time.sleep(0.3)

    print("-" * 60)
    print(f"\nDone!")
    print(f"  Found:     {found}")
    print(f"  Not found: {not_found}")
    print(f"  Output:    {output_csv}")


if __name__ == "__main__":
    main()
