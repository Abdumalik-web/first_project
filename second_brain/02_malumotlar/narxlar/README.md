# Narx ma'lumotlari

Fayl nomi: `<TICKER>_<timeframe>.csv`, masalan `BTCUSDT_1d.csv` yoki `AAPL_1d.csv`.

Format:
```csv
date,open,high,low,close,volume
2026-01-01,93500,94800,92100,94200,18234.5
```

Ma'lumotni qayerdan olish mumkin:
- Kripto: Binance API, CoinGecko
- Aksiya: Yahoo Finance (`yfinance`)
- Forex: TradingView'dan eksport, Alpha Vantage

Indikatorlar keyinchalik agent kodi orqali shu fayllardan avtomatik hisoblanadi.
