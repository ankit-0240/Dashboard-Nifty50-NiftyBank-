import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
import numpy as np
from scipy.stats import linregress

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
    ('Weekly Candlestick Chart', 'Hourly Candlestick Chart', 'Yearly Candlestick Chart','Stock Beta and Percentage Change','yearly Stock Beta and Percentage Change')
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

elif analysis_option == 'Stock Beta and Percentage Change':
    
    stock_tickers = ['AARTIIND.NS', 'ABB.NS', 'ABBOTINDIA.NS', 'ABCAPITAL.NS', 'ABFRL.NS', 'ACC.NS', 'ADANIENT.NS',
                 'ADANIPORTS.NS', 'AMBUJACEM.NS', 'APOLLOHOSP.NS', 'APOLLOTYRE.NS', 'ASHOKLEY.NS', 'ASTRAL.NS',
                 'ATUL.NS', 'AUBANK.NS', 'AUROPHARMA.NS', 'BAJAJFINSV.NS', 'BAJFINANCE.NS', 'BALKRISIND.NS',
                 'BALRAMCHIN.NS', 'BANDHANBNK.NS', 'BANKBARODA.NS', 'BEL.NS', 'BHARATFORG.NS', 'BHARTIARTL.NS',
                 'BHEL.NS', 'BIOCON.NS', 'BOSCHLTD.NS', 'BPCL.NS', 'BRITANNIA.NS', 'BSOFT.NS', 'CANBK.NS',
                 'CHAMBLFERT.NS', 'CHOLAFIN.NS', 'CIPLA.NS', 'COALINDIA.NS', 'COFORGE.NS', 'CONCOR.NS',
                 'COROMANDEL.NS', 'CROMPTON.NS', 'CUB.NS', 'DABUR.NS', 'DALBHARAT.NS', 'DEEPAKNTR.NS', 'DLF.NS',
                 'EICHERMOT.NS', 'ESCORTS.NS', 'GAIL.NS', 'GLENMARK.NS', 'GMRINFRA.NS', 'GNFC.NS', 'GODREJCP.NS',
                 'GODREJPROP.NS', 'GRASIM.NS', 'GUJGASLTD.NS', 'HAL.NS', 'HDFCBANK.NS', 'HDFCLIFE.NS',
                 'HEROMOTOCO.NS', 'HINDPETRO.NS', 'HINDUNILVR.NS', 'ICICIBANK.NS', 'ICICIGI.NS', 'ICICIPRULI.NS',
                 'IDEA.NS', 'IDFC.NS', 'IDFCFIRSTB.NS', 'IEX.NS', 'INDHOTEL.NS', 'INDIACEM.NS', 'INDIAMART.NS',
                 'INDIGO.NS', 'INDUSINDBK.NS', 'INDUSTOWER.NS', 'IOC.NS', 'IPCALAB.NS', 'IRCTC.NS', 'ITC.NS',
                 'JINDALSTEL.NS', 'JKCEMENT.NS', 'JSWSTEEL.NS', 'JUBLFOOD.NS', 'KOTAKBANK.NS', 'LICHSGFIN.NS',
                 'LT.NS', 'LTF.NS', 'LTTS.NS', 'M&MFIN.NS', 'MANAPPURAM.NS', 'MARICO.NS', 'MARUTI.NS', 'MCX.NS',
                 'METROPOLIS.NS', 'MFSL.NS', 'MGL.NS', 'MOTHERSON.NS', 'MPHASIS.NS', 'NATIONALUM.NS', 'NAVINFLUOR.NS',
                 'NESTLEIND.NS', 'NMDC.NS', 'NTPC.NS', 'OBEROIRLTY.NS', 'ONGC.NS', 'PEL.NS', 'PETRONET.NS', 'PFC.NS',
                 'PIDILITIND.NS', 'PIIND.NS', 'PNB.NS', 'POLYCAB.NS', 'POWERGRID.NS', 'PVRINOX.NS', 'RAMCOCEM.NS',
                 'RBLBANK.NS', 'RECLTD.NS', 'RELIANCE.NS', 'SAIL.NS', 'SBICARD.NS', 'SBILIFE.NS', 'SBIN.NS',
                 'SHRIRAMFIN.NS', 'SRF.NS', 'SUNTV.NS', 'TATACHEM.NS', 'TATACOMM.NS', 'TATACONSUM.NS', 'TATAMOTORS.NS',
                 'TATAPOWER.NS', 'TATASTEEL.NS', 'TCS.NS', 'TORNTPHARM.NS', 'UBL.NS', 'ULTRACEMCO.NS', 'UPL.NS',
                 'VEDL.NS', 'VOLTAS.NS', 'ZYDUSLIFE.NS']

    market_ticker = '^NSEI'

    st.title("Stock Beta and Percentage Change")
    
    
    time_interval = st.sidebar.selectbox("Select Time Interval", ["Daily", "Weekly", "Monthly", "3 Months"])


    selected_stock = st.sidebar.selectbox("Select Stock", stock_tickers)
    start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
    end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2023-12-31"))
   

    st.write(f"Fetching data for {selected_stock} from {start_date} to {end_date}...")

    @st.cache_data(ttl=3600)  
    def fetch_stock_data(ticker, start, end, interval='1d'):
        return yf.download(ticker, start=start, end=end, interval=interval)['Adj Close']

    try:
        
        if time_interval == "Daily":
            stock_data = fetch_stock_data(selected_stock, start_date, end_date, interval='1d')
            market_data = fetch_stock_data(market_ticker, start_date, end_date, interval='1d')
            interval_label = 'Daily Percent Change'
            interval_data = stock_data.pct_change(fill_method=None) * 100

        elif time_interval == "Weekly":
            stock_data = fetch_stock_data(selected_stock, start_date, end_date, interval='1wk')
            market_data = fetch_stock_data(market_ticker, start_date, end_date, interval='1wk')
            interval_label = 'Weekly Percent Change'
            interval_data = stock_data.pct_change(fill_method=None) * 100

        elif time_interval == "Monthly":
            stock_data = fetch_stock_data(selected_stock, start_date, end_date, interval='1mo')
            market_data = fetch_stock_data(market_ticker, start_date, end_date, interval='1mo')
            interval_label = 'Monthly Percent Change'
            interval_data = stock_data.pct_change(fill_method=None) * 100

        elif time_interval == "3 Months":
            stock_data = fetch_stock_data(selected_stock, start_date, end_date, interval='3mo')
            market_data = fetch_stock_data(market_ticker, start_date, end_date, interval='3mo')
            interval_label = '3-Month Percent Change'
            interval_data = stock_data.pct_change(fill_method=None) * 100
            
        if stock_data.empty or market_data.empty:
            st.error("No data found for the selected date range. Please adjust the date range.")
            st.stop()

   
        market_returns = market_data.pct_change(fill_method=None) * 100
        covariance = (interval_data - interval_data.mean()) * (market_returns - market_returns.mean())
        variance = market_returns.var()
        beta = covariance / variance if variance != 0 else np.nan

        result_df = pd.DataFrame({
            'Date': stock_data.index,
            'Stock': selected_stock,
            interval_label: interval_data.values,
            'Beta': beta.values
        })

        st.write(f"Displaying {time_interval.lower()} data for {selected_stock}:")
        st.write(result_df)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        
