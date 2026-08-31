"""
Basit ama gerçekçi bir event-driven backtest motoru.

Gerçekçilik için dahil edilenler:
- Komisyon (round-trip) ve slipaj maliyeti
- ATR tabanlı stop-loss ve take-profit (sinyal her mumda değil, pozisyon
  kapanana kadar sabit kalır)
- Aynı anda tek pozisyon (long veya short)
- Sinyal bir sonraki mumun açılışında uygulanır (look-ahead bias'ı önlemek için)

Bu motor "kesin performans" değil, kural setinin GEÇMİŞTE nasıl davrandığını
gösterir. Geçmiş performans gelecek performansın garantisi değildir.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Trade:
    entry_time: pd.Timestamp
    entry_price: float
    direction: int  # 1 = long, -1 = short
    stop_price: float
    target_price: float
    exit_time: pd.Timestamp = None
    exit_price: float = None
    exit_reason: str = None
    pnl_pct: float = None


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


class Backtester:
    def __init__(
        self,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.0005,
        initial_capital: float = 10_000.0,
        risk_per_trade_pct: float = 0.01,
    ):
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.initial_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct

    def run(self, df: pd.DataFrame) -> BacktestResult:
        equity = self.initial_capital
        equity_curve = []
        trades = []
        position: Trade = None

        idx = df.index
        for i in range(1, len(df) - 1):
            row = df.iloc[i]
            next_row = df.iloc[i + 1]

            if position is not None:
                hit_stop = (
                    row["Low"] <= position.stop_price
                    if position.direction == 1
                    else row["High"] >= position.stop_price
                )
                hit_target = (
                    row["High"] >= position.target_price
                    if position.direction == 1
                    else row["Low"] <= position.target_price
                )

                if hit_stop or hit_target:
                    exit_price = position.stop_price if hit_stop else position.target_price
                    exit_price *= (1 - self.slippage_pct * position.direction)
                    raw_pnl_pct = (exit_price - position.entry_price) / position.entry_price * position.direction
                    net_pnl_pct = raw_pnl_pct - 2 * self.commission_pct

                    position.exit_time = idx[i]
                    position.exit_price = exit_price
                    position.exit_reason = "stop" if hit_stop else "target"
                    position.pnl_pct = net_pnl_pct

                    stop_pct_risk = abs(position.stop_price - position.entry_price) / position.entry_price
                    size_multiplier = self.risk_per_trade_pct / max(stop_pct_risk, 1e-6)
                    equity *= (1 + net_pnl_pct * size_multiplier)
                    trades.append(position)
                    position = None

            if position is None and row["signal"] != 0:
                direction = int(row["signal"])
                entry_price = next_row["Open"] * (1 + self.slippage_pct * direction)
                stop_dist = row["stop_dist"]
                target_dist = row["target_dist"]

                stop_price = entry_price - direction * stop_dist
                target_price = entry_price + direction * target_dist

                position = Trade(
                    entry_time=idx[i + 1],
                    entry_price=entry_price,
                    direction=direction,
                    stop_price=stop_price,
                    target_price=target_price,
                )

            equity_curve.append(equity)

        equity_series = pd.Series(equity_curve, index=idx[1:len(equity_curve) + 1])
        metrics = self._compute_metrics(equity_series, trades)
        return BacktestResult(equity_curve=equity_series, trades=trades, metrics=metrics)

    def _compute_metrics(self, equity: pd.Series, trades: list) -> dict:
        if len(equity) < 2 or len(trades) == 0:
            return {"trade_count": len(trades), "note": "Yetersiz veri/işlem"}

        total_return = equity.iloc[-1] / self.initial_capital - 1
        days = max((equity.index[-1] - equity.index[0]).days, 1)
        cagr = (equity.iloc[-1] / self.initial_capital) ** (365 / days) - 1

        daily_returns = equity.pct_change().dropna()
        sharpe = (
            daily_returns.mean() / daily_returns.std() * np.sqrt(252)
            if daily_returns.std() > 0 else 0.0
        )

        running_max = equity.cummax()
        drawdown = equity / running_max - 1
        max_dd = drawdown.min()

        wins = [t for t in trades if t.pnl_pct and t.pnl_pct > 0]
        win_rate = len(wins) / len(trades) if trades else 0

        return {
            "trade_count": len(trades),
            "win_rate_pct": round(win_rate * 100, 2),
            "total_return_pct": round(total_return * 100, 2),
            "cagr_pct": round(cagr * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "final_equity": round(equity.iloc[-1], 2),
        }
