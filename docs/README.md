# Unit Change Alert System

A small Python pipeline that extracts unit change events from IntelliDealer and the IDDATA warehouse, evaluates user/branch rules, renders an HTML table, and emails personalized alerts via Microsoft Graph.

> Folder name in VS Code: **ALERT SYSTEM**

---

## Quick start

1. **Python**
   - Use Python 3.10+
   - (Windows) Ensure ODBC drivers are installed: *IBM i Access* (for AS/400 / DB2) and *Microsoft ODBC Driver for SQL Server*.
2. **Install dependencies**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # on Windows (or `source .venv/bin/activate` on macOS/Linux)
   pip install -r docs/requirements.txt
   ```
3. **Configure connections**
   - Copy your `connectionSettings.ini` into `config files/` (see sample below).
   - Adjust `config files/htmlTableSettings.json` to control columns, status colors, and status priority.
4. **Run**
   ```bash
   python UnitChangeDistributor.py
   ```
   - Logs are written to `logs/UnitChangeProcess_*.log`.
   - Old log files are automatically pruned.

---

## Repository layout (relevant parts)

```
ALERT SYSTEM/
├─ config files/
│  └─ connectionSettings.ini
├─ docs/
│  ├─ README.md  ← you are here
│  └─ requirements.txt
├─ functions/
│  ├─ intelliDealerFunctions.py   # read DB2/IntelliDealer & SQL templating
│  ├─ warehouseFunctions.py       # read SQL Server (IDDATA)
│  ├─ evaluationFunctions.py      # apply AlertMatrix rules per user/role
│  ├─ renderingFunctions.py       # load htmlTableSettings & render HTML email
│  ├─ graphFunctions.py           # send email via Microsoft Graph
│  └─ maintenanceFunctions.py     # simple file rotation helper
├─ sqlScripts/
│  └─ ChangeLog.sql               # primary query for change events
├─ UnitChangeDistributor.py       # orchestrator (main entrypoint)
└─ logs/                          # runtime logs
```

## Configuration

Place `connectionSettings.ini` under `config files/`.

### HTML table settings

`htmlTableSettings.json` controls:
- **wanted_columns**: the column order shown in email
- **status_order**: highest priority first (used for sorting)
- **status_colors**: background color per status

---

## How it works (high level)

1. **Load config** from `connectionSettings.ini`.
2. **Query data**  
   - `ChangeLog.sql` against IntelliDealer (DB2/iSeries).  
   - Supplemental lookups from the IDDATA SQL Server (if configured).
3. **Evaluate rules** with `evaluationFunctions.compile_change_list_for_user(...)` using an **AlertMatrix** style of branch/role filters.
4. **Render HTML** using `renderingFunctions` and the `htmlTableSettings.json` preferences.
5. **Send email** per user via **Microsoft Graph** (application permissions).
6. **Rotate logs** using `maintenanceFunctions.remove_old_files(...)`.

---

## Scheduling

You can automate the script with Windows Task Scheduler or a cron job. Recommended schedule: weekdays at 6–7am local time.

- **Windows Task Scheduler** (example action):  
  `Program/script`: `C:\path\to\python.exe`  
  `Arguments`: `C:\path\to\ALERT SYSTEM\UnitChangeDistributor.py`  
  `Start in`: `C:\path\to\ALERT SYSTEM`
- **Cron** (Linux):  
  `0 6 * * 1-5 /usr/bin/python3 /opt/alert-system/UnitChangeDistributor.py >> /opt/alert-system/logs/cron.log 2>&1`

---

## Security

- Keep `connectionSettings.ini` and secrets outside of version control.
- Use machine-level secrets (Task Scheduler “Run whether user is logged on or not”) or environment variables for deployment.
- Restrict access to the service account used for Graph email.

---

## License / Ownership

Internal Huron Tractor tooling. Do not distribute outside the organization without approval.

---

_Last updated: 2025-08-18_
