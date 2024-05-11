import dash
from dash import dcc, html, Input, Output, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import calendar
from dateutil.relativedelta import relativedelta
import pandas
from wallet_keeper.modules.visualizer import processing
from decimal import Decimal
import re
import numpy
from statsmodels.tsa.arima.model import ARIMA

dash.register_page(__name__, order=3, name="Accounts")


def make_month_selector():
    t0, t1 = processing.get_time_span()
    month_list = [i.strftime("%m/%Y") for i in pandas.date_range(start=t0, end=t1, freq='SMS', inclusive="both")]

    selector = dbc.Row(children=[
        dcc.Dropdown(
            month_list, month_list[0],
            id="select_month_range_start",
            placeholder="Start MM/YYYY",
            clearable=False
        ),
        dcc.Dropdown(
            month_list, month_list[-1],
            id="select_month_range_end",
            placeholder="End MM/YYYY",
            clearable=False
        )
    ])

    return html.Div([html.H5("Select date range:"), selector])


# Range slider for accounting
def get_first_and_last_day(t0, t1):
    d0 = t0.replace(day=1)
    r1 = calendar.monthrange(t1.year, t1.month)
    d1 = t1.replace(day=r1[1])
    return d0, d1


# Layout
# ======
layout = dbc.Container(
    children=[
        dcc.Store(id='analytics_monthly'),
        dbc.Row(children=[
            dbc.Col(children=[
                make_month_selector(),
                html.H4("Monthly development"),
                dbc.Row([
                    dbc.Col([dcc.Graph(id="analytics_history_graph")]),
                ])

            ], width=3),
            dbc.Col(children=[
                dbc.Row(id='monthly_breakdown_categories', children=[])
            ], width=9)
        ])
    ],
    fluid=True
)


# Dataframe for monthly analytics
@callback(
    Output('analytics_monthly', 'data'),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value"),
)
def filter_dataframe_monthly(month_start, month_end):
    # Apply accounting range
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    # Prepare dataframe
    df, df_tags, df_properties, df_comments = processing.get_transfers(start_date=dmin, end_date=dmax, value="price")

    # Apply selection
    mask = df["category"].notnull()
    df = df[mask]
    categories = list(df["category"].unique())
    accounts = list(df["account"].unique())

    df["year"] = df["date"].apply(lambda x: x.year)
    df["month"] = df["date"].apply(lambda x: x.month)
    df = df.groupby(["year", "month", "account", "category"]).agg(
        total=pandas.NamedAgg(column="price", aggfunc="sum")
    ).reset_index()
    df["date"] = df['year'].astype(str) + "-" + df['month'].astype(str)
    df["date"] = pandas.to_datetime(df["date"], format="%Y-%m")

    df_monthly = pandas.DataFrame()
    for i, a in enumerate(accounts):
        acc = accounts[i]
        n = (dmax.year - dmin.year) * 12 + dmax.month - dmin.month
        dfm = pandas.DataFrame({
            "date": [dmin + relativedelta(months=i) for i in range(n + 1)],
        })
        dfm["account"] = acc
        dfm["category"] = processing.get_account_category(acc)
        dfm["total"] = Decimal(0.0)
        mask_r = df["account"] == acc
        mask_l = dfm["date"].isin(df[mask_r]["date"])
        dfm.loc[mask_l, "total"] = df.loc[mask_r, "total"].values
        df_monthly = pandas.concat([df_monthly, dfm])
    df = df_monthly

    return df.to_dict(orient="records")


# History graph
@callback(
    Output("analytics_history_graph", "figure"),
    Input('analytics_monthly', 'data'),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value")
)
def display_history(analytics_monthly, month_start, month_end):
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


# Averages graph
@callback(
    Output("monthly_breakdown_categories", "children"),
    Input('analytics_monthly', 'data'),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value")
)
def display_category(analytics_monthly, month_start, month_end):
    if not analytics_monthly:
        return []

    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    dfm = pandas.DataFrame(analytics_monthly)
    dfm["date"] = pandas.to_datetime(dfm["date"])

    children = []
    categories = list(dfm["category"].unique())
    n_cat = len(categories)
    n_col = 3
    n_row = (n_cat - 1) // n_col + 1
    n = n_col * n_row
    categories += [None] * (n - len(categories))
    matrix = numpy.array(categories).reshape(-1, n_col)
    for j in range(n_col):
        col = []
        for i in range(n_row):
            cat = matrix[i, j]
            df = dfm[dfm["category"] == cat].copy()
            for acc, group in df.groupby(["account"]):
                df.loc[df["account"] == acc[0], "total"] = group["total"].cumsum().values

            # Generate figure
            fig = px.area(df, x="date", y="total", color="account")

            fig.update_xaxes(range=[dmin - timedelta(days=30),
                                    dmax + timedelta(days=30)])
            fig.update_xaxes(title_text="Month")
            fig.update_yaxes(title_text="Total")

            col.append(dbc.Row([html.H4(cat), dcc.Graph(figure=fig)]))
        children.append(dbc.Col(col))

    return children
