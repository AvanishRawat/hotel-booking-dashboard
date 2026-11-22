"""Chart 1: which kinds of bookings are canceled most? (horizontal bar chart)

One bar per group of the chosen category (deposit type, market segment, ...):
  bar length = share of that group's bookings that were canceled,
  dotted line = cancellation rate of all bookings shown.
Bars are sorted from most to least canceled. Clicking a bar filters the other
charts to that group; the selected bar stays red and the others turn grey.
"""
import plotly.graph_objects as go

from charts import placeholder

# Category columns the dropdown can switch between, with readable names
CATEGORIES = {
    "deposit_type": "Deposit type",
    "market_segment": "Market segment",
    "customer_type": "Customer type",
    "distribution_channel": "Distribution channel",
    "meal": "Meal plan",
}
DEFAULT_CATEGORY = "deposit_type"

# Readable names for coded values. The raw value is still used for filtering.
VALUE_NAMES = {
    "meal": {"BB": "Bed & breakfast (BB)", "HB": "Half board (HB)",
             "FB": "Full board (FB)", "SC": "No meal (SC)",
             "Undefined": "No meal (Undefined)"},
}

# Takeaway title for each category; {} is the most-canceled group
TITLES = {
    "deposit_type": "{} bookings cancel most",
    "market_segment": "The {} segment cancels most",
    "customer_type": "{} customers cancel most",
    "distribution_channel": "Bookings via {} cancel most",
    "meal": "{} bookings cancel most",
}

MIN_BOOKINGS = 20  # same rule as Chart 2: hide groups too small to trust

RED = "#cb181d"    # cancellations are red in Charts 1 and 2
GREY = "#d1d5db"   # bars that are not selected
INK, MUTED, GRID = "#1f2937", "#6b7280", "#e5e7eb"
BAR_PX = 24                         # bar thickness in pixels
HEIGHT, TOP, BOTTOM = 440, 70, 80   # figure height and top/bottom margins


def group_name(column, value):
    """Readable name for one group, e.g. ("meal", "BB") -> "Bed & breakfast (BB)"."""
    return VALUE_NAMES.get(column, {}).get(value, str(value))


def make_chart1(df, category=DEFAULT_CATEGORY, selected=None):
    """Cancellation rate per group of `category`; `selected` is the raw value
    of the bar clicked in this chart (highlighted), or None."""
    if df.empty:
        return placeholder(df, "No bookings match the selected filters")

    groups = (df.groupby(category, observed=True)["is_canceled"]
              .agg(rate="mean", canceled="sum", bookings="size")
              .reset_index())
    hidden = groups[groups["bookings"] < MIN_BOOKINGS]
    groups = (groups[groups["bookings"] >= MIN_BOOKINGS]
              .sort_values("rate", ascending=False))
    if groups.empty:
        return placeholder(df, "Too few bookings to compare by "
                           + CATEGORIES[category].lower())

    overall = df["is_canceled"].mean()
    values = [str(v) for v in groups[category]]
    names = [group_name(category, v) for v in values]
    colors = [RED if selected is None or v == selected else GREY
              for v in values]

    # Keep bars thin: leave whatever the 24px bar doesn't fill as space
    slot_px = (HEIGHT - TOP - BOTTOM) / len(groups)
    bargap = min(0.85, max(0.2, 1 - BAR_PX / slot_px))

    fig = go.Figure(go.Bar(
        x=groups["rate"], y=names, orientation="h",
        marker=dict(color=colors, cornerradius=4),
        customdata=list(zip(values, groups["canceled"].astype(int),
                            groups["bookings"].astype(int),
                            groups["bookings"] / len(df))),
        texttemplate="%{x:.0%}", textposition="outside",
        textfont=dict(color=INK, size=12), cliponaxis=False,
        hovertemplate=("<b>%{y}</b><br>"
                       "Canceled: <b>%{x:.0%}</b> "
                       "(%{customdata[1]:,} of %{customdata[2]:,})<br>"
                       "%{customdata[3]:.0%} of all bookings shown<br>"
                       "<i>Click to filter Charts 2, 3 and 4</i>"
                       "<extra></extra>"),
    ))

    # Reference: the cancellation rate of every booking shown
    fig.add_vline(x=overall, layer="below",   # behind bars and their labels
                  line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_annotation(x=overall, y=1, xref="x", yref="paper",
                       yanchor="bottom", showarrow=False,
                       text=f"All bookings: {overall:.0%}",
                       font=dict(size=11, color=MUTED))
    if len(hidden):
        hidden_names = ", ".join(group_name(category, str(v))
                                 for v in hidden[category])
        fig.add_annotation(x=0, y=0, xref="paper", yref="paper",
                           xanchor="left", yanchor="top", yshift=-52,
                           showarrow=False, align="left",
                           text=f"Not shown (fewer than {MIN_BOOKINGS} "
                                f"bookings): {hidden_names}",
                           font=dict(size=11, color=MUTED))

    # Takeaway title: the most-canceled group against the overall rate
    top = groups.iloc[0]
    if len(groups) == 1:
        title = f"Only {names[0]} bookings left: {top['rate']:.0%} canceled"
    else:
        title = (TITLES.get(category, "{} bookings cancel most")
                 .format(names[0])
                 + f": {top['rate']:.0%} vs {overall:.0%} overall")

    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15)),
        height=HEIGHT, bargap=bargap, showlegend=False,
        hovermode="y",      # hover anywhere along a bar's row, not just on it
        dragmode=False,
        hoverlabel=dict(bgcolor="white", font=dict(color=INK)),
        margin=dict(l=10, r=16, t=TOP, b=BOTTOM),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    fig.update_xaxes(title="Canceled (share of the group's bookings)",
                     title_font=dict(size=12, color=MUTED),
                     range=[0, 1.12], tickformat=".0%",
                     tickvals=[0, 0.25, 0.5, 0.75, 1],
                     gridcolor=GRID, zeroline=False)
    fig.update_yaxes(autorange="reversed", automargin=True, ticksuffix="  ")
    return fig
