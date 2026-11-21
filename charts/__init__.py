import threading

import plotly.graph_objects as go

# Plotly Express is not thread-safe: two callbacks building figures at the
# same time can crash with "ValueError: Invalid value". Build one at a time.
FIGURE_LOCK = threading.Lock()


def placeholder(df, label):
    """Empty figure shown until a real chart replaces it."""
    fig = go.Figure()
    fig.add_annotation(
        text=f"{label}<br><sub>{len(df):,} bookings after filters</sub>",
        showarrow=False, font=dict(size=16, color="#6b7280"))
    fig.update_layout(
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white", paper_bgcolor="white", height=360)
    return fig
