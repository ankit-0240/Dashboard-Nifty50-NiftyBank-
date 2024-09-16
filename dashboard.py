import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
import numpy as np


def download_and_process_data(ticker: str):
    data = yf.download(ticker, start="2019-04-01", end="2025-03-31", interval="1d")
    data["Month-Day"] = data.index.strftime("%m-%d")
    data["Normalized Date"] = pd.to_datetime(
        "1900-" + data["Month-Day"], format="%Y-%m-%d", errors="coerce"
    ).map(lambda d: d.replace(year=1901) if d.month < 4 else d)
    del data["Month-Day"]
    data["Fiscal Year"] = np.where(data.index.month >= 4, data.index.year, data.index.year - 1)
    return data


def create_plot(data, title):
    fig = go.Figure()
    for year, grp in data.groupby("Fiscal Year"):
        fig.add_trace(
            go.Scatter(
                x=grp["Normalized Date"],
                y=grp["Close"],
                mode="lines+markers",
                name=f"FY {year}-{year+1}",
            ),
        )
    start_padding = pd.Timestamp("1900-03-29")
    end_padding = pd.Timestamp("1901-04-03")
    fig.update_layout(
        title=title,
        xaxis_title="Month",
        yaxis_title="Closing Price (INR)",
        xaxis=dict(
            tickformat="%b",
            tickvals=pd.date_range("1900-04-01", "1901-03-31", freq="MS"),
            range=[start_padding, end_padding],
        ),
        hovermode="x unified",
        template="plotly_dark",
        legend_title="Year",
    )
    fig.update_traces(
        hovertemplate="<br /><b>Date:</b> %{x|%d}<br />"
        + "<b>Closing Price:</b> %{y}<br />",
    )
    return fig


nifty50_df = yf.download('^NSEI', start='2021-09-01', end='2050-09-01', interval='1d')
niftybank_df = yf.download('^NSEBANK', start='2021-09-01', end='2050-09-01', interval='1d')

nifty50_df.reset_index(inplace=True)
niftybank_df.reset_index(inplace=True)

nifty50_df['Weekday'] = nifty50_df['Date'].dt.day_name()
niftybank_df['Weekday'] = niftybank_df['Date'].dt.day_name()


st.sidebar.title('Stock Analysis Dashboard')


analysis_option = st.sidebar.radio(
    'Select Analysis Type',
    ('Weekly Candlestick Chart', 'Hourly Candlestick Chart', 'Yearly Candlestick Chart')
)


if analysis_option == 'Weekly Candlestick Chart':
    option = st.sidebar.selectbox('Select the index', ('Nifty 50', 'Nifty Bank'))
    st.sidebar.title('Select Date')
    start_date = st.sidebar.date_input('Start date', min(nifty50_df['Date'].min(), niftybank_df['Date'].min()))
    end_date = st.sidebar.date_input('End date', max(nifty50_df['Date'].max(), niftybank_df['Date'].max()))

    if option == 'Nifty 50':
        df = nifty50_df[(nifty50_df['Date'] >= pd.Timestamp(start_date)) & (nifty50_df['Date'] <= pd.Timestamp(end_date))]
    else:
        df = niftybank_df[(niftybank_df['Date'] >= pd.Timestamp(start_date)) & (niftybank_df['Date'] <= pd.Timestamp(end_date))]

    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    selected_days = st.sidebar.multiselect('Select Days', days_order, default=days_order)

    for day in selected_days:
        day_data = df[df['Weekday'] == day]
        baseline = [0] * len(day_data)

        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=day_data['Date'],
            open=day_data['Open'] - day_data['Open'],
            high=day_data['High'] - day_data['Open'],
            low=day_data['Low'] - day_data['Open'],
            close=day_data['Close'] - day_data['Open'],
            name=f'Candlestick ({day})',
            increasing_line_color='green',
            decreasing_line_color='red'
        ))

        fig.add_trace(go.Scatter(
            x=day_data['Date'],
            y=baseline,
            mode='lines',
            line=dict(color='gray', dash='dash'),
            name='Baseline'
        ))

        fig.update_layout(
            title=f'Candlestick Chart for {day} - {option}',
            xaxis_title='Date',
            yaxis_title=f'{day}',
            xaxis_rangeslider_visible=False,
            template='plotly_dark',
            yaxis=dict(showgrid=True, zeroline=True)
        )

        st.plotly_chart(fig)


