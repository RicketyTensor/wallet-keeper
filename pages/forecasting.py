import dash
from dash import dcc, html, Input, Output, callback, MATCH
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy
import pandas
from pages.dataframes import df_transactions, accounts
from dateutil import parser
from dateutil.relativedelta import relativedelta
import statsmodels.stats.api as sms
from statsmodels.tsa.ar_model import AutoReg
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.filters.cf_filter import cffilter

dash.register_page(__name__, order=5)


def forecast_settings():
    return html.Div(children=[
        html.H5("Sampling range"),
        dcc.DatePickerRange(
            id="forcast_sampling_range",
            min_date_allowed=df_transactions.date.min(),
            max_date_allowed=df_transactions.date.max(),
            initial_visible_month=df_transactions.date.max(),
            start_date=df_transactions.date.min(),
            end_date=df_transactions.date.max()
        ),
        html.H5("Sampling rate"),
        dbc.RadioItems(
            id="forecast_sampling_rate",
            options=[
                {"label": "Daily", "value": 1},
                {"label": "Monthly", "value": 2},
                {"label": "Quarterly", "value": 3},
            ],
            value=2,
        ),
        html.H5("Forecast method"),
        dbc.RadioItems(
            id="forecast_method",
            options=[
                {"label": "Stupid", "value": 1},
                {"label": "Autoregression", "value": 2},
                {"label": "Moving Average", "value": 3},
            ],
            value=2,
        ),
    ])


layout = dbc.Container(
    [
        dcc.Store(id='data_history'),
        dcc.Store(id='data_samples'),
        dcc.Store(id='data_filtered'),
        dcc.Store(id='data_forecast'),
        dbc.Row([
            # Account selector
            dbc.Col(children=[
                dcc.Dropdown(
                    id="acc_selector",
                    options=accounts,
                    value=["Assets"],
                    multi=True,
                    persistence=True
                ),
                forecast_settings()
            ], width={"size": 3}),
            # Accounting
            dbc.Col([
                html.Div(id="forecast_div", children=[])
            ])
        ])
    ],
    fluid=True
)


@callback(
    Output("forecast_div", "children"),
    Input("acc_selector", "value"),
)
def display_forecast(selected):
    patched_children = []

    if selected:
        for acc in selected:
            patched_children.append(
                dbc.Row(children=[
                    dbc.Col([dcc.Graph(id={"type": "forecast_sampling", "index": acc})]),
                    dbc.Col([dcc.Graph(id={"type": "forecast_graph", "index": acc})])
                ])
            )

    return patched_children


@callback(
    Output('data_history', 'data'),
    Input("forecast_sampling_rate", "value"),
)
def filter_data_history(rate):
    # Prepare dataframe
    df = df_transactions.copy()
    dmin = df.date.min()
    dmax = df.date.max()

    # Extend dataframe to include all entries in the forecasting range
    match rate:
        case 1:
            # Collapse months
            df = df.groupby(["date", "account"]).agg(
                total=pandas.NamedAgg(column="amount", aggfunc="sum")
            ).reset_index()

            # Make a filler dataframe
            pmin = dmin
            pmax = dmax
            n = (pmax - pmin).days
            df_filler = pandas.DataFrame({"date": [pmin + relativedelta(days=i) for i in range(n + 1)]})
        case 2:
            # Collapse months
            df = df.groupby(["year", "month", "account"]).agg(
                total=pandas.NamedAgg(column="amount", aggfunc="sum")
            ).reset_index()
            df["date"] = df.apply(lambda x: datetime(x.year, x.month, 1) + relativedelta(day=99), axis=1)
            df["date"] = pandas.to_datetime(df["date"])

            # Make a filler dataframe
            pmin = dmin.replace(day=1)
            pmax = dmax + relativedelta(day=99)
            n = (pmax.year - pmin.year) * 12 + dmax.month - dmin.month
            df_filler = pandas.DataFrame({"date": [pmin + relativedelta(months=i, day=99) for i in range(n + 1)]})
        case 3:
            # Collapse months
            df = df.groupby(["year", "quarter", "account"]).agg(
                total=pandas.NamedAgg(column="amount", aggfunc="sum")
            ).reset_index()
            df["date"] = df.apply(lambda x: datetime(x.year, x.quarter * 3, 1) + relativedelta(day=99), axis=1)
            df["date"] = pandas.to_datetime(df["date"])

            # Make a filler dataframe
            quarter = pandas.Timestamp(dmin).quarter
            pmin = datetime(dmin.year, 1, 1) + relativedelta(months=3 * quarter, days=-1)
            pmax = dmax + relativedelta(day=99)
            n = (pmax.year - pmin.year) * 4 + pandas.Timestamp(pmax).quarter - pandas.Timestamp(pmin).quarter
            df_filler = pandas.DataFrame({"date": [pmin + relativedelta(months=i * 3, day=99) for i in range(n + 1)]})
        case _:
            raise ValueError("Unknown option from forecast sampling rate radio buttons!")

    df_filler["total"] = 0.0

    # Pad the original dataframe
    df_complete = pandas.DataFrame()
    for a in df.account.unique():
        mask = df.account == a
        df_temp = df_filler.copy()
        df_temp.loc[df_temp["date"].isin(df.loc[mask, "date"]), "total"] = df.loc[mask, "total"].values
        df_temp["account"] = a
        df_complete = pandas.concat([df_complete, df_temp])

    return df_complete.round(decimals=2).to_dict(orient='records')


