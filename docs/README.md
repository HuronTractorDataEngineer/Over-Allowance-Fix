# Alert System

A small, scheduled Python job that detects recent **unit changes** in IntelliDealer, evaluates who should be notified (by role and branch) using rules in the Data Warehouse, renders an HTML summary table, and sends email via Microsoft Graph.

The job is designed to run on **Windows Server 2019** under **Task Scheduler**. It can also be run manually.

---

## Table of contents
- [Overview](#overview)
- [Data flow](#data-flow)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
  - [Environment variables](#environment-variables)
  - [HTML table settings (`config/htmlSettings.json`)](#html-table-settings-confightmlsettingsjson)
- [Running locally](#running-locally)
- [Windows Task Scheduler](#windows-task-scheduler)
- [Logs & maintenance](#logs--maintenance)
- [Troubleshooting](#troubleshooting)
- [Extending the system](#extending-the-system)

---

## Overview
- **Source**: IntelliDealer change log (DB2/IBM i) queried with a parameterized SQL script (see `config/ChangeLog.sql`).
- **Recipients**: Pulled from the Data Warehouse tables (e.g., `AlertUsers`, `AlertMatrix`). Additional salespeople/purchasers found in the change log can be included automatically.
- **Evaluation**: Role + branch rules determine who receives which rows. Rules support simple equality, `IN` / `NOT IN`, and optional *from → to* status change conditions.
- **Output**: A responsive(ish) HTML table with status coloring, ordered columns, currency formatting, and an optional call‑to‑action link to a Fabric/Power BI report.
- **Delivery**: Microsoft Graph `sendMail` using application permissions (client credentials).

> **Entry point:** `UnitChangeDistributor.py`

---

## Data flow
1. **Window selection** – the job computes a *look‑back window* based on the current run time (weekday mornings cover the weekend; late‑afternoon runs use a shorter window).  
2. **Load settings** – `config/htmlSettings.json` provides which columns to show, sort/order behavior, and color mapping for statuses.
3. **Fetch data**  
   - **IntelliDealer (DB2/i)**: Execute `config/ChangeLog.sql` with the computed time parameters and load the results into a DataFrame.  
   - **Data Warehouse (SQL Server)**: Read recipient lists and rule matrices into DataFrames.
4. **Evaluate rules** – For each user, filter by branch and apply the role’s rule rows to build their personal change list. Salesperson/purchaser email addresses found in the data can be appended as recipients.
5. **Render email** – Convert the user’s rows to HTML with status coloring and right‑aligned currency, and add the optional **“Click here for past changes”** button.
6. **Send** – Use Microsoft Graph to send the email on behalf of the configured sender.

---

## Repository layout
```
ALERT SYSTEM/
├─ config/
│  ├─ ChangeLog.sql              # Parameterized SQL for IntelliDealer change feed
│  └─ htmlSettings.json          # Columns, order, colors, CTA link
├─ functions/
│  ├─ evaluationFunctions.py     # Rule parsing & per‑user list builders
│  ├─ graphFunctions.py          # Graph token + sendMail (no MSAL dependency)
│  ├─ intelliDealerFunctions.py  # DB2 connection, config & time window logic
│  ├─ maintenanceFunctions.py    # Log pruning, folder housekeeping
│  ├─ renderingFunctions.py      # Table sorting + HTML rendering
│  └─ warehouseFunctions.py      # SQL Server connection + table readers
├─ logs/                         # Rotating run logs (created at runtime)
├─ UnitChangeDistributor.py      # Orchestrator / main script
└─ docs/                         # (Optional) requirements, notes
```

---

## Prerequisites
- **Windows Server 2019** (or Windows 10/11 for local dev)
- **Python 3.12** (64‑bit)
- **ODBC drivers**
  - IBM i Access ODBC Driver (for DB2 / IntelliDealer)
  - Microsoft ODBC Driver for SQL Server (e.g., ODBC Driver 17 or newer)
- **Network egress** to Microsoft Graph
  - `https://login.microsoftonline.com/` (token)
  - `https://graph.microsoft.com/` (sendMail)
- **Microsoft Entra app registration** with *Application* permission **Mail.Send** (admin‑consented). A client secret is required.

Optional (for development): create and activate a virtual environment, then install packages listed in `docs/requirements.txt`.

---

## Configuration
All secrets and connection info are supplied via **environment variables** so the script can run headless under Task Scheduler. The HTML rendering options live in `config/htmlSettings.json`.

### Environment variables
**IntelliDealer (DB2/IBM i)**
- `ID_SERVER` – Host or DSN of the IBM i / DB2 server
- `ID_DATABASE` – Database / library if applicable
- `ID_USER` – Service user ID
- `ID_PASSWORD` – Service user password

**Data Warehouse (SQL Server)**
- `DW_SERVER` – SQL Server hostname
- `DW_DATABASE` – Database name
- `DW_USER` – SQL login
- `DW_PASSWORD` – SQL password

**Microsoft Graph (email)**
- `GRAPH_TENANT_ID` – Directory (tenant) ID
- `GRAPH_CLIENT_ID` – App registration’s client ID
- `GRAPH_CLIENT_SECRET` – App client secret
- `GRAPH_SENDER_UPN` – UPN of the mailbox to send from (e.g., `alerts@yourdomain.com`)

> Set these at the **system** level (or for the run‑as service account) so Task Scheduler can read them.

**Example (PowerShell, run as Administrator):**
```powershell
[Environment]::SetEnvironmentVariable('DW_SERVER','sql01','Machine')
[Environment]::SetEnvironmentVariable('DW_DATABASE','Warehouse','Machine')
# ...repeat for all vars...
```

### HTML table settings (`config/htmlSettings.json`)
```jsonc
{
  "wanted_columns": [ "USER_ID", "EVENT_TS", "STOCK_NUMBER", ... ],
  "statuses_order": [ "Available", "Rental", "Sold", ... ],
  "status_colors": {
    "Available":   "#D5F5E3",
    "Shop":        "#FADBD8",
    "Transfered":  "#A3E4D7",
    "Transferred": "#A3E4D7"
  },
  "report": {
    "url":   "https://app.fabric.microsoft.com/Redirect?...",
    "label": "Click here for past changes"
  }
}
```

- **wanted_columns** – Ordered list of columns to display in the email table
- **statuses_order** – Determines sorting precedence (left as‑is if missing)
- **status_colors** – Background color per status (case/space/underscore agnostic)
- **report** – Optional CTA button URL + label appended under the email header

> You can safely add new statuses or change colors here without code changes.

---

## Running locally
```bash
# From the project root
python UnitChangeDistributor.py
```
The script will:
1) compute the time window, 2) read configuration, 3) pull data, 4) evaluate recipients, 5) render HTML, 6) send emails, and 7) prune old log files.

---

## Windows Task Scheduler
**Action**
- **Program/script**: `C:\Program Files\Python312\python.exe`
- **Add arguments**: `"C:\Users\jkourtesis\projects\Alert System\UnitChangeDistributor.py"`
- **Start in**: `C:\Users\jkourtesis\projects\Alert System`

**Recommended triggers**
- Weekdays at **09:00** and **16:30** (aligns with the job’s look‑back logic)

**General**
- Run whether user is logged on or not
- Use a service account that has ODBC access and the environment variables defined

---

## Logs & maintenance
- Logs are written to the `logs/` directory with timestamped filenames.  
- On each run, the job **keeps the newest 10** logs and deletes older ones.  
- Ensure the `logs/` folder is writable by the scheduled task’s run‑as account.

---

## Troubleshooting
**Nothing is sent**
- Verify environment variables are present in the Task Scheduler context.
- Confirm ODBC drivers are installed and DSNs/hosts are reachable.
- Check the latest file in `logs/` for stack traces and SQL errors.

**Graph errors (401/403/429)**
- Ensure the app registration has **Mail.Send (Application)** and admin consent.
- Confirm `GRAPH_SENDER_UPN` refers to a valid mailbox that can send.
- For 429 (rate‑limit), space out runs or reduce per‑minute email volume.

**DB2/SQL connectivity**
- Test with `isql`/`odbcad32` or Python snippets to confirm the driver names and connection strings.

**HTML table looks wrong**
- Ensure column names in `wanted_columns` exist in the data set.
- Update `status_colors` if new statuses appear.

---

## Extending the system
- **Add recipients/roles**: Update Warehouse tables (`AlertUsers`, `AlertMatrix`). New roles can be added with rule rows—no code change needed.
- **Include/exclude columns**: Edit `wanted_columns` and re‑order as desired.
- **Color/ordering**: Adjust `status_colors` and `statuses_order`.
- **Alternate schedules**: Change Task Scheduler triggers. If you adjust run times significantly, revisit the look‑back logic in `intelliDealerFunctions.py`.

---

> **Note**: This project intentionally keeps *all secrets* out of the repo. Rotate the Graph client secret periodically and limit access to the run‑as account.

