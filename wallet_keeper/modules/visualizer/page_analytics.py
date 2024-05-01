import dash
from dash import dcc, html, Input, Output, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar
from dateutil.relativedelta import relativedelta
import pandas
from wallet_keeper.modules.visualizer import processing
from decimal import Decimal

dash.register_page(__name__, order=3, name="Analytics")


def make_account_selector(identifier):
    accounts = processing.get_accounts()

    selector = dcc.Dropdown(
        accounts,
        id=identifier,
        placeholder="Select an account",
    )
    return html.Div([html.H5("Select accounts:"), selector])


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


selector_plus = dbc.Row([
    html.Div("Add:"),
    make_account_selector("selector_plus")
])

# Layout
# ======
layout = dbc.Container(
    children=[
        dcc.Store(id='analytics_monthly'),
        dbc.Col(children=[
            dbc.Row([
                dbc.Col([selector_plus]),
            ]),
            make_month_selector(),
            html.H4("Monthly development"),
            dbc.Row([
                dbc.Col([dcc.Graph(id="analytics_history_graph")]),
                dbc.Col([dcc.Graph(id="analytics_averages_graph")]),
            ])

        ])
    ],
    fluid=True
)


# Dataframe for monthly analytics
@callback(
    Output('analytics_monthly', 'data'),
    Input("selector_plus", "value"),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value")
)
def filter_dataframe_monthly(plus, month_start, month_end):
    if not plus:
        return pandas.DataFrame().to_dict(orient="records")

    # Apply accounting range
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    # Prepare dataframe
    accounts = processing.get_accounts()
    df, df_tags, df_properties, df_comments = processing.get_transfers()

    # Apply range
    df = df[df["date"].between(dmin, dmax, inclusive="both")].copy().reset_index()

    # Apply summation
    df_temp = pandas.DataFrame()
    if plus:
        mask = df.account.isin(plus) if isinstance(plus, list) else df.account.isin([plus])
        df_temp = pandas.concat([df_temp, df[mask]])
    df = df_temp

    # Collapse months
    df = df.groupby(["year", "month"]).agg(
        total=pandas.NamedAgg(column="amount", aggfunc="sum")
    ).reset_index()
    df["date"] = df['year'].astype(str) + "-" + df['month'].astype(str)
    df["date"] = pandas.to_datetime(df["date"], format="%Y-%m")

    n = (dmax.year - dmin.year) * 12 + dmax.month - dmin.month
    df_monthly = pandas.DataFrame({"date": [dmin + relativedelta(months=i) for i in range(n + 1)],
                                   })
    df_monthly["year"] = df_monthly["date"].apply(lambda x: x.year)
    df_monthly["month"] = df_monthly["date"].apply(lambda x: x.month)
    df_monthly["total"] = Decimal(0.0)
    df_monthly.loc[df_monthly["date"].isin(df["date"]), "total"] = df["total"].values

    return df_monthly.to_dict(orient='records')


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

    # Generate figure
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=dfm["date"].dt.strftime("%m / %Y"),
            y=dfm["total"]
        )
    )

    fig.update_xaxes(range=[dmin - timedelta(days=30),
                            dmax + timedelta(days=30)])
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Total")
    return fig


# Averages graph
@callback(
    Output("analytics_averages_graph", "figure"),
    Input('analytics_monthly', 'data'),
    Input("select_month_range_start", "value"),
    Input("select_month_range_end", "value"),
    Input("selector_plus", "value"),
)
def display_averages(data, month_start, month_end, plus):
    if not data:
        return go.Figure()

    df = pandas.DataFrame(data)
    df["date"] = pandas.to_datetime(df["date"])
    dmin = datetime.strptime(month_start, "%m/%Y")
    dmax = datetime.strptime(month_end, "%m/%Y") + relativedelta(months=1) - timedelta(days=1)

    # Generate figure
    fig = go.Figure()

    # Overall
    fig.add_trace(
        go.Box(y=df["total"], name="Overall", boxpoints='all')
    )

    # Last two years
    dmax = df.date.max()
    dmin = dmax - relativedelta(months=23)
    df = df[(df.date.between(dmin, dmax, inclusive="both"))]

    fig.add_trace(
        go.Box(y=df["total"], name="Last 2 years", boxpoints='all')
    )

    # Last year
    dmax = df.date.max()
    dmin = dmax - relativedelta(months=11)
    df = df[(df.date.between(dmin, dmax, inclusive="both"))]

    fig.add_trace(
        go.Box(y=df["total"], name="Last year", boxpoints='all')
    )

    # Last quarter
    dmax = df.date.max()
    dmin = dmax - relativedelta(months=3)
    df = df[(df.date.between(dmin, dmax, inclusive="both"))]

    fig.add_trace(
        go.Box(y=df["total"], name="Last quarter", boxpoints='all')
    )

    # This month
    accounts = processing.get_accounts()
    df, df_tags, df_properties, df_comments = processing.get_transfers()
    dmax = df.date.max()
    dmin = dmax - relativedelta(months=1)
    df = df[(df.date.between(dmin, dmax, inclusive="both"))]
    df_temp = pandas.DataFrame()
    if plus:
        mask = df.account.isin(plus) if isinstance(plus, list) else df.account.isin([plus])
        df_temp = pandas.concat([df_temp, df[mask]])
    y = df_temp["amount"].sum()

    fig.add_hline(
        y=y,
        line_dash="dot",
        label=dict(
            text="Last 30 days",
            textposition="end",
            font=dict(size=20, color="white"),
            yanchor="top",
        ),
    )

    fig.update_yaxes(title_text="Monthly averages")
    return fig