@callback(
    Output('data_samples', 'data'),
    Input("data_history", "data"),
    Input('forcast_sampling_range', 'start_date'),
    Input('forcast_sampling_range', 'end_date'),
)
def filter_data_samples(data_history, start_date, end_date):
    # Prepare dataframe
    dfh = pandas.DataFrame(data_history)
    dfh["date"] = pandas.to_datetime(dfh["date"])

    # Apply range
    dmin = parser.parse(start_date).replace(day=1)
    dmax = parser.parse(end_date)
    df = dfh[dfh["date"].between(dmin, dmax, inclusive="both")].copy().reset_index()

    return df.round(decimals=2).to_dict(orient='records')


@callback(
    Output('data_filtered', 'data'),
    Input("data_samples", "data"),
    Input("forecast_sampling_rate", "value"),
)
def filter_data_filtered(data_history, rate):
    # Prepare dataframe
    df = pandas.DataFrame(data_history)
    df["date"] = pandas.to_datetime(df["date"])

    dfg = df.groupby(["account"])
    for n, g in dfg:
        cf_cycles, cf_trend = cffilter(g.total)
        df.loc[df.account == n[0], "cycle"] = cf_cycles.values

    return df.round(decimals=2).to_dict(orient='records')


@callback(
    Output('data_forecast', 'data'),
    Input("data_filtered", "data"),
    Input("forecast_method", "value"),
    Input("forecast_sampling_rate", "value"),
)
def filter_data_forecast(data_filtered, method, rate):
    # Prepare dataframe
    df = pandas.DataFrame(data_filtered)
    df["date"] = pandas.to_datetime(df["date"])
    dff = df

    match rate:
        case 1:
            n = ((df["date"].max() + relativedelta(years=1)) - df["date"].max()).days
            dates = [df["date"].max() + relativedelta(days=i) for i in range(n + 1)]
        case 2:
            n = 12
            dates = [df["date"].max() + relativedelta(months=i) for i in range(n + 1)]
        case 3:
            n = 4
            dates = [df["date"].max() + relativedelta(months=i * 3) for i in range(n + 1)]
        case _:
            raise ValueError("Unknown option from forecast sampling rate radio buttons!")

    df = pandas.DataFrame()

    dfg = dff.groupby(["account"])
    for n, g in dfg:
        acc = n[0]

        if method == 1:
            x, y, yl, yu = forecast_stupid(g.total.values, dates)  # Stupid method
        elif method == 2:
            x, y, yl, yu = forecast_ar(g.total.values, dates)  # Autoregression
        elif method == 3:
            x, y, yl, yu = forecast_arma(g.total.values, dates)  # Autoregression
        else:
            raise ValueError("The selected forecast method is not supported yet!")

        df_temp = pandas.DataFrame({"date": dates})
        df_temp.loc[:, "mid"] = y
        df_temp.loc[:, "lower"] = yl
        df_temp.loc[:, "upper"] = yu
        df_temp.loc[:, "account"] = acc
        df = pandas.concat([df, df_temp])

    return df.round(decimals=2).to_dict(orient='records')


def forecast_stupid(values, dates):
    # Train model
    model = sms.DescrStatsW(values)
    m = model.mean
    cl, cu = model.tconfint_mean()
    y = numpy.array([m * i for i in range(len(dates))])
    yl = numpy.array([cl * i for i in range(len(dates))])
    yu = numpy.array([cu * i for i in range(len(dates))])

    return dates, y, yl, yu


