import dash
import numpy
from dash import dcc
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas
from wallet_keeper.pages.preprocessing import df_transactions, prefixes, original_accounts, explode_accounts, df_prices
from wallet_keeper.modules.utils.colors import to_rgba
from dash import dcc, html, Input, Output, callback, MATCH, dash_table

dash.register_page(__name__, path='/', order=1)

# Preprocess dataframe for overview
df_totals = df_transactions.groupby(["account", "currency"]).agg({
    "amount": "sum"
}).reset_index()
df_totals["amount"] = df_totals["amount"].round(decimals=2)

# Unify currencies for the overview



def display_bar_totals():
    df = df_totals.copy()
    df = df[df.account.isin(prefixes)].reset_index()

    # Show discrepancies
    delta_name = "Unaccouted for"
    for name, group in df.groupby("currency"):
        delta = -1 * df.amount.sum()
        if delta != 0.0:
            df.loc[len(df)] = {
                "account": delta_name,
                "amount": delta,
                "currency": name
            }

    # Assign pattern shape
    pattern_shape_map = {a: None for a in prefixes}
    pattern_shape_map.update({delta_name: "/"})

    # Figure
    limit = df.amount.apply("abs").max().round(-3)
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

    fig.update_layout(title="Current totals")
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


def display_accounts_sunburst(name):
    df = df_totals[df_totals.account.isin(original_accounts)].copy()
    df = explode_accounts(df)

    # Select group
    df = df[(df.account.str.startswith(name))]
    df = df.sort_values("account")

    # Apply custom summation in order to handle negative values
    df["sign"] = df["amount"].apply(lambda x: -1 if x < 0 else 1)
    df["amount"] = df["amount"].abs()
    df["account"] = df["account"].apply(lambda x: x.replace(" ", "_"))

    # Sum up backwards
    if len(df) > 0:
        for i, d in enumerate(range(1, max(df.depth) + 1)[::-1]):
            mask = df.depth == d
            dfg = df[mask].groupby(["parent"]).agg({
                "amount": "sum",
                "currency": "first"
            }).reset_index()
            dfg = dfg.rename(columns={"parent": "account"})
            dfg["name"] = dfg["account"].apply(lambda x: x.split(":")[-1])
            dfg["parent"] = dfg["account"].apply(lambda x: ":".join(x.split(":")[:-1]))
            dfg["sign"] = 1
            dfg["amount"] = dfg["amount"].round(2)
            dfg["depth"] = d - 1
            df = pandas.concat([df, dfg])

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
    n = len(prefixes)
    if n % 2 > 0:
        prefix_matrix = prefixes + [None]
    else:
        prefix_matrix = prefixes
    prefix_matrix = numpy.array(prefix_matrix).reshape(-1, 2)

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
                            figure=display_accounts_sunburst(col))
                    ],
                        width=6
                    )
                )
            else:
                children.append(
                    dbc.Col([],
                            width=6
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
