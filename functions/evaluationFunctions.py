import pandas as pd

# ------------------------------------------------------------
# Helper functions — Build user list
# ------------------------------------------------------------
def build_dfUsers_from_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds and email df from df
    """
    email_col = _find_col(df, 'EMAIL')
    name_col  = _find_col(df, 'NAME')

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

    # Collect from Email column
    if email_col:
        names = df[name_col] if name_col else None
        for em, nm in zip(df[email_col], (names if names is not None else [None] * len(df))):
            add(em, nm)

    # Return a stable, printable DataFrame
    rows = [{'Email': e, 'Name': mapping[e]} for e in sorted(mapping)]
    dfEmails = pd.DataFrame(rows, columns=['Email', 'Name'])


    # Add Role and Branch columns to df
    dfEmails = dfEmails.assign(Role='Settlement Auditor', Branch='All')

    return dfEmails

def _find_col(df: pd.DataFrame, target_upper: str) -> str | None:
    """
    Return the first column name matching target_upper (case-insensitive), or None.
    """
    for c in df.columns:
        if str(c).upper() == target_upper:
            return c
    return None

def compile_error_list(WANTED_COLUMNS, df_log: pd.DataFrame, person_email: str) -> pd.DataFrame:
    """
    Return rows where EMAIL matches person_email (case-insensitive).
    """
    if not person_email:
        return df_log.iloc[0:0]  # empty with same cols

    # Find the EMAIL column (case-insensitive), and fail clearly if it's missing.
    email_col = _find_col(df_log, 'EMAIL')
    if email_col is None:
        raise KeyError("Expected EMAIL column not found in df_log.")

    e = person_email.strip().casefold()
    em = df_log[email_col].fillna('').astype(str).str.strip().str.casefold() if email_col else pd.Series(False, index=df_log.index)

    filtered = df_log.loc[em == e]

    # Keep only the requested columns that exist
    cols = [c for c in WANTED_COLUMNS if c in filtered.columns]
    return filtered.loc[:, cols].copy()
