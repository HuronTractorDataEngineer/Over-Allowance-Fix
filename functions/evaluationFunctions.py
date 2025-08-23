import logging
from typing import Optional, Set
import pandas as pd

# ------------------------------------------------------------
# Helper functions — AlertMatrix rule evaluation
# ------------------------------------------------------------

def _tokenize_csv_field(val: Optional[str]) -> Set[str]:
    """
    Normalize a comma-separated string into a set of uppercase tokens.
    Returns: A set of unique tokens, trimmed and uppercased; empty tokens are discarded.
    """
    if val is None:
        return set()
    s = str(val).strip()
    if not s:
        return set()
    return {t.strip().upper() for t in s.split(',') if t.strip()}

def _apply_value_rule(series: pd.Series, op_token: Optional[str], values: Set[str]) -> pd.Series:
    """
    Apply an 'IN' / 'NOT IN' filter to a string Series.

    Normalizes values to uppercase/stripped before comparison.

    Returns:
        A boolean Series marking rows that satisfy the rule.
        Unknown operators result in an all-True mask.
    """
    if op_token is None or str(op_token).strip() == '' or len(values) == 0:
        return pd.Series(True, index=series.index)
    s = series.fillna('').str.upper().str.strip()
    tok = str(op_token).strip().upper()
    if tok == 'IN':
        return s.isin(values)
    if tok == 'NOT IN':
        return ~s.isin(values)
    # Unknown operator → no-op (all True)
    return pd.Series(True, index=series.index)

def _change_mask(df_log: pd.DataFrame, change_value: Optional[str]) -> pd.Series:
    """
    Build a boolean mask for rows matching a requested change type.

    Behavior:
    - If `change_value` is falsy/blank → all True (no filtering).
    - If `change_value` is 'branch' (or 'branch change'/'branchchange', case-insensitive)
    → rows where STATUS_CHANGE is empty (branch-only changes).
    - Otherwise → case-insensitive exact match on STATUS_CHANGE
    (e.g., 'Inventory to Sold').

    Returns:
        A boolean Series aligned to df_log indicating matching rows.
    """
    cv = (change_value or '').strip()
    if not cv:
        return pd.Series(True, index=df_log.index)
    status_s = df_log['STATUS_CHANGE'].fillna('').str.strip().str.casefold()
    key = cv.casefold()
    if key in {'branch', 'branch change', 'branchchange'}:
        return status_s == ''
    # exact match on STATUS_CHANGE for values like 'Inventory to Sold'
    return status_s == key


def _mask_for_single_rule(df_log: pd.DataFrame, rule_row: pd.Series) -> pd.Series:
    """
    Build a boolean mask for one AlertMatrix rule (AND across fields + change).

    For each field, applies the rule's operator ('IN'/'NOT IN') to CSV values:
        MAK/Make → df_log['MAKE']
        TYP/Type → df_log['TYPE']
        DEPT/Department → df_log['DEPARTMENT']
        GRP/Group → df_log['GROUP_CODE']
    Then ANDs a change filter from rule_row['Change'] via `_change_mask`.

    Returns:
        A boolean Series aligned to df_log indicating rows that satisfy the rule.
    """
    mask = pd.Series(True, index=df_log.index)
    # MAKE/TYPE/DEPARTMENT/GROUP_CODE operators
    for op_col, val_col, log_col in (
        ('MAK',  'Make',       'MAKE'),
        ('TYP',  'Type',       'TYPE'),
        ('DEPT', 'Department', 'DEPARTMENT'),
        ('GRP',  'Group',      'GROUP_CODE'),
    ):
        op = rule_row.get(op_col)
        vals = _tokenize_csv_field(rule_row.get(val_col))
        mask &= _apply_value_rule(df_log[log_col], op, vals)

    # Change mapping (e.g., 'Inventory to Sold', or 'BRANCH')
    mask &= _change_mask(df_log, rule_row.get('Change'))

    return mask

def _branch_mask(df_log: pd.DataFrame, user_branch: str) -> pd.Series:
    """
    Return a branch filter mask over the log DataFrame.

    Behavior:
    - If `user_branch` is blank or indicates ALL ('all', '*', 'any', 'all branches', 'all-branches'),
    return an all-True mask (no filtering).
    - Otherwise, case-insensitive match where PREVIOUS_BRANCH == user_branch
    or CURRENT_BRANCH == user_branch.

    Returns:
        A boolean Series aligned to df_log.
    """
    b = (user_branch or '').strip()
    if not b or b.lower() in {'all', '*', 'any', 'all branches', 'all-branches'}:
        return pd.Series(True, index=df_log.index)
    prev_b = df_log['PREVIOUS_BRANCH'].fillna('').str.strip().str.casefold()
    curr_b = df_log['CURRENT_BRANCH'].fillna('').str.strip().str.casefold()
    b_norm = b.casefold()
    return (prev_b == b_norm) | (curr_b == b_norm)

