# Over Allowance Fix

Automates detection and correction of **Overallowance** account mismatches in IntelliDealer.  
The job snapshots current issues into a staging table, auto‑fixes eligible records (Pending/Released), and emails clean HTML summaries (with status coloring) to the right settlement/audit contacts via Microsoft Graph.

---

## Why this exists

In IntelliDealer, Overallowance (OA) can be posted to the wrong GL account depending on unit type and sale account. This tool:

- Finds trades where **current OA account** ≠ the **expected** OA account
- **Auto‑corrects** non‑invoiced (Pending/Released) lines directly in `CGIIND`
- **Surfaces Invoiced** exceptions for journal intervention
- Emails **per-person** error lists plus a **global invoiced** summary

---

## How it works (pipeline)

1. **Snapshot** — `sql/removeOldIssues.sql` truncates `DMOVRACCF` (staging).  
2. **Rebuild** — `sql/insertNewIssues.sql` repopulates `DMOVRACCF` with *current* issues.
3. **Auto‑fix** — `sql/fixIssues.sql` writes corrected OA accounts back to `CGIIND` for **Pending/Released**.
4. **Recipients** — `sql/errorLog.sql` maps Branch/Salesperson to **Settlement Auditor Name and Email**.
5. **Render & send** — Python builds small per‑recipient DataFrames, renders colored HTML tables, and **emails** through Microsoft Graph.
6. **Housekeeping** — logs rotate in `logs/`.

---

## Repository layout

```
OVER ALLOWANCE FIX/
├─ config/
│  └─ htmlSettings.json          # Columns, status colors, status order, default CCs
├─ functions/
│  ├─ evaluationFunctions.py     # Build recipient list & per-person error slices
│  ├─ graphFunctions.py          # Microsoft Graph email (client credentials)
│  ├─ intelliDealerFunctions.py  # ODBC connection + SQL execution helpers
│  ├─ maintenanceFunctions.py    # Log cleanup & misc utilities
│  └─ renderingFunctions.py      # HTML table + status coloring/sort
├─ logs/                         # Timestamped job logs (rotated)
├─ sql/
│  ├─ errorLog.sql               # Join DMOVRACCF to per-recipient Name/Email
│  ├─ fixIssues.sql              # Update CGIIND for Pending/Released
│  ├─ insertNewIssues.sql        # Populate DMOVRACCF with current issues
│  ├─ rebuildIssuesTable.sql     # (optional) helper if structure needs rebuild
│  └─ removeOldIssues.sql        # Truncate DMOVRACCF (fresh snapshot each run)
├─ .gitignore
└─ main.py
```

> Tip: include an empty `functions/__init__.py` if packaging/imports require it in your environment.

---

## Prerequisites

- **Python 3.10+**
- **Packages**
  ```bash
  pip install pandas pyodbc requests
  ```
- **IBM i ODBC driver** (Access Client Solutions). Ensure the ODBC driver is installed (64‑bit if using 64‑bit Python) and accessible to `pyodbc`.
- **Microsoft Graph** Azure AD app (client‑credentials flow) with **Application** permission:
  - `Mail.Send` (Application)
  - Admin consent granted
  - A mailbox UPN you can send as (`GRAPH_SENDER_UPN`)

> ⚠️ This job updates production data (`CGIIND`). Test in non‑prod first.

---

## Configuration

All runtime configuration is provided via environment variables and a small JSON file for HTML formatting.

### IntelliDealer (ODBC)

Set these variables in your runtime environment (scheduler, service, or shell):

- `ID_SERVER` — Host/IP of the IBM i / DB2 system  
- `ID_DATABASE` — Database/library (e.g., company library)  
- `ID_USER` — Service account  
- `ID_PASSWORD` — Password

### Microsoft Graph (email)

- `GRAPH_TENANT_ID` — Azure AD tenant ID  
- `GRAPH_CLIENT_ID` — App registration client ID  
- `GRAPH_CLIENT_SECRET` — Client secret  
- `GRAPH_SENDER_UPN` — Mailbox UPN to send “from” (e.g., `noreply@hurontractor.com`)

### HTML / rendering

`config/htmlSettings.json` controls:

```jsonc
{
  "wanted_columns": ["STATUS","INVOICE","TRADE_KEY","BRANCH","SALESPERSON","CURRENT_OVER_ACC","CORRECT_OVER_ACC","COMMENTS"],
  "status_order":   ["Invoiced","Released","Pending"],
  "status_colors":  {
    "Invoiced": "#ffe8e8",
    "Released": "#fff6d6",
    "Pending":  "#e9f6ff"
  },
  "cc": ["settlements@hurontractor.com"]
}
```

---

## Running locally

From the repository root:

```bash
python main.py
```

What happens per run:

1. Load settings & connect to DB.
2. `TRUNCATE DMOVRACCF` → rebuild current issues (`insertNewIssues.sql`).
3. Apply **auto‑fix** for Pending/Released (`fixIssues.sql`).
4. Build per‑recipient tables and **email** HTML summaries.
5. Optionally send a **global “Invoiced”** summary to settlement/audit.
6. Write a log to `logs/OverAllowAccFix_YYYY-MM-DD_HH-MM-SS.log` and prune older logs.

### Scheduling

**Windows Task Scheduler** (example):
- Program/script: `python`
- Arguments: `C:\path\to\repo\main.py`
- Start in: `C:\path\to\repo`

**cron** (example):
```
0 6 * * 1-6 /usr/bin/python3 /opt/overallowance/main.py >> /opt/overallowance/cron.log 2>&1
```

---

## Notes on the data flow

- The truncate‑and‑rebuild approach guarantees a clean snapshot and avoids duplicates in `DMOVRACCF`.
- **Invoiced** rows are **not** auto‑fixed. They are emailed for journal action.
- Email tables are sorted by **status priority** (from `status_order`) and then by **Invoice**.

---

## Troubleshooting

- **ODBC connection/driver errors**
  - Verify IBM i ODBC driver installation and bitness (Python & driver must match).
  - Recheck `ID_*` variables and network access to the host.
- **Graph 401/403/insufficient privileges**
  - Confirm `GRAPH_*` values, `Mail.Send` (Application) permission, and admin consent.
  - Ensure the sender UPN is allowed for application‑send.
- **No emails / empty tables**
  - Validate the `insertNewIssues.sql` logic for current conditions.
  - Ensure `errorLog.sql` maps to real recipients (Name/Email).
- **Wrong columns/order or colors**
  - Update `config/htmlSettings.json` → `wanted_columns`, `status_order`, `status_colors`.

---

## Development tips

- Consider a `--noop` (dry‑run) flag to skip DB updates and email sends while writing HTML files locally.
- Add small unit tests for:
  - Recipient extraction & per‑user slicing
  - Sort order for email tables
  - Status counting in headers

---

## Security

- Secrets are **only** read from environment variables. Never commit credentials or `.env` files.
- Restrict the Graph app to the minimum scope and monitor mail‑send usage.

---

## License / Ownership

Internal Huron Tractor utility. Not for external distribution.
