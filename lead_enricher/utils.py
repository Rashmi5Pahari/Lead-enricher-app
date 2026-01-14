import pandas as pd
from io import StringIO

def read_csv_bytes(uploaded) -> pd.DataFrame:
    # uploaded can be st.uploaded_file
    try:
        return pd.read_csv(uploaded)
    except Exception:
        # try decode
        s = uploaded.getvalue().decode("utf-8")
        return pd.read_csv(StringIO(s))
