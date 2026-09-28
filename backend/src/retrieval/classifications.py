"""Classification projections used by CPC-only database and graph edges."""

import pandas as pd


def cpc_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Return only nonblank CPC links; IPCR/US remain in the source export."""
    required = {"patent_id", "classification_type", "classification_code"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Classification data missing columns: {', '.join(sorted(missing))}")
    result = frame.loc[
        frame["classification_type"].str.strip().eq("CPC")
        & frame["patent_id"].str.strip().ne("")
        & frame["classification_code"].str.strip().ne("")
    ].copy()
    for column in required:
        result[column] = result[column].str.strip()
    return result
