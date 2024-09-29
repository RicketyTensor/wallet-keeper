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


def make_month_selector():
    t0, t1 = processing.get_time_span()
    month_list = [i.strftime("%m/%Y") for i in pandas.date_range(start=t0, end=t1, freq='SMS', inclusive="both")]

    selector = dbc.Row(children=[
        dcc.Dropdown(
            month_list, month_list[0],
            id="select_month_range_start",
            placeholder="Start MM/YYYY",
            clearable=False,
            persistence=True
        ),
        dcc.Dropdown(
            month_list, month_list[-1],
            id="select_month_range_end",
            placeholder="End MM/YYYY",
            clearable=False,
            persistence=True
        )
    ])

    return html.Div([html.H5("Select month range:"), selector])


# Dataframe for monthly analytics
@callback(
    Output('data_monthly', 'data'),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value"),
)
def filter_dataframe_monthly(month_start, month_end):
    # Apply accounting range
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    # Prepare dataframe
    df, df_tags, df_properties, df_comments = processing.get_transfers(start_date=dmin, end_date=dmax)

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


# Dataframe for monthly analytics
@callback(
    Output('data_totals', 'data'),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value"),
)
def filter_dataframe_totals(month_start, month_end):
    # Apply accounting range
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    # Prepare dataframe
    df = processing.get_account_totals(start_date=dmin, end_date=dmax, hierarchy=True)

    return df.to_dict(orient="records")
