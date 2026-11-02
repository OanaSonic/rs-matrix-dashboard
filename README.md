# RS Matrix + Minervini Scanner

Browser-based Streamlit application. Switch between S&P 500 and a NYSE + Nasdaq subset; sector RS, interactive ticker/industry matrix, scanner filters, CSV export.

## Publish without local installation
1. Create a GitHub repository and upload `app.py` and `requirements.txt` to its root.
2. Sign in at https://share.streamlit.io/ using GitHub.
3. Click **Create app**, select your repository and `app.py`, then **Deploy**.
4. Open the generated URL on desktop or phone.

## Important limitations
- Yahoo Finance is an unofficial, non-guaranteed source. Daily historical bars are **not** a licensed consolidated real-time feed. Data may be delayed, missing or rate-limited.
- Whole US market mode is capped at 2,000 symbols per scan for performance; the default scans 500. This is **not** a full-market scan. The selected universe uses Nasdaq Trader listed symbols and excludes some securities heuristically.
- RS is *relative period return* `(1+stock_return)/(1+SPY_return)-1`, not IBD's proprietary RS Rating or an RS-line breakout signal.
- Up/Down Volume is a proxy based on 50 daily close-to-close price changes, not an official proprietary indicator.
- Market-cap segmentation is not implemented because reliable market-cap data is not guaranteed free for the entire universe.
- The Minervini filter here is a starter filter, **not** the full Minervini Trend Template or VCP detection.
- S&P membership and ticker data depend on public third-party sites; upstream changes may break parsing.
- yfinance may rate-limit bulk requests. Lower the ticker limit if errors occur.

## Sector SPDR module
The dashboard includes all 11 Select Sector SPDR ETFs (XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLB, XLRE, XLC), their relative strength vs SPY, and top 10 holdings by reported fund weight (up to 110 rows). Holdings are fetched from Yahoo Finance fund data or the public Stock Analysis holdings page, and are never invented when unavailable. Weights are holdings weights, not implied stock returns. The page shows the source; verify the holdings-as-of date at the issuer. ETF and underlying prices use daily Yahoo Finance bars, not guaranteed live feeds.
