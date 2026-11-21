"""Chart 2: how do lead time and average daily rate relate to cancellations? (heatmap)

Each cell is a group of bookings (all hotels in the current filter):
  x = lead time range (days booked ahead), y = average daily rate (ADR) range (€),
  color and label = share of those bookings that were canceled.
Clicking a cell filters the other charts to that group of bookings.
"""
import plotly.graph_objects as go

from charts import placeholder

LEAD_STEP, LEAD_MAX = 30, 360   # 0-29, 30-59, ... 360+ days
PRICE_STEP, PRICE_MAX = 50, 200  # €0-49, €50-99, ... €200+
MIN_BOOKINGS = 20                # hide cells with too few bookings


def lead_bin(lead_time):
    """Lower edge of the lead-time range, e.g. 75 days -> 60 (the 60–89 range)."""
    return lead_time.clip(upper=LEAD_MAX) // LEAD_STEP * LEAD_STEP


def price_bin(adr):
    """Lower edge of the ADR range, e.g. €130 -> 100."""
    return adr.clip(upper=PRICE_MAX) // PRICE_STEP * PRICE_STEP


def label(lo, step, top, unit=""):
    return f"{unit}{top}+" if lo >= top else f"{unit}{lo}–{unit}{lo + step - 1}"


def make_chart2(df):
    if df.empty:
        return placeholder(df, "No bookings match the selected filters")

    # Cancellation rate, canceled count and booking count for every cell
    cells = (df.assign(lead=lead_bin(df["lead_time"]).astype(int),
                       price=price_bin(df["adr"]).astype(int))
             .groupby(["price", "lead"])["is_canceled"]
             .agg(["mean", "sum", "size"]))
    leads = list(range(0, LEAD_MAX + 1, LEAD_STEP))
    prices = list(range(0, PRICE_MAX + 1, PRICE_STEP))

    rates, counts = [], []
    for p in prices:
        rate_row, count_row = [], []
        for l in leads:
            mean, canceled, n = (cells.loc[(p, l)] if (p, l) in cells.index
                                 else (None, 0, 0))
            rate_row.append(mean if n >= MIN_BOOKINGS else None)
            count_row.append([int(canceled), int(n)])
        rates.append(rate_row)
        counts.append(count_row)

    fig = go.Figure(go.Heatmap(
        z=rates,
        x=[label(l, LEAD_STEP, LEAD_MAX) for l in leads],
        y=[label(p, PRICE_STEP, PRICE_MAX, "€") for p in prices],
        customdata=counts,
        colorscale="Reds", zmin=0, zmax=1,
        colorbar=dict(title="Canceled (% of bookings)", tickformat=".0%",
                      thickness=10,
                      orientation="h", y=-0.5, len=0.7),
        texttemplate="%{z:.0%}",
        textfont=dict(size=10),
        xgap=2, ygap=2,
        hovertemplate=("Lead time: %{x} days<br>"
                       "Average daily rate (ADR): %{y}<br>"
                       "Canceled: <b>%{z:.0%}</b> "
                       "(%{customdata[0]:,} of %{customdata[1]:,})"
                       "<extra></extra>"),
    ))

    # Takeaway: bookings made within a month vs. 6+ months ahead
    short = df.loc[df["lead_time"] <= 30, "is_canceled"].mean()
    long = df.loc[df["lead_time"] > 180, "is_canceled"].mean()
    title = ("Bookings made further ahead cancel more" if long > short
             else "Lead time does not raise cancellations here")

    fig.update_layout(title=title, title_x=0, height=500,
                      margin=dict(l=70, r=16, t=60, b=170),
                      plot_bgcolor="#f3f4f6")
    fig.update_xaxes(title="Lead time (days booked ahead)", tickangle=-45)
    fig.update_yaxes(title="Average daily rate (€ per night)")
    return fig
