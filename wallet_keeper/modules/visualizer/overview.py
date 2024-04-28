import dash
import numpy
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas
from dash import dcc, html
from wallet_keeper.modules.visualizer import processing
from decimal import Decimal

dash.register_page(__name__, path='/', order=1, name="Spending overview")

def display_bar_totals():
    df = processing.get_account_totals()
    mask = df.depth == 0
    df = df[mask]
    prefixes = df.account.values

    # Show discrepancies
    delta_name = "Unaccounted for"
    for name, group in df.groupby("currency"):
        delta = -1 * df.amount.sum()
        if delta != 0.0:
            df.loc[len(df)] = {
                "account": delta_name,
                "amount": delta,
                "currency": name,
                "depth": 0
            }

    # Assign pattern shape
    pattern_shape_map = {a: None for a in prefixes}
    pattern_shape_map.update({delta_name: "/"})

    # Figure
    limit = df.amount.apply("abs").max()
    fig = go.Figure(
        px.bar(
            df,
            x="amount",
            y="currency",
            orientation="h",
            color="account",
            text_auto=True,
            pattern_shape="account",
            pattern_shape_map=pattern_shape_map
        )
    )

    fig.update_layout(title="Transaction split")
    fig.update_layout(xaxis_range=[-limit, limit])
    fig.update_xaxes(title_text="Account")
    fig.update_yaxes(title_text="Amount")
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))
    return fig


def display_accounts_sunburst(name, df):
    # Select group
    df = df[(df.account.str.startswith(name))]
    df = df.sort_values("account")

    # Apply custom summation in order to handle negative values
    df["sign"] = df["amount"].apply(lambda x: -1 if x < 0 else 1)
    df["amount"] = df["amount"].abs()

    # Sum up backwards
    if len(df) > 0:
        # reset parents
        for j, r in df.iterrows():
            if r.parent:
                df.loc[df.account == r.parent, "amount"] = Decimal(0.0)

        for i in list(range(1, max(df.depth) + 1))[::-1]:
            mask = df.depth == i
            groups = df[mask].groupby(["account", "currency"])
            for name, group in groups:
                parent = ":".join(name[0].split(":")[:-1])
                if parent:
                    for j, r in group.iterrows():
                        df.loc[df.account == parent, "amount"] += r.amount

    df.account = df.account.apply(lambda x: x.replace(" ", "_"))
    df["name"] = df.account.apply(lambda x: x.split(":")[-1])
    ids = list(df.account.apply(lambda x: ":".join(x.split(":")[1:])))
    parents = list(df.parent.apply(lambda x: ":".join(x.split(":")[1:])))
    labels = list(df.name)
    values = df.amount.values
    discrete_pattern = df.sign.apply(lambda x: "/" if x < 0 else "").values

    fig = go.Figure()
    fig.add_trace(go.Sunburst(
        labels=labels,  # mandatory
        ids=ids,  # optional
        parents=parents,  # mandatory
        values=values,  # mandatory
        branchvalues="total",
        marker={
            # "colors": color_discrete_sequence,
            "pattern": {"shape": discrete_pattern}
        }
    ))
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
    fig.update_layout(font_size=20,
                      height=1400)
    return fig


def sunburst_grid():
    df = processing.get_account_totals()
    prefixes = list(df[df.depth == 0].account.values)

    n = len(prefixes)
    ncol = 4
    nrow = 1 + n // ncol if n % ncol else 1
    if nrow > 1:
        prefix_matrix = prefixes + [None] * (ncol - n % ncol)
    else:
        prefix_matrix = prefixes
    prefix_matrix = numpy.array(prefix_matrix).reshape(-1, ncol)

    grid = []
    for row in prefix_matrix:
        children = []
        for col in row:
            if col is not None:
                children.append(
                    dbc.Col(children=[
                        html.H4(col.capitalize()),
                        dcc.Graph(
                            id="overview_graph_sunburst_{}".format(col),
                            figure=display_accounts_sunburst(col, df))
                    ],
                        width=12 / ncol
                    )
                )
            else:
                children.append(
                    dbc.Col([],
                            width=12 / ncol
                            )
                )
        grid.append(dbc.Row(children=children))

    return grid


layout = dbc.Container(children=[
    dcc.Store(id='data_totals'),
    dbc.Row([
        dbc.Col(children=[
            dcc.Graph(id="overview_graph_totals", figure=display_bar_totals())
        ]),
    ]),
    dbc.Row([
        *sunburst_grid()
    ])
], fluid=True)