elif analysis_option == 'Hourly Candlestick Chart':
    st.sidebar.title('Stock Analysis Hourly Basis')
    index_options = {'Nifty50': '^NSEI', 'NiftyBank': '^NSEBANK'}
    ticker_option = st.sidebar.selectbox('Select Index', list(index_options.keys()))
    ticker = index_options[ticker_option]

    start_date = st.sidebar.date_input('Start Date', pd.to_datetime('2024-01-01'))
    end_date = st.sidebar.date_input('End Date', pd.to_datetime('2025-12-01'))

    df = yf.download(ticker, start=start_date, end=end_date, interval='1h')

    df.reset_index(inplace=True)
    df = df[(df['Datetime'].dt.time >= pd.to_datetime('09:00').time()) & 
            (df['Datetime'].dt.time <= pd.to_datetime('15:30').time())]

    df['Time'] = df['Datetime'].dt.time
    unique_dates = df['Datetime'].dt.date.unique()
    baseline_shift = pd.Series(index=unique_dates, data=[i * 500 for i in range(len(unique_dates))])
    df['Baseline'] = df['Datetime'].dt.date.map(baseline_shift)

    fig = go.Figure()

    for date in unique_dates:
        day_data = df[df['Datetime'].dt.date == date]
        baseline = baseline_shift[date]

        open_shifted = day_data['Open'] - day_data['Open'] + baseline
        high_shifted = day_data['High'] - day_data['Open'] + baseline
        low_shifted = day_data['Low'] - day_data['Open'] + baseline
        close_shifted = day_data['Close'] - day_data['Open'] + baseline

        fig.add_trace(go.Candlestick(
            x=day_data['Time'],  
            open=open_shifted,
            high=high_shifted,
            low=low_shifted,
            close=close_shifted,
            name=f'{date} Candlestick',
            increasing_line_color='green',
            decreasing_line_color='red'
        ))

        fig.add_trace(go.Scatter(
            x=[day_data['Time'].min(), day_data['Time'].max()],
            y=[baseline, baseline],
            mode='lines',
            line=dict(color='gray', dash='dash'),
            name=f'{date} Baseline'
        ))

    fig.update_layout(
        title=f'Candlestick Chart ({ticker_option})',
        xaxis_title='Time',
        yaxis_title='Date',
        template='plotly_dark',
        xaxis_rangeslider_visible=False,  
        height=1500,  
        yaxis=dict(
            tickmode='array',
            tickvals=[baseline_shift[date] for date in unique_dates],  
            ticktext=[str(date) for date in unique_dates],  
            showgrid=True,
            zeroline=False
        ),
        xaxis=dict(
            type='category',  
            tickmode='auto',
            tickformat='%H:%M',  
            showgrid=True,
            zeroline=False
        )
    )

    st.plotly_chart(fig)


elif analysis_option == 'Yearly Candlestick Chart':
    st.sidebar.title('Stock Analysis Yearly Basis')
    index_options = {'Nifty50': '^NSEI', 'NiftyBank': '^NSEBANK'}
    ticker_option = st.sidebar.selectbox('Select Index', list(index_options.keys()))

    if ticker_option == "Nifty50":
        data = download_and_process_data("^NSEI")
        title = "Nifty50 Closing Prices Comparison by Year"
    else:
        data = download_and_process_data("^NSEBANK")
        title = "Nifty Bank Closing Prices Comparison by Year"

    start_date = st.sidebar.date_input("Select start date", pd.Timestamp("2019-04-01"))
    end_date = st.sidebar.date_input("Select end date", pd.Timestamp("2025-03-31"))

    filtered_data = data[(data.index >= pd.Timestamp(start_date)) & (data.index <= pd.Timestamp(end_date))]

    fig = create_plot(filtered_data, title)
    st.plotly_chart(fig)
