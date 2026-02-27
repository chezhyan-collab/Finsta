# Zerodha Portfolio Management

A lightweight Python portfolio management utility for Zerodha (Kite Connect).

## Features

- Authenticates using Zerodha API credentials
- Fetches holdings and day positions
- Computes:
  - Total invested value
  - Current market value
  - Overall and per-symbol P&L
  - Allocation by symbol
- Supports optional target allocation and generates rebalance suggestions
- Exports a CSV report

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure credentials

Set environment variables:

```bash
export KITE_API_KEY="your_api_key"
export KITE_ACCESS_TOKEN="your_access_token"
```

> Generate `access_token` using Zerodha's login flow for Kite Connect.

## Usage

```bash
python portfolio_manager.py --output reports/portfolio.csv
```

With target allocation JSON:

```bash
python portfolio_manager.py \
  --target-allocation target_allocation.json \
  --output reports/portfolio.csv
```

Example `target_allocation.json`:

```json
{
  "INFY": 0.2,
  "TCS": 0.2,
  "RELIANCE": 0.3,
  "HDFCBANK": 0.3
}
```

## Notes

- This tool uses the official `kiteconnect` Python package.
- Rebalance suggestions are informational and **not** trade advice.
