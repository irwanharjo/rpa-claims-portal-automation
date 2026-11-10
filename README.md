# Claims Portal RPA Automation

A desktop RPA tool (Python + Tkinter + Selenium) that automates submitting outpatient/medical claim reimbursements into a corporate web claims portal, driven from a batch of Excel spreadsheets.

Built for a real production use case (processing dozens of claims per run across multiple client entities) and simplified/genericized here for portfolio purposes — entity names, portal URL, and credentials have been replaced with placeholders.

## What it does

- Watches a `Siap_Input/` folder for pairs of Excel spreadsheets + supporting PDF invoices
- Parses the spreadsheet to detect the header row, patient/claim columns, and totals, regardless of minor formatting differences between files
- Infers the client entity and claim category from free-text codes found in the spreadsheet
- Logs into the claims portal and drives the multi-step claim submission form: entity/category selection, invoice number, invoice date (extracted from the PDF via `pdfplumber`, with a manual-override dialog when extraction is ambiguous), document type tagging, and PDF upload
- Cross-checks each row's total in Excel against the amount shown on the portal before checking it off, and reports any rows it couldn't confidently match for manual review
- Archives processed files to `Selesai_Input/` once a batch is confirmed

## Setup

```bash
pip install -r requirements.txt
copy .env.example .env   # then fill in your own portal URL + credentials
```

Update `ENTITY_CODE_MAP` and `PISA_CATEGORY_CODES` in `robot_aps.py` to match your own portal's entity/category structure — the values here are illustrative placeholders.

## Run

```bash
python robot_aps.py
```

## Stack

Python · Selenium · pandas · pdfplumber · Tkinter

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for what changed after the first public version (production hardening notes).