if analysis_option == 'yearly Stock Beta and Percentage Change':

    stock_tickers = [
        'AARTIIND.NS', 'ABB.NS', 'ABBOTINDIA.NS', 'ABCAPITAL.NS', 'ABFRL.NS', 'ACC.NS',
        'ADANIENT.NS', 'ADANIPORTS.NS', 'AMBUJACEM.NS', 'APOLLOHOSP.NS', 'APOLLOTYRE.NS',
        'ASHOKLEY.NS', 'ASTRAL.NS', 'ATUL.NS', 'AUBANK.NS', 'AUROPHARMA.NS', 'BAJAJFINSV.NS',
        'BAJFINANCE.NS', 'BALKRISIND.NS', 'BALRAMCHIN.NS', 'BANDHANBNK.NS', 'BANKBARODA.NS',
        '^NSEBANK', 'BEL.NS', 'BHARATFORG.NS', 'BHARTIARTL.NS', 'BHEL.NS', 'BIOCON.NS',
        'BOSCHLTD.NS', 'BPCL.NS', 'BRITANNIA.NS', 'BSOFT.NS', 'CANBK.NS', 'CHAMBLFERT.NS',
        'CHOLAFIN.NS', 'CIPLA.NS', 'COALINDIA.NS', 'COFORGE.NS', 'CONCOR.NS', 'COROMANDEL.NS',
        'CROMPTON.NS', 'CUB.NS', 'DABUR.NS', 'DALBHARAT.NS', 'DEEPAKNTR.NS', 'DLF.NS',
        'EICHERMOT.NS', 'ESCORTS.NS', 'GAIL.NS', 'GLENMARK.NS', 'GMRINFRA.NS', 'GNFC.NS',
        'GODREJCP.NS', 'GODREJPROP.NS', 'GRASIM.NS', 'GUJGASLTD.NS', 'HAL.NS', 'HDFCBANK.NS',
        'HDFCLIFE.NS', 'HEROMOTOCO.NS', 'HINDPETRO.NS', 'HINDUNILVR.NS', 'ICICIBANK.NS',
        'ICICIGI.NS', 'ICICIPRULI.NS', 'IDEA.NS', 'IDFC.NS', 'IDFCFIRSTB.NS', 'IEX.NS',
        'INDHOTEL.NS', 'INDIACEM.NS', 'INDIAMART.NS', 'INDIGO.NS', 'INDUSINDBK.NS',
        'INDUSTOWER.NS', 'IOC.NS', 'IPCALAB.NS', 'IRCTC.NS', 'ITC.NS', 'JINDALSTEL.NS',
        'JKCEMENT.NS', 'JSWSTEEL.NS', 'JUBLFOOD.NS', 'KOTAKBANK.NS', 'LICHSGFIN.NS',
        'LT.NS', 'LTF.NS', 'LTTS.NS', 'M&MFIN.NS', 'MANAPPURAM.NS', 'MARICO.NS',
        'MARUTI.NS', 'MCX.NS', 'METROPOLIS.NS', 'MFSL.NS', 'MGL.NS', 'MOTHERSON.NS',
        'MPHASIS.NS', 'NATIONALUM.NS', 'NAVINFLUOR.NS', 'NESTLEIND.NS', 'NMDC.NS',
        'NTPC.NS', 'OBEROIRLTY.NS', 'ONGC.NS', 'PEL.NS', 'PETRONET.NS', 'PFC.NS',
        'PIDILITIND.NS', 'PIIND.NS', 'PNB.NS', 'POLYCAB.NS', 'POWERGRID.NS', 'PVRINOX.NS',
        'RAMCOCEM.NS', 'RBLBANK.NS', 'RECLTD.NS', 'RELIANCE.NS', 'SAIL.NS', 'SBICARD.NS',
        'SBILIFE.NS', 'SBIN.NS', 'SHRIRAMFIN.NS', 'SRF.NS', 'SUNTV.NS', 'TATACHEM.NS',
        'TATACOMM.NS', 'TATACONSUM.NS', 'TATAMOTORS.NS', 'TATAPOWER.NS', 'TATASTEEL.NS',
        'TCS.NS', 'TORNTPHARM.NS', 'UBL.NS', 'ULTRACEMCO.NS', 'UPL.NS', 'VEDL.NS',
        'VOLTAS.NS', 'ZYDUSLIFE.NS'
    ]


    market_ticker = '^NSEI'  

    st.title("Stock Beta and Yearly Percentage Change")


    selected_stocks = st.sidebar.multiselect("Select Stocks", stock_tickers)
    start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
    end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2028-12-31"))


    @st.cache_data(ttl=3600)
    def fetch_data(tickers, start, end):
        return yf.download(tickers + [market_ticker], start=start, end=end)['Adj Close']

    if selected_stocks:
        st.write(f"Fetching data for {', '.join(selected_stocks)} from {start_date} to {end_date}...")
        
        try:
            data = fetch_data(selected_stocks, start_date, end_date)
            
        
            returns = data.pct_change().dropna()

            def calculate_beta(stock_returns, market_returns):
                slope, _, _, _, _ = linregress(market_returns, stock_returns)
                return slope

            results = []

            for stock in selected_stocks:
                beta = calculate_beta(returns[stock], returns[market_ticker])
                percentage_change = (data[stock][-1] - data[stock][0]) / data[stock][0] * 100
                results.append({'ticker': stock, 'beta value': beta, 'percentage_change': percentage_change})

    
            df = pd.DataFrame(results)

    
            df_sorted = df.sort_values(by='beta value').reset_index(drop=True)

            
            st.write("Sorted Beta Values and Percentage Change:")
            st.dataframe(df_sorted)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    else:
        st.warning("Please select at least one stock.")

    
    