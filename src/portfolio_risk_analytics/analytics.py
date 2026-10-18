"""Dependency-free portfolio return and risk calculations."""

from __future__ import annotations

from datetime import date
import math
from typing import Any


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _sample_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def analyze_portfolio(data: dict[str, Any]) -> dict[str, Any]:
    """Analyze constant-weight, daily-rebalanced holdings from price histories.

    Returns use simple close-to-close returns. Volatility and covariance use
    sample estimates and are annualized with ``periods_per_year``. This is a
    descriptive illustration, not a forecast or investment recommendation.
    """
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("assets must be a non-empty list")
    periods_per_year = _finite_number(data.get("periods_per_year", 252), "periods_per_year")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")

    dates: list[str] | None = None
    symbols: set[str] = set()
    weights: list[float] = []
    asset_returns: list[list[float]] = []
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            raise ValueError(f"assets[{index}] must be an object")
        symbol = asset.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError(f"assets[{index}].symbol must be a non-empty string")
        if symbol in symbols:
            raise ValueError(f"duplicate symbol: {symbol}")
        symbols.add(symbol)

        weight = _finite_number(asset.get("weight"), f"{symbol}.weight")
        if weight < 0:
            raise ValueError(f"{symbol}.weight cannot be negative")
        weights.append(weight)
        prices = asset.get("prices")
        if not isinstance(prices, list) or len(prices) < 3:
            raise ValueError(f"{symbol}.prices must contain at least three observations")
        asset_dates = asset.get("dates")
        if not isinstance(asset_dates, list) or len(asset_dates) != len(prices):
            raise ValueError(f"{symbol}.dates must match prices")
        parsed_dates: list[date] = []
        for raw_date in asset_dates:
            try:
                parsed_dates.append(date.fromisoformat(raw_date))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{symbol}.dates must contain ISO YYYY-MM-DD dates") from exc
        if any(later <= earlier for earlier, later in zip(parsed_dates, parsed_dates[1:])):
            raise ValueError(f"{symbol}.dates must be strictly increasing")
        normalized_dates = [item.isoformat() for item in parsed_dates]
        if dates is None:
            dates = normalized_dates
        elif dates != normalized_dates:
            raise ValueError("all assets must have identical dates")

        numeric_prices = [
            _finite_number(price, f"{symbol}.prices[{price_index}]")
            for price_index, price in enumerate(prices)
        ]
        if any(price <= 0 for price in numeric_prices):
            raise ValueError(f"{symbol}.prices must be positive")
        asset_returns.append([
            current / previous - 1.0
            for previous, current in zip(numeric_prices, numeric_prices[1:])
        ])

    if not math.isclose(sum(weights), 1.0, rel_tol=0.0, abs_tol=1e-8):
        raise ValueError("asset weights must sum to 1")
    assert dates is not None
    return_dates = dates[1:]
    portfolio_returns = [
        sum(weights[asset_index] * asset_returns[asset_index][period_index]
            for asset_index in range(len(assets)))
        for period_index in range(len(return_dates))
    ]
    daily_mean = sum(portfolio_returns) / len(portfolio_returns)
    daily_volatility = _sample_std(portfolio_returns)
    annualized_volatility = daily_volatility * math.sqrt(periods_per_year)
    total_return = math.prod(1.0 + value for value in portfolio_returns) - 1.0

    wealth = 1.0
    peak = 1.0
    drawdowns: list[float] = []
    wealth_series: list[dict[str, float | str]] = [{"date": dates[0], "value": wealth}]
    for timestamp, daily_return in zip(return_dates, portfolio_returns):
        wealth *= 1.0 + daily_return
        peak = max(peak, wealth)
        drawdown = wealth / peak - 1.0
        drawdowns.append(drawdown)
        wealth_series.append({"date": timestamp, "value": wealth})

    means = [sum(series) / len(series) for series in asset_returns]
    covariance_daily: list[list[float]] = []
    for left, left_mean in zip(asset_returns, means):
        row: list[float] = []
        for right, right_mean in zip(asset_returns, means):
            row.append(sum((x - left_mean) * (y - right_mean)
                           for x, y in zip(left, right)) / (len(left) - 1))
        covariance_daily.append(row)
    covariance_annual = [
        [value * periods_per_year for value in row] for row in covariance_daily
    ]
    covariance_times_weights = [
        sum(covariance_annual[i][j] * weights[j] for j in range(len(assets)))
        for i in range(len(assets))
    ]
    portfolio_variance = sum(weights[i] * covariance_times_weights[i]
                             for i in range(len(assets)))
    covariance_volatility = math.sqrt(max(0.0, portfolio_variance))
    asset_risk_contributions = []
    for index, asset in enumerate(assets):
        contribution = (
            weights[index] * covariance_times_weights[index] / covariance_volatility
            if covariance_volatility > 0
            else 0.0
        )
        share = (
            weights[index] * covariance_times_weights[index] / portfolio_variance
            if portfolio_variance > 0
            else 0.0
        )
        asset_risk_contributions.append({
            "symbol": asset["symbol"],
            "weight": weights[index],
            "annualized_volatility_contribution": contribution,
            "risk_share": share,
        })

    return {
        "metadata": {
            "observations": len(dates),
            "return_observations": len(portfolio_returns),
            "periods_per_year": periods_per_year,
            "weighting_assumption": "constant weights with daily rebalancing",
            "return_convention": "simple close-to-close returns",
            "volatility_estimator": "sample standard deviation, annualized by sqrt(periods_per_year)",
        },
        "portfolio": {
            "total_return": total_return,
            "mean_daily_return": daily_mean,
            "annualized_mean_return": daily_mean * periods_per_year,
            "daily_volatility": daily_volatility,
            "annualized_volatility": annualized_volatility,
            "maximum_drawdown": min(drawdowns, default=0.0),
            "wealth_series": wealth_series,
            "daily_returns": [
                {"date": timestamp, "return": value}
                for timestamp, value in zip(return_dates, portfolio_returns)
            ],
        },
        "covariance_annualized": {
            "symbols": [asset["symbol"] for asset in assets],
            "matrix": covariance_annual,
        },
        "asset_risk_contributions": asset_risk_contributions,
    }
