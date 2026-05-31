import streamlit as st
import pandas as pd
import sqlite3
import yfinance as yf
from streamlit_autorefresh import st_autorefresh
import os
import json

PORTFOLIO_FILE = "portfolio.json"
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_portfolio(tickers):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(tickers, f)
# --- Page Config ---
st.set_page_config(page_title="Institutional News Terminal", layout="wide", initial_sidebar_state="expanded")

# Auto-refresh the dashboard every 60 seconds (60000 milliseconds)
st_autorefresh(interval=60000, key="data_refresh")

# --- High-Density CSS Injection (Compress the View) ---
st.markdown("""
    <style>
        /* Compress the massive default margins */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }
        /* Shrink general text and tighten line heights */
        * {
            font-family: 'Courier New', monospace !important;
        }
        html, body, [class*="css"] {
            font-size: 13px;
        }
        /* Make the Ticker Tape ultra-compact */
        .ticker-tape {
            font-size: 12px;
            white-space: nowrap;
            overflow: hidden;
            background-color: #000000;
            color: #ffffff;
            padding: 4px;
            border-bottom: 1px solid #333;
            margin-bottom: -15px;
        }
        h1, h2, h3 {
            margin-bottom: 0px !important;
            padding-bottom: 4px !important;
        }
        div[data-testid="stCaptionContainer"] {
            margin-top: -10px !important;
            margin-bottom: -10px !important;
        }
        /* Hide Streamlit Header/Deploy Button */
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}

        /* Force Multiselect Tags to be Professional Blue */
        span[data-baseweb="tag"] {
            background-color: rgba(88, 166, 255, 0.15) !important;
            border: 1px solid #58A6FF !important;
            color: #58A6FF !important;
        }
        /* Squeeze Sidebar Top Padding */
        [data-testid="stSidebarUserContent"] {
            padding-top: 1rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- Custom CSS for Bloomberg Terminal Look ---
st.markdown("""
    <style>
        .stApp {
            background-color: #0E1117;
            color: #E0E0E0;
        }
    
    /* Neon Text for Headers */
    h1, h2, h3 {
        color: #58A6FF !important;
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Dataframe Styling */
    .dataframe {
        font-family: 'Courier New', Courier, monospace !important;
    }
    
    /* Ticker Tape Animation */
    .ticker-tape {
        background: #161b22;
        color: #58A6FF;
        font-family: 'Courier New', Courier, monospace;
        font-size: 1.2rem;
        font-weight: bold;
        padding: 10px;
        white-space: nowrap;
        overflow: hidden;
        border: 1px solid #30363d;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    
    /* Hide index in dataframes */
    thead tr th:first-child {display:none}
    tbody th {display:none}
</style>
""", unsafe_allow_html=True)

SHEET_CSV_URL = "INSERT_YOUR_PRIVATE_GOOGLE_SHEET_CSV_URL_HERE"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL, header=1)
        df = df.dropna(subset=['Headline Information'])
        
        # Extract smuggled URL from AI Reasoning
        if 'AI Reasoning' in df.columns:
            df['URL'] = df['AI Reasoning'].astype(str).str.extract(r'\| URL: (.*)')
            df['AI Reasoning'] = df['AI Reasoning'].astype(str).str.replace(r' \| URL: .*', '', regex=True)
        else:
            df['URL'] = None
            
        df['Date/Time Detected'] = pd.to_datetime(df['Date/Time Detected'], errors='coerce')
        df = df.sort_values(by='Date/Time Detected', ascending=False)
        return df
    except Exception as e:
        st.error(f"Failed to load live data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_live_prices(tickers_list):
    if not tickers_list:
        return {}
    
    price_data = {}
    try:
        data = yf.download(tickers_list, period="5d", interval="1d", progress=False)
        for t in tickers_list:
            try:
                try:
                    closes = data['Close'][t].dropna()
                except:
                    closes = data['Close'].dropna()

                if len(closes) >= 2:
                    last_price = float(closes.iloc[-1])
                    prev_price = float(closes.iloc[-2])
                    pct_change = ((last_price - prev_price) / prev_price) * 100
                    price_data[t] = {"price": last_price, "change": pct_change}
                elif len(closes) == 1:
                    price_data[t] = {"price": float(closes.iloc[-1]), "change": 0.0}
            except Exception as e:
                pass
    except Exception as e:
        pass
    return price_data


@st.cache_data(ttl=300)
def fetch_intraday_prices(tickers_list):
    if not tickers_list: return pd.DataFrame()
    try:
        data = yf.download(tickers_list, period="5d", interval="5m", progress=False)
        closes = data['Close']
        if isinstance(closes, pd.Series):
            closes = closes.to_frame(name=tickers_list[0])
        return closes
    except:
        return pd.DataFrame()

# --- Load Data ---

df = load_data()

if df.empty:
    st.warning("No data found or waiting for first payload.")
    st.stop()

# Clean missing values
df = df.fillna('')
if 'Impact' in df.columns:
    df['Impact'] = df['Impact'].astype(str).str.upper().str.strip()
if 'Sector' in df.columns:
    df['Sector'] = df['Sector'].astype(str).str.title().str.strip()

# Extract unique tickers from the latest 50 rows for the price overlays
recent_tickers = set()
for t_list in df['Tickers'].dropna():
    for t in str(t_list).split(','):
        t = t.strip().upper()
        if t: recent_tickers.add(t)

live_prices = fetch_live_prices(list(recent_tickers)[:20])
intraday_df = fetch_intraday_prices(list(recent_tickers)[:20])

# --- Ticker Tape ---
ticker_tape_html = ""
for t, d in live_prices.items():
    color = "#00ff00" if d['change'] >= 0 else "#ff4444"
    sign = "+" if d['change'] >= 0 else ""
    ticker_tape_html += f" | {t}: ${d['price']:.2f} <span style='color:{color}'>({sign}{d['change']:.2f}%)</span>"

if ticker_tape_html:
    st.markdown(f'<div class="ticker-tape">🟢 LIVE PRICING {ticker_tape_html} | </div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="ticker-tape">🟢 MARKET OPEN | Waiting for ticker extraction... </div>', unsafe_allow_html=True)

# --- Sidebar Filters ---
st.sidebar.title("🔥 Institutional News Terminal")
st.sidebar.header("Terminal Slicers")

# 1. Urgency Filter
urgencies = [u for u in df['Urgency'].unique() if u]
selected_urgency = st.sidebar.multiselect("Urgency Level", options=urgencies, default=[])

# 2. Sector Filter
sectors = [s for s in df['Sector'].unique() if s]
selected_sectors = st.sidebar.multiselect("Sectors", options=sectors, default=[])

# 3. Impact Direction Filter
directions = [d for d in df['Impact'].unique() if d]
selected_directions = st.sidebar.multiselect("Impact Direction", options=directions, default=[])

# 4. Impact Score Slider
min_score = 0
max_score = 10
score_range = st.sidebar.slider("Minimum Impact Score", min_value=min_score, max_value=max_score, value=0)

# 5. Ticker Search
search_ticker = st.sidebar.text_input("Search Ticker (e.g. AMZN)")

st.sidebar.divider()
st.sidebar.header("📁 Portfolio Management")
portfolio_tickers = load_portfolio()
portfolio_input = st.sidebar.text_area("My Watchlist (comma separated)", value=", ".join(portfolio_tickers))
new_portfolio = [t.strip().upper() for t in portfolio_input.split(",") if t.strip()]
if new_portfolio != portfolio_tickers:
    save_portfolio(new_portfolio)
    portfolio_tickers = new_portfolio

filter_by_portfolio = st.sidebar.checkbox("Show Watchlist Only", value=False)
enable_alerts = st.sidebar.checkbox("Desktop Alerts (Mac)", value=True)

st.sidebar.divider()
if st.sidebar.button("🔄 Force Refresh"):
    st.cache_data.clear()
    st.rerun()

# --- Apply Filters ---
filtered_df = df.copy()

if selected_urgency:
    filtered_df = filtered_df[filtered_df['Urgency'].isin(selected_urgency)]
if selected_sectors:
    filtered_df = filtered_df[filtered_df['Sector'].isin(selected_sectors)]
if selected_directions:
    filtered_df = filtered_df[filtered_df['Impact'].isin(selected_directions)]

# Handle Impact Score column (which might be named 'Impact Score (1-10)')
score_col = [c for c in df.columns if 'Score' in c][0]
filtered_df[score_col] = pd.to_numeric(filtered_df[score_col], errors='coerce').fillna(0)
if score_range > min_score:
    filtered_df = filtered_df[filtered_df[score_col] >= score_range]
if search_ticker:
    filtered_df = filtered_df[filtered_df['Tickers'].str.contains(search_ticker.upper(), na=False)]
if filter_by_portfolio and portfolio_tickers:
    mask = filtered_df['Tickers'].apply(lambda x: any(t.strip().upper() in portfolio_tickers for t in str(x).split(',')))
    filtered_df = filtered_df[mask]

# --- Alert Engine ---
if enable_alerts and portfolio_tickers and not df.empty:
    latest_ts = df['Date/Time Detected'].max()
    if 'last_alert_ts' not in st.session_state:
        st.session_state.last_alert_ts = latest_ts
    
    if latest_ts > st.session_state.last_alert_ts:
        new_rows = df[df['Date/Time Detected'] > st.session_state.last_alert_ts]
        for _, row in new_rows.iterrows():
            row_tickers = [t.strip().upper() for t in str(row.get('Tickers', '')).split(',') if t.strip()]
            if any(t in portfolio_tickers for t in row_tickers):
                headline = str(row.get('Headline Information', '')).replace('"', '\"').replace("'", "\'")
                score = row.get(score_col, 0)
                os.system(f"osascript -e 'display notification \"{headline}\" with title \"Institutional Terminal: Alert (Score {score})\"'")
        st.session_state.last_alert_ts = latest_ts

# --- 4 Quadrant Layout Logic ---

# Build Screener DF in memory first
screener_data = []
screener_tickers_to_fetch = list(recent_tickers)[:15] # Limit to avoid slow loading

# GLOBAL OVERRIDE: Inject searched ticker into the watchlist
if search_ticker:
    search_t_upper = search_ticker.upper().strip()
    if search_t_upper not in screener_tickers_to_fetch:
        screener_tickers_to_fetch.insert(0, search_t_upper)

for t in screener_tickers_to_fetch:
    try:
        info = yf.Ticker(t).info
        screener_data.append({
            "Ticker": t,
            "Company": info.get('shortName', 'Unknown'),
            "Market Cap": info.get('marketCap', 0),
            "PEG Ratio": info.get('pegRatio', 0),
            "ROE (%)": info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0,
        })
    except:
        pass

screener_df = pd.DataFrame(screener_data)
if not screener_df.empty:
    screener_df = screener_df.sort_values(by="Market Cap", ascending=False)
    # Convert Market Cap to Billions for native display, keep PEG and ROE as numbers
    screener_df['Market Cap'] = screener_df['Market Cap'] / 1e9

    screener_styled = screener_df.style.set_properties(**{
        'font-size': '11px',
        'padding': '0px 4px',
        'line-height': '1.0'
    })
else:
    screener_styled = screener_df

# Check what was selected in the Screener (Impact Tracing)
selected_screener_ticker = None
if 'screener_df_key' in st.session_state:
    sel_rows = st.session_state.screener_df_key.get('selection', {}).get('rows', [])
    if sel_rows and not screener_df.empty:
        try:
            selected_screener_ticker = screener_df.iloc[sel_rows[0]]['Ticker']
        except:
            pass

# Apply cross-filtering
if selected_screener_ticker:
    filtered_df = filtered_df[filtered_df['Tickers'].str.contains(selected_screener_ticker, na=False)]

# --- Live Price Overlays Column ---
def format_row_prices(row):
    val = row['Tickers']
    if not val: return ''
    
    ts = pd.to_datetime(row['Date/Time Detected'], errors='coerce')
    impact_dir = str(row.get('Impact', '')).upper()
    
    formatted = []
    for t in str(val).split(','):
        t = t.strip()
        if t in live_prices:
            d = live_prices[t]
            
            surprise_str = ""
            if not pd.isna(ts) and not intraday_df.empty and t in intraday_df.columns:
                series = intraday_df[t].dropna()
                if not series.empty:
                    try:
                        ts_pd = pd.to_datetime(ts)
                        if series.index.tz is not None:
                            ts_aware = ts_pd.tz_localize('UTC').tz_convert(series.index.tz) if ts_pd.tz is None else ts_pd.tz_convert(series.index.tz)
                        else:
                            ts_aware = ts_pd.tz_localize(None)
                            
                        pre_news_time = ts_aware - pd.Timedelta(minutes=60)
                        pre_prices = series[series.index <= pre_news_time]
                        
                        if not pre_prices.empty:
                            pre_price = float(pre_prices.iloc[-1])
                            curr_price = float(series.iloc[-1])
                            pct_move = ((curr_price - pre_price) / pre_price) * 100
                            
                            conf = ""
                            if pct_move > 0.5:
                                conf = "✅" if impact_dir == 'BULLISH' else "❌"
                            elif pct_move < -0.5:
                                conf = "✅" if impact_dir == 'BEARISH' else "❌"
                            else:
                                conf = "➖"
                                
                            sign = "+" if pct_move >= 0 else ""
                            surprise_str = f" | Surprise: {sign}{pct_move:.1f}% {conf}"
                    except Exception as e:
                        pass
                        
            color = "green" if d['change'] >= 0 else "red"
            sign = "+" if d['change'] >= 0 else ""
            formatted.append(f"{t} (${d['price']:.2f}{surprise_str})")
        else:
            formatted.append(t)
    return " | ".join(formatted)

filtered_df['Price Action'] = filtered_df.apply(format_row_prices, axis=1)

# Reorder columns for display
display_cols = ['Date/Time Detected', 'Urgency', 'Impact', score_col, 'Sector', 'Price Action', 'Headline Information', 'AI Reasoning', 'Source', 'URL']
display_df = filtered_df[[c for c in display_cols if c in filtered_df.columns]].copy()

# Rename Impact Score (1-10) to Score to save width
if score_col in display_df.columns:
    display_df = display_df.rename(columns={score_col: 'Score'})

# Format Impact Score Precision
if 'Score' in display_df.columns:
    display_df['Score'] = pd.to_numeric(display_df['Score'], errors='coerce')
    display_df['Score'] = display_df['Score'].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A")

# --- Heatmap Styling ---
def style_dataframe(row):
    styles = [''] * len(row)
    try:
        score = float(row['Score'])
        if score >= 8:
            if row['Impact'] == 'BULLISH':
                styles = ['background-color: rgba(0, 255, 0, 0.15); color: #00ff00; font-weight: bold;'] * len(row)
            elif row['Impact'] == 'BEARISH':
                styles = ['background-color: rgba(255, 0, 0, 0.15); color: #ff4444; font-weight: bold;'] * len(row)
        elif score <= 3:
            styles = ['color: #666666;'] * len(row)
    except:
        pass
    return styles

def color_direction(val):
    if val == 'BULLISH': return 'color: #00ff00; font-weight: bold;'
    if val == 'BEARISH': return 'color: #ff4444; font-weight: bold;'
    return 'color: #aaaaaa;'

styled_df = display_df.style.apply(style_dataframe, axis=1) \
    .map(color_direction, subset=['Impact']) \
    .set_properties(**{
        'font-size': '11px',
        'padding': '0px 4px',
        'line-height': '1.0'
    })

# Layout Matrix
tab1, tab2 = st.tabs(["🌐 Live Terminal", "📈 ML Performance Matrix"])

with tab1:
    
    col1, col2 = st.columns([7.5, 2.5])

    with col1:
        st.markdown("### [NEWS.GLO]")
        if selected_screener_ticker:
            st.caption(f"🔍 Impact Tracing Active: Showing only news affecting **{selected_screener_ticker}**")
        
        st.dataframe(
            styled_df, 
            use_container_width=True, 
            height=500, 
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "URL": st.column_config.LinkColumn("🔗 Link", display_text="Read Article")
            },
            key="news_df_key"
        )

    with col2:
        st.markdown("### [SCRN.USA]")
        st.caption("Click a ticker to instantly trace its news impact (Pro Tip 2)")
    
        if not screener_df.empty:
            st.dataframe(
                screener_df,
                column_config={
                    "Company": st.column_config.TextColumn("Company", width="small"),
                    "Market Cap": st.column_config.NumberColumn("Mkt Cap", format="$%.2f B"),
                    "PEG Ratio": st.column_config.NumberColumn("PEG", format="%.2f"),
                    "ROE (%)": st.column_config.NumberColumn("ROE", format="%.1f%%"),
                },
                use_container_width=True,
                height=250,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="screener_df_key"
            )
        else:
            st.info("No tickers found in recent news to screen.")
        
        st.markdown("### [ERNS.CHART]")
    
        # Decide which ticker to chart
        chart_ticker = selected_screener_ticker
    
        # If a user clicked a news row, we can also extract the ticker from that!
        if 'news_df_key' in st.session_state and not chart_ticker:
            n_rows = st.session_state.news_df_key.get('selection', {}).get('rows', [])
            if n_rows and not display_df.empty:
                try:
                    clicked_news_tickers = display_df.iloc[n_rows[0]]['Live Prices']
                    # Try to extract the first word (the ticker)
                    if clicked_news_tickers:
                        chart_ticker = clicked_news_tickers.split(' ')[0].strip()
                except:
                    pass
                
        # GLOBAL OVERRIDE: If user explicitly searched a ticker, chart it!
        if search_ticker and not chart_ticker:
            chart_ticker = search_ticker.upper().strip()
                
        if chart_ticker:
            st.caption(f"📊 Historical Earnings: **{chart_ticker}** (USD in Millions)")
            try:
                from plotly.subplots import make_subplots
                import plotly.graph_objects as go
                t_data = yf.Ticker(chart_ticker)
                inc = t_data.quarterly_income_stmt
                if inc is not None and not inc.empty and 'Net Income' in inc.index:
                    net_inc = inc.loc['Net Income'].dropna().sort_index() / 1e6
                
                    # Check for Total Revenue
                    has_rev = 'Total Revenue' in inc.index
                
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                    fig.add_trace(
                        go.Bar(x=net_inc.index, y=net_inc.values, name="Net Income", marker_color='#58A6FF'),
                        secondary_y=False,
                    )
                
                    if has_rev:
                        rev = inc.loc['Total Revenue'].dropna().sort_index() / 1e6
                        fig.add_trace(
                            go.Scatter(x=rev.index, y=rev.values, name="Total Revenue", mode='lines+markers', line=dict(color='#00ff00', width=2)),
                            secondary_y=True,
                        )
                
                    fig.update_layout(
                        template="plotly_dark",
                        margin=dict(l=0, r=0, t=40, b=0), 
                        height=300,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"No quarterly earnings data available for {chart_ticker}.")
            except Exception as e:
                st.error(f"Could not chart {chart_ticker}: {e}")
        else:
            st.info("Select a stock from the Watchlist or News Feed to visualize Earnings Acceleration.")



with tab2:
    st.markdown("### Model Validation & Backtester")
    st.caption("Validating the AI's predictions against real-time market reactions (1-hour forward return).")
    
    bullish_calls = display_df[display_df['Impact'] == 'BULLISH']
    bearish_calls = display_df[display_df['Impact'] == 'BEARISH']
    
    if not display_df.empty:
        bull_wins = bullish_calls['Price Action'].str.contains('✅', na=False).sum()
        bull_losses = bullish_calls['Price Action'].str.contains('❌', na=False).sum()
        bull_total = bull_wins + bull_losses
        bull_rate = (bull_wins / bull_total * 100) if bull_total > 0 else 0
        
        bear_wins = bearish_calls['Price Action'].str.contains('✅', na=False).sum()
        bear_losses = bearish_calls['Price Action'].str.contains('❌', na=False).sum()
        bear_total = bear_wins + bear_losses
        bear_rate = (bear_wins / bear_total * 100) if bear_total > 0 else 0
        
        cA, cB = st.columns(2)
        cA.metric("🟢 BULLISH Accuracy", f"{bull_rate:.1f}%", f"{bull_wins} Wins / {bull_losses} Losses")
        cB.metric("🔴 BEARISH Accuracy", f"{bear_rate:.1f}%", f"{bear_wins} Wins / {bear_losses} Losses")
        
        st.divider()
        st.markdown("#### Validated High-Conviction Trades")
        valid_df = display_df[display_df['Price Action'].str.contains('✅', na=False)]
        if not valid_df.empty:
            st.dataframe(valid_df, use_container_width=True, hide_index=True)
        else:
            st.info("No validated setups yet.")
    else:
        st.info("No price correlation data available yet.")
