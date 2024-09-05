import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go


nifty50_df = yf.download('^NSEI', start='2021-09-01', end='2050-09-01', interval='1d')
niftybank_df = yf.download('^NSEBANK', start='2021-09-01', end='2050-09-01', interval='1d')


nifty50_df.reset_index(inplace=True)
niftybank_df.reset_index(inplace=True)


nifty50_df['Weekday'] = nifty50_df['Date'].dt.day_name()
niftybank_df['Weekday'] = niftybank_df['Date'].dt.day_name()


st.sidebar.title('Stock Analysis')
option = st.sidebar.selectbox(
    'Select the index',
    ('Nifty 50', 'Nifty Bank')
)


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


