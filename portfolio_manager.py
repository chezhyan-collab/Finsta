import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from kiteconnect import KiteConnect


@dataclass
class PortfolioMetrics:
    total_invested: float
    total_current_value: float
    total_pnl: float
    total_pnl_pct: float


class ZerodhaPortfolioManager:
    def __init__(self, api_key: str, access_token: str) -> None:
        self.client = KiteConnect(api_key=api_key)
        self.client.set_access_token(access_token)

    def get_holdings(self) -> pd.DataFrame:
        holdings = self.client.holdings()
        if not holdings:
            return pd.DataFrame(
                columns=[
                    "tradingsymbol",
                    "quantity",
                    "average_price",
                    "last_price",
                ]
            )
        return pd.DataFrame(holdings)

    def get_day_positions(self) -> pd.DataFrame:
        positions = self.client.positions().get("day", [])
        if not positions:
            return pd.DataFrame(columns=["tradingsymbol", "quantity", "average_price", "last_price"])
        return pd.DataFrame(positions)

    @staticmethod
    def compute_metrics(df: pd.DataFrame) -> PortfolioMetrics:
        if df.empty:
            return PortfolioMetrics(0.0, 0.0, 0.0, 0.0)

        working = df.copy()
        working["invested"] = working["quantity"] * working["average_price"]
        working["current_value"] = working["quantity"] * working["last_price"]
        working["pnl"] = working["current_value"] - working["invested"]
        working["pnl_pct"] = (working["pnl"] / working["invested"].replace(0, pd.NA)) * 100

        total_invested = float(working["invested"].sum())
        total_current_value = float(working["current_value"].sum())
        total_pnl = float(working["pnl"].sum())
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0.0

        return PortfolioMetrics(
            total_invested=round(total_invested, 2),
            total_current_value=round(total_current_value, 2),
            total_pnl=round(total_pnl, 2),
            total_pnl_pct=round(total_pnl_pct, 2),
        )

    @staticmethod
    def enrich_positions(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        output = df[["tradingsymbol", "quantity", "average_price", "last_price"]].copy()
        output["invested"] = output["quantity"] * output["average_price"]
        output["current_value"] = output["quantity"] * output["last_price"]
        output["pnl"] = output["current_value"] - output["invested"]
        output["pnl_pct"] = (output["pnl"] / output["invested"].replace(0, pd.NA)) * 100

        total_current = output["current_value"].sum()
        output["allocation_pct"] = (output["current_value"] / total_current * 100) if total_current else 0.0
        return output.sort_values("current_value", ascending=False)

    @staticmethod
    def rebalance_suggestions(df: pd.DataFrame, target_weights: Dict[str, float]) -> pd.DataFrame:
        if df.empty or not target_weights:
            return pd.DataFrame(columns=["tradingsymbol", "current_value", "target_value", "delta_value"])

        total_value = float(df["current_value"].sum())
        current_values = df.groupby("tradingsymbol")["current_value"].sum().to_dict()

        symbols = sorted(set(target_weights).union(current_values))
        rows: List[Dict[str, float]] = []

        for symbol in symbols:
            current = float(current_values.get(symbol, 0.0))
            target = float(target_weights.get(symbol, 0.0)) * total_value
            rows.append(
                {
                    "tradingsymbol": symbol,
                    "current_value": round(current, 2),
                    "target_value": round(target, 2),
                    "delta_value": round(target - current, 2),
                }
            )

        return pd.DataFrame(rows).sort_values("delta_value", ascending=False)


def load_target_allocation(path: Optional[str]) -> Dict[str, float]:
    if not path:
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = sum(data.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError("Target allocation weights must sum to 1.0")

    return {k.upper(): float(v) for k, v in data.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Portfolio management utility for Zerodha")
    parser.add_argument("--target-allocation", type=str, default=None, help="Path to JSON target allocation")
    parser.add_argument("--output", type=str, default="portfolio_report.csv", help="Path to write portfolio CSV")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    api_key = os.getenv("KITE_API_KEY")
    access_token = os.getenv("KITE_ACCESS_TOKEN")

    if not api_key or not access_token:
        raise EnvironmentError("Set KITE_API_KEY and KITE_ACCESS_TOKEN environment variables.")

    manager = ZerodhaPortfolioManager(api_key=api_key, access_token=access_token)

    holdings_df = manager.get_holdings()
    positions_df = manager.get_day_positions()

    all_positions = pd.concat([holdings_df, positions_df], ignore_index=True)
    enriched = manager.enrich_positions(all_positions)
    metrics = manager.compute_metrics(enriched)

    target_alloc = load_target_allocation(args.target_allocation)
    rebalance = manager.rebalance_suggestions(enriched, target_alloc)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    enriched.to_csv(output_path, index=False)

    print("Portfolio Summary")
    print(f"Total Invested: ₹{metrics.total_invested:,.2f}")
    print(f"Current Value: ₹{metrics.total_current_value:,.2f}")
    print(f"Total P&L: ₹{metrics.total_pnl:,.2f} ({metrics.total_pnl_pct:.2f}%)")
    print(f"Detailed report written to: {output_path}")

    if not rebalance.empty:
        print("\nRebalance Suggestions (₹ delta to target):")
        print(rebalance.to_string(index=False))


if __name__ == "__main__":
    main()
