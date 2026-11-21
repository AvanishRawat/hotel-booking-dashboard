"""Read an uploaded file and clean it.

The file must have the same columns as data/hotel_bookings.csv.
"""
import base64
import io

import pandas as pd

# Text columns that clean() never edits. Reading them straight in as
# categories keeps memory low (the free Render server only has 512 MB).
CATEGORY_COLUMNS = {
    column: "category" for column in [
        "hotel", "meal", "market_segment", "distribution_channel",
        "reserved_room_type", "assigned_room_type", "deposit_type",
        "customer_type", "reservation_status", "reservation_status_date",
    ]
}


def read_bookings(source, filename=".csv"):
    """Read a CSV or Excel file (a path or file-like object)."""
    if str(filename).endswith(".csv"):
        return pd.read_csv(source, dtype=CATEGORY_COLUMNS)
    return pd.read_excel(source, dtype=CATEGORY_COLUMNS)


def parse_upload(contents, filename):
    """Turn the file from dcc.Upload into a DataFrame."""
    data = base64.b64decode(contents.split(",")[1])
    return read_bookings(io.BytesIO(data), filename)


def clean(df):
    df = df.copy()   # work on our own copy (avoids pandas copy warnings)

    # 1. Missing values
    df["children"] = df["children"].fillna(0)
    df["country"] = df["country"].fillna("Unknown")
    df = df.drop(columns=["agent", "company"])   # mostly empty ID columns

    # 2. Remove impossible rows
    df = df[(df["adr"] >= 0) & (df["adr"] < 1000)]                  # bad prices
    df = df[df["adults"] + df["children"] + df["babies"] > 0].copy() # no guests

    # 3. Derived columns
    df["arrival_date"] = pd.to_datetime(
        df["arrival_date_year"].astype(str) + "-"
        + df["arrival_date_month"] + "-"
        + df["arrival_date_day_of_month"].astype(str),
        format="%Y-%B-%d")
    df["arrival_month_num"] = df["arrival_date"].dt.month
    df["total_nights"] = df["stays_in_weekend_nights"] + df["stays_in_week_nights"]

    # 4. Store the remaining text columns as categories too (less memory)
    df["country"] = df["country"].astype("category")
    df["arrival_date_month"] = df["arrival_date_month"].astype("category")

    return df
