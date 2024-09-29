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
from wallet_keeper.modules.visualizer.common import make_month_selector
from decimal import Decimal

dash.register_page(__name__, order=4, name="Budgeting")


def make_account_selector(identifier):
    accounts = processing.get_accounts_w_budget()
    table = dash_table.DataTable(
        id=identifier,
        columns=[
            {"name": "Account",
             "id": "account",
             "deletable": False,
             "selectable": False}
        ],
        data=[{"account": " : ".join(a.split(":"))} for a in accounts],
        editable=False,
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        column_selectable=False,
        row_selectable="multi",
        persistence=True,
        row_deletable=False,
        selected_columns=[],
        selected_rows=[],
        page_action="none",
        # page_current=0,
        # page_size=40,
        style_cell={'textAlign': 'left'},
        style_as_list_view=True,
        fixed_rows={'headers': True},
        style_table={'minHeight': "700px", 'height': "700px", 'maxHeight': "700px",
                     "overflowY": "auto"},
    )
    return table

# Layout
# ======
layout = dbc.Container(
    children=[
        dcc.Store(id='budgeting_data'),
        dbc.Row(children=[
            dbc.Col(children=[
                make_account_selector("budgeting_selector_plus"),
                make_month_selector(),
            ], width=3),
            dbc.Col(children=[
                dcc.Graph(id="budgeting_history_graph"),
                dcc.Graph(id="budgeting_cumulative_graph"),
            ], width=9)
        ])

    ],
    fluid=True
)


# Dataframe for monthly analytics
@callback(
    Output('budgeting_data', 'data'),
    Input("budgeting_selector_plus", "derived_virtual_selected_rows"),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value"),
)
def filter_dataframe_monthly(plus, month_start, month_end):
    if not plus:
        return pandas.DataFrame().to_dict(orient="records")

    # Apply accounting range
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    # Prepare dataframe
    accounts = processing.get_accounts_w_budget()
    df, df_tags, df_properties, df_comments = processing.get_transfers(start_date=dmin, end_date=dmax)
    dfb_monthly, dfb_yearly = processing.get_budgets()
    dfb_monthly = dfb_monthly[["account", "price"]].rename(columns={"price": "monthly"})
    dfb_yearly = dfb_yearly[["account", "price"]].rename(columns={"price": "yearly"})
    dfb = pandas.merge(dfb_monthly, dfb_yearly, on="account", how="outer").fillna(0.0)

    # Apply selection
    if plus:
        mask = df["account"].isin([accounts[i] for i in plus])
        df = df[mask]

    df["year"] = df["date"].apply(lambda x: x.year)
    df["month"] = df["date"].apply(lambda x: x.month)
    df = df.groupby(["year", "month", "account"]).agg(
        total=pandas.NamedAgg(column="price", aggfunc="sum")
    ).reset_index()
    df["date"] = df['year'].astype(str) + "-" + df['month'].astype(str)
    df["date"] = pandas.to_datetime(df["date"], format="%Y-%m")

    df_monthly = pandas.DataFrame()
    for i in plus:
        acc = accounts[i]
        n = (dmax.year - dmin.year) * 12 + dmax.month - dmin.month
        dfm = pandas.DataFrame({
            "date": [dmin + relativedelta(months=i) for i in range(n + 1)],
        })
        dfm["account"] = acc
        dfm["total"] = Decimal(0.0)

        # Add budget
        dfm["budget"] = Decimal(dfb.loc[dfb["account"] == acc, "monthly"].values[0])
        r = Decimal(0.0)
        for i, row in dfm.iterrows():
            if i == 0:
                r = Decimal(dfb.loc[dfb["account"] == acc, "yearly"].values[0]) / 12
            elif row["date"].month == 1:
                r = Decimal(dfb.loc[dfb["account"] == acc, "yearly"].values[0]) / 12
            dfm.loc[i, "budget"] += r

        # Assign existing values
        mask_r = df["account"] == acc
        mask_l = dfm["date"].isin(df[mask_r]["date"])
        dfm.loc[mask_l, "total"] = df.loc[mask_r, "total"].values
        df_monthly = pandas.concat([df_monthly, dfm])
    df = df_monthly

    return df.to_dict(orient="records")


# History graph
@callback(
    Output("budgeting_history_graph", "figure"),
    Input('budgeting_data', 'data'),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value"),
)
def display_history(analytics_monthly, month_start, month_end):
    if not analytics_monthly:
        return go.Figure()

    # Apply accounting range
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    dfm = pandas.DataFrame(analytics_monthly)
    dfm["date"] = pandas.to_datetime(dfm["date"])

    # Generate figure
    fig = px.bar(dfm, x="date", y="total", color="account")

    # Add budget
    df = dfm.groupby(["date"]).sum().reset_index()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["budget"],
        name="Budget"
    ))

    fig.update_xaxes(range=[dmin - timedelta(days=30),
                            dmax + timedelta(days=30)])
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Total")
    return fig


# Cumulative graph
@callback(
    Output("budgeting_cumulative_graph", "figure"),
    Input('budgeting_data', 'data'),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value"),
)
def display_cumulative(analytics_monthly, month_start, month_end):
    if not analytics_monthly:
        return go.Figure()

    # Apply accounting range
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    dfm = pandas.DataFrame(analytics_monthly)
    dfm["date"] = pandas.to_datetime(dfm["date"])
    for acc, group in dfm.groupby(["account"]):
        dfm.loc[dfm["account"] == acc[0], "total"] = group["total"].cumsum().values

    # Generate figure
    fig = px.area(dfm, x="date", y="total", color="account")

    # Add budget
    df = dfm.groupby(["date"]).sum().reset_index()
    df["budget"] = df["budget"].cumsum()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["budget"],
        name="Budget"
    ))

    fig.update_xaxes(range=[dmin - timedelta(days=30),
                            dmax + timedelta(days=30)])
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Total")
    return fig
