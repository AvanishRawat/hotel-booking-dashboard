import plotly.express as px

from charts import placeholder

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def make_chart3(df):
    """Compare monthly cancellation rates over time for each hotel."""
    if df.empty:
        return placeholder(df, "No bookings match the selected filters")

    monthly = (
        df.dropna(subset=["arrival_date", "is_canceled"])
        .assign(
            arrival_month=lambda data: (
                data["arrival_date"].dt.to_period("M").dt.to_timestamp()
            )
        )
        .groupby(["hotel", "arrival_month"], as_index=False)
        .agg(
            cancellation_rate=("is_canceled", "mean"),
            bookings=("is_canceled", "size"),
        )
    )
    if monthly.empty:
        return placeholder(df, "No monthly booking data available")

    monthly["arrival_year"] = monthly["arrival_month"].dt.year
    monthly["arrival_month_num"] = monthly["arrival_month"].dt.month
    shared = monthly.pivot(
        index="arrival_month", columns="hotel", values="cancellation_rate"
    )
    if {"City Hotel", "Resort Hotel"} <= set(shared.columns):
        shared = shared.dropna(subset=["City Hotel", "Resort Hotel"])
    if len(shared) and {"City Hotel", "Resort Hotel"} <= set(shared.columns):
        latest = shared.iloc[-1]
        latest_month = shared.index[-1]
        if latest["Resort Hotel"] >= latest["City Hotel"]:
            title = (
                f"Resort cancellations caught up by "
                f"{latest_month:%b %Y}"
            )
        else:
            city_higher = (
                shared["City Hotel"] > shared["Resort Hotel"]
            ).mean()
            title = (
                f"City Hotel had a higher cancellation rate in "
                f"{city_higher:.0%} of shared months"
            )
    else:
        peak = monthly.loc[monthly["cancellation_rate"].idxmax()]
        title = (
            f"{peak['hotel']} cancellations peaked at "
            f"{peak['cancellation_rate']:.1%} in "
            f"{peak['arrival_month']:%b %Y}"
        )

    fig = px.line(
        monthly,
        x="arrival_month",
        y="cancellation_rate",
        color="hotel",
        markers=True,
        custom_data=["arrival_year", "arrival_month_num", "bookings"],
        color_discrete_map={
            "City Hotel": "#2563eb",
            "Resort Hotel": "#f59e0b",
        },
        labels={
            "arrival_month": "Arrival month",
            "cancellation_rate": "Cancellation rate",
            "hotel": "Hotel",
        },
    )
    fig.update_traces(
        hovertemplate=(
            "%{fullData.name}<br>%{x|%b %Y}<br>"
            "Cancellation rate: %{y:.1%}<br>"
            "Bookings: %{customdata[2]:,}<extra></extra>"
        )
    )
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15)),
        height=360,
        margin=dict(l=55, r=16, t=62, b=78),
        legend=dict(title="Hotel", orientation="h",
                    yanchor="top", y=-0.28, xanchor="left", x=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_xaxes(dtick="M3", tickformat="%b %Y", tickangle=-35,
                     showgrid=False)
    fig.update_yaxes(tickformat=".0%", range=[0, 1], showgrid=True,
                     gridcolor="#e5e7eb")
    return fig
