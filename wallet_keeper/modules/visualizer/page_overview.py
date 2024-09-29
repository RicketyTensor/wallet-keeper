from dash import dcc, html, Input, Output, callback, dash_table, register_page, MATCH, callback_context
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import numpy
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas
from dash import dcc, html
from wallet_keeper.modules.visualizer import processing
from wallet_keeper.modules.visualizer.common import make_month_selector, filter_dataframe_monthly
from decimal import Decimal

register_page(__name__, path='/', order=1, name="Spending overview")


@callback(
    Output("overview_bar_totals", "figure"),
    Input('data_totals', 'data'),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value")
)
def display_bar_totals(data_totals, month_start, month_end):
    # Transfer to dataframe
    df = pandas.DataFrame(data_totals)

    # Transform to datetime format
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

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


@callback(
    Output({"type": "overview_graph_sunburst", "index": MATCH}, "figure"),
    Input('data_totals', 'data'),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value")
)
def display_accounts_sunburst(data_totals, month_start, month_end):
    idx = callback_context.outputs_list['id']['index']  # get id of current callback

    # Transfer to dataframe
    df = pandas.DataFrame(data_totals)

    # Transform to datetime format
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    # Select group
    df = df[(df.account.str.startswith(idx))]
    df = df.sort_values("account")

    # Apply custom summation in order to handle negative values
    df["sign"] = df["amount"].apply(lambda x: -1 if x < 0 else 1)
    df["amount"] = df["amount"].abs().apply(lambda x: Decimal(x))

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
                        df.loc[df.account == parent, "amount"] += Decimal(r.amount)

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
    df = processing.get_account_totals(hierarchy=True)
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
                            id={"type": "overview_graph_sunburst", "index": col}
                        )
                    ], width=12 / ncol)
                )
            else:
                children.append(
                    dbc.Col([],
                            width=12 / ncol
                            )
                )
        grid.append(dbc.Row(children=children))

    return grid


# History graph
@callback(
    Output("overview_categories_graph", "figure"),
    Input('data_monthly', 'data'),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value")
)
def display_categories(analytics_monthly, month_start, month_end):
    if not analytics_monthly:
        return go.Figure()

    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    dfm = pandas.DataFrame(analytics_monthly)
    dfm["date"] = pandas.to_datetime(dfm["date"])

    dfm = dfm.groupby(["date", "category"]).agg({
        "total": "sum"
    }).reset_index()
    for acc, group in dfm.groupby(["category"]):
        dfm.loc[dfm["category"] == acc[0], "total"] = group["total"].cumsum().values

    # Generate figure
    fig = px.area(dfm, x="date", y="total", color="category")

    fig.update_xaxes(range=[dmin - timedelta(days=30),
                            dmax + timedelta(days=30)])
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Total")
    return fig


@callback(
    Output({"type": "overview_category_graph", "index": MATCH}, "figure"),
    Input('data_monthly', 'data'),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value")
)
def display_cetegory(data_monthly, month_start, month_end):
    idx = callback_context.outputs_list['id']['index']  # get id of current callback

    # Transfer to dataframe
    df = pandas.DataFrame(data_monthly)
    df["date"] = pandas.to_datetime(df["date"])

    # Transform to datetime format
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    df = df[df["category"] == idx].copy()
    for acc, group in df.groupby(["account"]):
        df.loc[df["account"] == acc[0], "total"] = group["total"].cumsum().values

    # Generate figure
    fig = px.area(df, x="date", y="total", color="account")

    fig.update_xaxes(range=[dmin - timedelta(days=30),
                            dmax + timedelta(days=30)])
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Total")

    return fig


def category_grid():
    df = processing.get_account_totals(hierarchy=False)
    categories = list(filter(None, {processing.get_account_category(a) for a in df["account"] if a}))

    n = len(categories)
    ncol = 2
    nrow = 1 + n // ncol if n % ncol else 1
    if nrow > 1:
        prefix_matrix = categories + [None] * (ncol - n % ncol)
    else:
        prefix_matrix = categories
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
                            id={"type": "overview_category_graph", "index": col}
                        )
                    ])
                )
            else:
                children.append(
                    dbc.Col([])
                )
        grid.append(dbc.Row(children=children))

    return grid


layout = dbc.Container(children=[
    dcc.Store(id='data_totals'),
    dcc.Store(id='data_monthly'),
    dbc.Row(children=[
        dbc.Col(children=[
            make_month_selector()
        ], width=1),
        dbc.Col(children=[
            dcc.Graph(id="overview_bar_totals")
        ], width=11),
    ]),
    dbc.Row(children=[
        *sunburst_grid()
    ]),
    dbc.Row(children=[
        dbc.Col(children=[
            dcc.Graph(id="overview_categories_graph")
        ], width=4),
        dbc.Col(children=[
            *category_grid()
        ], width=8)
    ]),
], fluid=True)
