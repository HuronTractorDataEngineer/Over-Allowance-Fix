# Over Allowance Fix

Automated job that audits and corrects **Over Allowance** account coding in IntelliDealer, then emails status tables to the appropriate users.  
Runs unattended on **Windows Server 2019** on TO BE DETERMINED

---

## Overview

1. Refreshed a working table in DB2 on IBM i (iSeries) with the latest over‑allowance candidates.
2. Compute the correct over‑allowance account based on mapping rules and transaction state.
3. **Update** IntelliDealer for *Pending* and *Released* records (invoiced records are excluded from updates).
4. Compile personalized tables for each settlement auditor and email them via **Microsoft Graph** (application permissions).
5. Send a separate summary to the designated reviewer for **Invoiced (last 3 days)** items that require journal action.
6. Rotate log files to keep the newest 10 logs.

---

## Repository Layout

```
OVER ALLOWANCE FIX/
├─ config/
│  └─ htmlSettings.json        # Columns, status order/colors, CC list
│  └─ rebuildIssuesTable.sql   # Script to make changes to workin table is needed (Run in ACS)
├─ docs/
│  └─ (optional) README.md     # Project docs (this file can live at root)
├─ functions/
│  ├─ evaluationFunctions.py   # Build user list, per-user filters
│  ├─ graphFunctions.py        # Send email via Microsoft Graph
│  ├─ intelliDealerFunctions.py# DB access, SQL execution helpers
│  ├─ maintenanceFunctions.py  # Keep newest N log files
│  └─ renderingFunctions.py    # HTML table settings & rendering
├─ logs/                       # Log file directory; timestamped log files
├─ sql/
│  ├─ fixScript.sql            # Refresh DMOVRACCF data update CGIIND (non‑invoiced)
│  └─ errorLog.sql             # Pull run reporting data (Join DMOVRACCF to settlement recipients)
├─ .gitignore
└─ main.py                     # Orchestrates the end‑to‑end run
```

> **Note:** The app resolves files by folder name (e.g., `sql/`, `config/`). When running under **Task Scheduler**, set the task’s **Start in** directory to the project root—or use absolute paths.

---

## Prerequisites

- **Python 3.x** on Windows Server 2019
- **IBM i Access ODBC Driver** (“iSeries Access ODBC Driver”) installed
- Network access/credentials to the IntelliDealer DB2 database
- A Microsoft Entra app with **Graph** permissions to send mail as the service account (application permissions)
- Outbound HTTPS allowed to Graph API endpoints

---

## Configuration

### 1) Environment Variables

Set these for the **run account** (the same account used by Task Scheduler). System‑level env vars are recommended.

**IntelliDealer / DB2**
- `ID_SERVER` — IBM i host
- `ID_DATABASE` — Default library / DBQ
- `ID_USER` — User profile
- `ID_PASSWORD` — Password

**Microsoft Graph (application creds)**
- `GRAPH_TENANT_ID`
- `GRAPH_CLIENT_ID`
- `GRAPH_CLIENT_SECRET`
- `GRAPH_SENDER_UPN` — UPN of the mailbox to send from

### 2) HTML/Email Settings (`config/htmlSettings.json`)

Controls the email table:
- `wanted_columns` — column subset & order
- `status_order` — render/sort order (first = highest priority)
- `status_colors` — background color per status
- `cc` — additional recipients for all emails

A sample is already included.

---

## Installation

```bat
:: From an elevated PowerShell or CMD
cd C:\path	o\OverAllowanceFix

:: (Optional) Create and activate a virtual environment
python -m venv .venv
call .venv\Scriptsctivate.bat

:: Install dependencies
pip install -r requirements.txt
```

> Ensure the IBM i Access ODBC Driver is installed on the server before running.

---

## Running Locally

```bat
cd C:\path	o\OverAllowanceFix
call .venv\Scriptsctivate.bat
python main.py
```

Logs are written to `.\logs\OverAllowAccFix_YYYY-MM-DD_HH-MM-SS.log`

---

## Windows Task Scheduler

Create a scheduled task that runs **Mon–Fri** at **TO BE DETERMINED**.

**Action (recommended `.cmd` wrapper):**

```bat
@echo off
setlocal
cd /d C:\path	o\OverAllowanceFix

:: If you prefer not to use system env vars, you can set them here:
:: set ID_SERVER=your-host
:: set ID_DATABASE=YOURLIB
:: set ID_USER=userid
:: set ID_PASSWORD=********
:: set GRAPH_TENANT_ID=...
:: set GRAPH_CLIENT_ID=...
:: set GRAPH_CLIENT_SECRET=...
:: set GRAPH_SENDER_UPN=service@yourdomain.com

call .venv\Scriptsctivate.bat
python main.py
```

**Settings:**
- Run whether user is logged on or not
- Use the same account that owns the environment variables
- Start in: `C:\path	o\OverAllowanceFix`
- If the task is still running, **Do not start a new instance** (prevents overlap)
- (Optional) Stop the task if it runs longer than 30 minutes

---

## How It Works (Data & SQL)

- `sql/fixScript.sql`
  - Truncates and repopulates `DMOVRACCF` from live data and mapping rules.
  - Derives **Correct_Over_Acc** and **Status** and marks items requiring action.
  - **Updates** `CGIIND` only for **Pending/Released**, never for *Invoiced*.
  - Includes **Invoiced (last 3 days)** for review emails.
- `sql/errorLog.sql`
  - Joins `DMOVRACCF` to a small mapping of settlement recipients to attach **Name** and **Email**.

The Python entrypoint (`main.py`) orchestrates:
1. Build/refresh data via ODBC.
2. Compile per‑user slices and render HTML tables.
3. Send emails using Microsoft Graph.
4. Rotate logs (keep newest 10).

---

## Logging & Maintenance

- Log files are timestamped per run in `.\logs\`.
- `remove_old_files(directory, keep_count)` keeps only the newest **10** logs (configurable in `main.py`).

---

## Troubleshooting

- **ODBC Driver not found**: Verify IBM i Access ODBC Driver is installed and the driver name is exactly `"iSeries Access ODBC Driver"`.
- **Connection errors**: Confirm `ID_*` env vars and network access to the IBM i host.
- **Graph errors**: Ensure the four `GRAPH_*` env vars are set and the app has permission to send as the service account. Check service principal assignment and consent.
- **No emails received**: Validate `GRAPH_SENDER_UPN`, recipient addresses, and spam/quarantine rules.
- **Empty tables**: Confirm the SQL scripts in `sql/` are present and that the run account has privileges to read/write the referenced libraries/tables.

---

## Development Notes

- Keep import side effects minimal; do work inside functions (e.g., `main()`), not at import time.
- Use absolute or project‑root‑relative paths when running under Task Scheduler.
- Consider a simple single‑instance lock if you expect long runs near the 16:30 trigger.

---

## License

Internal use at Huron Tractor.
