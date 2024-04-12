import dash
from dash import dcc, html, Input, Output, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import datetime
import calendar
from dateutil.relativedelta import relativedelta
import pandas
from pages.preprocessing import df_transactions, accounts

dash.register_page(__name__, order=3)


def make_account_selector(identifier):
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


selector_plus = dbc.Row([
    html.Div("Add:"),
    make_account_selector("selector_plus")
])

selector_minus = dbc.Row([
    html.Div("Deduct:"),
    make_account_selector("selector_minus")
])


# Range slider for accounting
def get_first_and_last_day(t0, t1):
    d0 = t0.replace(day=1)
    r1 = calendar.monthrange(t1.year, t1.month)
    d1 = t1.replace(day=r1[1])
    return d0, d1


t0 = df_transactions["date"].min()
t1 = df_transactions["date"].max()
d0, d1 = get_first_and_last_day(t0, t1)
max_range = (d1.year - d0.year) * 12 + d1.month - d0.month
points = range(0, max_range + 1)
accounting_range = dbc.Row([
    html.Div("Accounting period:"),
    dcc.RangeSlider(min=points[0],
                    max=points[-1],
                    step=1,
                    value=[points[0], points[-1]],
                    id='analytics_range_slider',
                    marks={p: (d0 + relativedelta(months=p)).strftime("%m/%y")
                           for p in points},
                    allowCross=False
                    )
])

# Layout
# ======
layout = dbc.Container(
    children=[
        dcc.Store(id='analytics_monthly'),
        dbc.Col(children=[
            dbc.Row([
                dbc.Col([selector_plus]),
                dbc.Col([selector_minus]),
            ]),
            accounting_range,
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
    Input("selector_plus", "derived_virtual_selected_rows"),
    Input("selector_minus", "derived_virtual_selected_rows"),
    Input("analytics_range_slider", "value")
)
def filter_dataframe_monthly(plus, minus, month_range):
    if not plus and not minus:
        return pandas.DataFrame().to_dict(orient="records")

    # Apply accounting range
    dmin = d0 + relativedelta(months=month_range[0])
    dmax = d0 + relativedelta(months=month_range[1])

    # Prepare dataframe
    df = df_transactions.copy()

    # Apply range
    df = df[df["date"].between(dmin, dmax, inclusive="both")].copy().reset_index()

    # Apply summation
    df_temp = pandas.DataFrame()
    if plus:
        mask = df["account"].isin([accounts[i] for i in plus])
        df_temp = pandas.concat([df_temp, df[mask]])
    if minus:
        mask = df["account"].isin([accounts[i] for i in minus])
        df.loc[mask, "amount"] *= -1
        df_temp = pandas.concat([df_temp, df[mask]])
    df = df_temp

    # Collapse months
    df = df.groupby(["year", "month"]).agg(
        total=pandas.NamedAgg(column="amount", aggfunc="sum")
    ).reset_index()
    df["date"] = df['year'].astype(str) + "-" + df['month'].astype(str)
    df["date"] = pandas.to_datetime(df["date"], format="%Y-%m")
    df['total'] = df['total'].round(decimals=2)

    n = (dmax.year - dmin.year) * 12 + dmax.month - dmin.month
    df_monthly = pandas.DataFrame({"date": [dmin + relativedelta(months=i) for i in range(n + 1)],
                                   })
    df_monthly["year"] = df_monthly["date"].apply(lambda x: x.year)
    df_monthly["month"] = df_monthly["date"].apply(lambda x: x.month)
    df_monthly["total"] = 0.0
    df_monthly.loc[df_monthly["date"].isin(df["date"]), "total"] = df["total"].values

    return df_monthly.to_dict(orient='records')


# History graph
@callback(
    Output("analytics_history_graph", "figure"),
    Input('analytics_monthly', 'data'),
    Input("analytics_range_slider", "value")
)
def display_history(analytics_monthly, month_range):
    if not analytics_monthly:
        return go.Figure()

    dmin = d0 + relativedelta(months=month_range[0])
    dmax = d0 + relativedelta(months=month_range[1])

    dfm = pandas.DataFrame(analytics_monthly)
    dfm["date"] = pandas.to_datetime(dfm["date"])

    # Generate figure
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=dfm["date"],
            y=dfm["total"]
        )
    )

    fig.update_xaxes(range=[dmin - datetime.timedelta(days=30),
                            dmax + datetime.timedelta(days=30)])
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Total")
    return fig


# Averages graph
@callback(
    Output("analytics_averages_graph", "figure"),
    Input('analytics_monthly', 'data'),
    Input("analytics_range_slider", "value"),
    Input("selector_plus", "derived_virtual_selected_rows"),
    Input("selector_minus", "derived_virtual_selected_rows"),
)
def display_averages(data, month_range, plus, minus):
    if not data:
        return go.Figure()

    df = pandas.DataFrame(data)
    df["date"] = pandas.to_datetime(df["date"])
    dmin = d0 + relativedelta(months=month_range[0])
    dmax = d0 + relativedelta(months=month_range[1])

    # Generate figure
    fig = go.Figure()

    # Overall
    fig.add_trace(
        go.Box(y=df["total"], name="Overall", boxpoints='all')
    )

    # Last two year
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
    df = df_transactions.copy()
    dmax = df.date.max()
    dmin = dmax - relativedelta(months=1)
    df = df[(df.date.between(dmin, dmax, inclusive="both"))]
    df_temp = pandas.DataFrame()
    if plus:
        mask = df["account"].isin([accounts[i] for i in plus])
        df_temp = pandas.concat([df_temp, df[mask]])
    if minus:
        mask = df["account"].isin([accounts[i] for i in minus])
        df.loc[mask, "amount"] *= -1
        df_temp = pandas.concat([df_temp, df[mask]])
    y = df_temp["amount"].sum().round(decimals=2)

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
