"""Read an uploaded file and clean it.

The file must have the same columns as data/hotel_bookings.csv.
"""
import base64
import io

import pandas as pd


def parse_upload(contents, filename):
    """Turn the file from dcc.Upload into a DataFrame."""
    data = base64.b64decode(contents.split(",")[1])
    if filename.endswith(".csv"):
        return pd.read_csv(io.BytesIO(data))
    return pd.read_excel(io.BytesIO(data))


def clean(df):
    df = df.copy()

    # 1. Missing values
    df["children"] = df["children"].fillna(0)
    df["country"] = df["country"].fillna("Unknown")
    df = df.drop(columns=["agent", "company"])   # mostly empty ID columns

    # 2. Remove impossible rows
    df = df[(df["adr"] >= 0) & (df["adr"] < 1000)]                  # bad prices
    df = df[df["adults"] + df["children"] + df["babies"] > 0]        # no guests

    # 3. Derived columns
    df["arrival_date"] = pd.to_datetime(
        df["arrival_date_year"].astype(str) + "-"
        + df["arrival_date_month"] + "-"
        + df["arrival_date_day_of_month"].astype(str),
        format="%Y-%B-%d")
    df["arrival_month_num"] = df["arrival_date"].dt.month
    df["total_nights"] = df["stays_in_weekend_nights"] + df["stays_in_week_nights"]

    # 4. Store text columns as categories: same values, ~5x less memory
    #    (keeps the app within the free Render server's 512 MB)
    text_columns = df.select_dtypes(include="object").columns
    df[text_columns] = df[text_columns].astype("category")

    return df