def forecast_ar(values, dates):
    # Train model
    model = AutoReg(values, lags=1, trend="ct")
    model_fit = model.fit()
    prediction = model_fit.get_prediction(start=len(values), end=len(values) + len(dates) - 1)

    return dates, prediction.predicted_mean, *prediction.conf_int().T


def forecast_arma(values, dates):
    # Train model
    model = ARIMA(values, order=(2, 0, 1), trend="ct")
    model_fit = model.fit()
    prediction = model_fit.get_prediction(start=len(values), end=len(values) + len(dates) - 1)

    return dates, prediction.predicted_mean, *prediction.conf_int().T


# Forecast graph
@callback(
    Output({"type": "forecast_graph", "index": MATCH}, "figure"),
    Input('data_history', 'data'),
    Input('data_samples', 'data'),
    Input('data_forecast', 'data'),
    Input("forecast_sampling_rate", "value"),
    Input('forcast_sampling_range', 'start_date'),
    Input('forcast_sampling_range', 'end_date')
)
def display_forecast_graph(data_history, data_samples, data_forecast, rate, start_date, end_date):
    idx = dash.callback_context.outputs_list['id']['index']  # get id of current callback

    # Generate figure
    fig = go.Figure()

    # Graph of Actuals
    # ================
    df = pandas.DataFrame(data_history)
    df["date"] = pandas.to_datetime(df["date"])
    df = df[df.account == idx].copy()
    df["cumsum"] = df["total"].cumsum()
    dfh = df

    fig.add_trace(
        go.Scatter(
            x=dfh["date"],
            y=dfh["cumsum"],
            name="Actuals"
        )
    )

    # Graph of training set
    # =====================
    df = pandas.DataFrame(data_samples)
    df["date"] = pandas.to_datetime(df["date"])
    df = df[df.account == idx].copy()
    df["cumsum"] = df["total"].cumsum()
    dfs = df

    fig.add_trace(
        go.Scatter(
            x=dfs["date"],
            y=dfs["cumsum"],
            name="Training set"
        )
    )

    # Graph of forecast
    # =================
    df = pandas.DataFrame(data_forecast)
    df["date"] = pandas.to_datetime(df["date"])
    df = df[df.account == idx].copy()
    df["cs_mid"] = df["mid"].cumsum()
    df["cs_lower"] = df["lower"].cumsum()
    df["cs_upper"] = df["upper"].cumsum()
    dff = df

    color = px.colors.qualitative.Plotly[1]
    fill_color = [int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]

    fig.add_trace(
        go.Scatter(
            x=numpy.append(dff.date, dff.date[::-1]),
            y=numpy.append(dff.cs_lower, dff.cs_upper[::-1]),
            line_color="rgba({},{},{},{})".format(*fill_color, 0.0),
            fillcolor="rgba({},{},{},{})".format(*fill_color, 0.2),
            fill="toself",
            showlegend=False,
            name="Forecast",
            # mode="lines"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dff.date,
            y=dff.cs_mid,
            name="Forecast",
            line_color="rgba({},{},{},{})".format(*fill_color, 1.0),
            mode="lines"
        )
    )

    # fig.update_xaxes(range=[dff["date"].min() - relativedelta(days=30),
    #                         max(dff["date"].max(), x[-1]) + relativedelta(days=30)])
    fig.update_layout(
        title=idx,
        xaxis_rangeslider_visible=True,
    )
    return fig


@callback(
    Output({"type": "forecast_sampling", "index": MATCH}, "figure"),
    Input('data_samples', 'data'),
    Input('data_filtered', 'data'),
    Input('forcast_sampling_range', 'start_date'),
    Input('forcast_sampling_range', 'end_date'),
)
def display_forecast_sampling(data_samples, data_filtered, start_date, end_date):
    idx = dash.callback_context.outputs_list['id']['index']  # get id of current callback

    # Prepare dataframes
    df = pandas.DataFrame(data_samples)
    df["date"] = pandas.to_datetime(df["date"])
    dfs = df[df.account == idx].copy()

    df = pandas.DataFrame(data_filtered)
    df["date"] = pandas.to_datetime(df["date"])
    dff = df[df.account == idx].copy()

    # Generate figure
    fig = go.Figure()

    # Compute predictions
    # ===================
    # Graph of training set
    fig.add_trace(
        go.Scatter(
            x=dfs.date,
            y=dfs.total,
            name="Samples"
        )
    )

    # Graph of training set
    fig.add_trace(
        go.Scatter(
            x=dff.date,
            y=dff.cycle,
            name="Filtered"
        )
    )

    return fig