def compile_change_list_for_user(WANTED_COLUMNS, df_log: pd.DataFrame, df_matrix: pd.DataFrame, user_branch: str, user_role: str) -> pd.DataFrame:
    """
    Build a per-user change list by branch + role-based AlertMatrix rules.

    Applies:
    - Branch filter: PREVIOUS_BRANCH == user_branch OR CURRENT_BRANCH == user_branch;
    skipped if user_branch indicates ALL.
    - Role rules: OR across AlertMatrix rows for the user's role; each row is an
    AND of field rules and an optional change mapping. If no rules exist for the
    role, only the branch filter is applied.

    Returns:
        A copy of the filtered DataFrame with columns limited to WANTED_COLUMNS
        (missing columns are logged and omitted).
    """
    # Branch mask (handles All)
    branch_mask = _branch_mask(df_log, user_branch)

    # Select matrix rows for the role
    role_mask = df_matrix['Role'].fillna('').str.strip() == (user_role or '').strip()
    role_rows = df_matrix.loc[role_mask]

    if role_rows.empty:
        logging.warning(f'No AlertMatrix rules found for role "{user_role}"; skipping role-based filter (branch-only).')
        filtered = df_log.loc[branch_mask]
    else:
        any_rule_mask = pd.Series(False, index=df_log.index)
        for _, rr in role_rows.iterrows():
            any_rule_mask |= _mask_for_single_rule(df_log, rr)
        filtered = df_log.loc[branch_mask & any_rule_mask]

    # Final column projection
    missing = [c for c in WANTED_COLUMNS if c not in filtered.columns]
    if missing:
        logging.error(f'Missing expected columns in dfChangeLog: {missing}')
        cols = [c for c in WANTED_COLUMNS if c in filtered.columns]
    else:
        cols = WANTED_COLUMNS

    return filtered.loc[:, cols].copy()

# ------------------------------------------------------------
# Helper functions — Salesperson and Purchaser Evaluation
# ------------------------------------------------------------

def _find_col(df: pd.DataFrame, target_upper: str) -> str | None:
    """
    Return the first column name matching target_upper (case-insensitive), or None.
    """
    for c in df.columns:
        if str(c).upper() == target_upper:
            return c
    return None

def compile_change_list_for_Salesmen(WANTED_COLUMNS, df_log: pd.DataFrame, person_email: str) -> pd.DataFrame:
    """
    Rows where email matches either Salesperson_Email or Purchaser_Email.
    """
    if not person_email:
        return df_log.iloc[0:0]  # empty with same cols

    sp_col = _find_col(df_log, 'SALESPERSON_EMAIL')
    pu_col = _find_col(df_log, 'PURCHASER_EMAIL')
    if not sp_col and not pu_col:
        logging.error('Expected SALESPERSON_EMAIL / PURCHASER_EMAIL not found in dfChangeLog.')
        return df_log.iloc[0:0]

    e = person_email.strip().casefold()
    sp = df_log[sp_col].fillna('').astype(str).str.strip().str.casefold() if sp_col else pd.Series(False, index=df_log.index)
    pu = df_log[pu_col].fillna('').astype(str).str.strip().str.casefold() if pu_col else pd.Series(False, index=df_log.index)
    filtered = df_log.loc[(sp == e) | (pu == e)]

    # Project to your usual email table columns
    cols = [c for c in WANTED_COLUMNS if c in filtered.columns]
    return filtered.loc[:, cols].copy()

def append_Salesmen_to_dfAlertUsers(dfAlertUsers: pd.DataFrame, df_log: pd.DataFrame) -> pd.DataFrame:
    """
    Build Dataframe with unique Salesperson Email and Name
    Where Salesperson is in Salesperson or Purchaser column of dfChangelog
    """
    sp_email_col = _find_col(df_log, 'SALESPERSON_EMAIL')
    pu_email_col = _find_col(df_log, 'PURCHASER_EMAIL')
    sp_name_col  = _find_col(df_log, 'SALESPERSON')
    pu_name_col  = _find_col(df_log, 'PURCHASER')

    mapping: dict[str, str] = {}

    def _clean_email(x) -> str:
        # Drop NA/None/NaN; normalize whitespace & case
        if pd.isna(x):
            return ''
        s = str(x).strip()
        return s.lower() if '@' in s else ''

    def _clean_name(x) -> str:
        if pd.isna(x):
            return ''
        return str(x).strip()

    def add(email, name):
        e = _clean_email(email)
        if not e:
            return
        n = _clean_name(name) or e  # fallback to email if name missing
        # prefer the longer, non-empty name if we see the same email twice
        prev = mapping.get(e)
        if not prev or (n and len(n) > len(prev)):
            mapping[e] = n

    # Collect from Salesperson columns
    if sp_email_col:
        sp_names = df_log[sp_name_col] if sp_name_col else None
        for em, nm in zip(df_log[sp_email_col], (sp_names if sp_names is not None else [None] * len(df_log))):
            add(em, nm)

    # Collect from Purchaser columns
    if pu_email_col:
        pu_names = df_log[pu_name_col] if pu_name_col else None
        for em, nm in zip(df_log[pu_email_col], (pu_names if pu_names is not None else [None] * len(df_log))):
            add(em, nm)

    # Return a stable, printable DataFrame
    rows = [{'Email': e, 'Name': mapping[e]} for e in sorted(mapping)]

    dfSalesmen = pd.DataFrame(rows, columns=['Email', 'Name'])
    dfSalesmen = dfSalesmen.assign(Role='Salesperson', Branch='All')
    dfAlertUsers = pd.concat([dfAlertUsers, dfSalesmen], ignore_index=True)

    return dfAlertUsers

