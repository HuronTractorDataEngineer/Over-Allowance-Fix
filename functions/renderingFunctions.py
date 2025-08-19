import datetime
from typing import Optional
import pandas as pd
import html as _html
import json
from pathlib import Path

# ------------------------------------------------------------
# HTML Table Config Loading
# ------------------------------------------------------------
def _norm_status(s: str) -> str:
    """
    Normalize a status string for case/spacing/underscore-insensitive lookups.

    Transforms:
    - strips leading/trailing whitespace
    - lowercases
    - replaces '_' with '-'
    - replaces double spaces ('  ') with a single space

    Returns:
        Normalized status key.
    """
    return (
        s.strip().lower()
        .replace('_', '-')
        .replace('  ', ' ')
    )

def load_htmlTable_settings(settings_path: str | Path | None = None):
    """
    Load HTML table rendering settings from JSON.

    If `settings_path` is None, defaults to
    <repo_root>/config/htmlTableSettings.json (relative to this file).

    Returns:
        wanted_columns: List of column names to include (in order).
        status_colors: Mapping of normalized status -> color (e.g., hex).
        status_order: List of normalized statuses in priority order.

    Notes:
        Status keys and order are normalized via `_norm_status` for
        case/spacing/underscore-insensitive lookups.
    """
    if settings_path is None:
        settings_path = Path(__file__).resolve().parents[1] / "config" / "htmlTableSettings.json"

    with open(settings_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    wanted_columns = cfg.get("wanted_columns", [])
    status_order   = [_norm_status(s) for s in cfg.get("status_order", [])]
    status_colors  = {_norm_status(k): v for k, v in cfg.get("status_colors", {}).items()}

    return wanted_columns, status_colors, status_order

# ------------------------------------------------------------
# Email rendering — with STATUS-based sorting & row coloring
# ------------------------------------------------------------

def _normalize_status(val: Optional[str]) -> str:
    """
    Normalize a status value to a lowercase, trimmed string.

    Returns:
        The lowercased, stripped string; '' if the input is None/empty.
    """

    return (str(val or '').strip().lower())

def sort_for_email(_STATUS_RANK, df: pd.DataFrame) -> pd.DataFrame:
    """
    Sort a change list DataFrame for email presentation.

    Order is:
    1) status priority (descending) via `_STATUS_RANK` on normalized STATUS,
    2) EVENT_TS (descending, parsed with `to_datetime(errors='coerce')`),
    3) STOCK_NUMBER (ascending) for tie-break.

    Returns:
        A new DataFrame sorted as above; if STATUS is missing, returns `df` unchanged.
    """

    if 'STATUS' not in df.columns:
        return df
    work = df.copy()
    work['_rank'] = work['STATUS'].map(lambda s: _STATUS_RANK.get(_normalize_status(s), 0))
    if 'EVENT_TS' in work.columns:
        work['_ts'] = pd.to_datetime(work['EVENT_TS'], errors='coerce')
    else:
        work['_ts'] = pd.NaT
    # Sort: STATUS rank desc, then EVENT_TS desc, then STOCK_NUMBER asc for stability
    work = work.sort_values(by=['_rank','_ts','STOCK_NUMBER'], ascending=[False, False, True], kind='mergesort')
    return work.drop(columns=['_rank','_ts'])

def render_html_table(_STATUS_RANK, STATUS_COLORS, df: pd.DataFrame, title: str, subtitle: str = '') -> str:
    """
    Render a status-colored HTML table suitable for email.

    Behavior:
    - Sorts `df` via `sort_for_email` using `_STATUS_RANK` (status priority, then
    EVENT_TS desc, then STOCK_NUMBER asc).
    - Applies row background colors from `STATUS_COLORS` keyed by normalized 'STATUS'.
    - Wraps the table in minimal inline CSS with title, optional subtitle, and a
    generated timestamp.

    Returns:
        str: Complete HTML document as a string.
    """

    # Ensure sorted
    df = sort_for_email(_STATUS_RANK, df)

    # Build HTML table with inline row background colors for maximum email-client compatibility
    headers = list(df.columns)

    def td(val: object) -> str:
        return f"<td>{_html.escape('' if pd.isna(val) else str(val))}</td>"

    rows_html = []
    for _, row in df.iterrows():
        status_key = _normalize_status(row.get('STATUS'))
        bg = STATUS_COLORS.get(status_key, '')
        tr_style = f" style=\"background-color: {bg};\"" if bg else ''
        cells = ''.join(td(row.get(col)) for col in headers)
        rows_html.append(f"<tr{tr_style}>{cells}</tr>")

    thead = '<thead><tr>' + ''.join(f"<th>{_html.escape(col)}</th>" for col in headers) + '</tr></thead>'
    tbody = '<tbody>' + ''.join(rows_html) + '</tbody>'

    style = """
    <style>
      body { font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }
      .container { max-width: 1080px; margin: 0 auto; padding: 12px 16px; }
      h1 { font-size: 18px; margin: 0 0 4px; }
      h2 { font-size: 14px; font-weight: normal; color: #555; margin: 0 0 12px; }
      table { border-collapse: collapse; width: 100%; font-size: 13px; }
      th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }
      th { background: #f4f6f8; }
      .meta { font-size: 12px; color: #666; margin-bottom: 10px; }
    </style>
    """

    table_html = f"<table>{thead}{tbody}</table>"

    html = f"""
    <html>
      <head>{style}</head>
      <body>
        <div class='container'>
          <h1>{_html.escape(title)}</h1>
          <h2>{_html.escape(subtitle)}</h2>
          <div class='meta'>Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
          {table_html}
        </div>
      </body>
    </html>
    """
    return html