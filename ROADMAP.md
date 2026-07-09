# Roadmap

Ideas for making the game feel more like real trading. Nothing here is committed
work; it's a menu of directions, roughly ordered by how much realism they add for
the effort, with a note on whether the free keyless data can support each one.

The current keyless feeds already carry more than the game uses today. Yahoo's
chart response includes market hours with pre/regular/post trading periods,
dividend and split history, day and 52-week ranges, and volume. CoinGecko gives
24h high/low, volume, market-cap rank, all-time high, and multi-period changes.
What is not available keyless is real bid/ask and stock fundamentals, since
Yahoo's quote endpoint returns 401, so anything spread- or P/E-related has to be
simulated or left out.

Legend: **[keyless]** works with the current free data, **[simulate]** needs a
plausible model rather than real data, **[mixed]** is partly one and partly the other.

## Order types and a fill engine

The biggest single step from toy to broker. Add an orders table and a small
background worker that reuses the existing ~60-second price refresh to check and
fill pending orders when their conditions are met.

- [ ] Limit orders, filling only at your price or better **[keyless]**
- [ ] Stop-loss and take-profit orders **[keyless]**
- [ ] Trailing stops **[keyless]**
- [ ] Good-till-cancelled versus day orders, plus an open-orders view **[keyless]**

## Trading friction

Frictionless trading is the clearest sign it's a game.

- [ ] Commissions or fees per trade, typically higher for crypto than stocks **[keyless]**
- [ ] A simulated bid/ask spread that scales with asset class and liquidity **[simulate]**
- [ ] Slippage on large orders **[simulate]**

## Market hours and state

- [ ] An Open / Closed / Pre-market / After-hours badge per asset **[keyless]**
- [ ] Mark prices as live or last-close, and block or flag trades when a market is shut **[keyless]**
- [ ] Keep crypto trading 24/7 and forex roughly 24/5 **[keyless]**

## Income

- [ ] Dividend payments credited to cash when a position is held through the ex-date **[keyless]**
- [ ] Interest on idle cash, like a savings rate **[simulate]**
- [ ] Stock-split adjustments to holdings **[keyless]**
- [ ] Crypto staking-style rewards **[simulate]**

## Short selling, margin and leverage

Higher realism, and more accounting to get right.

- [ ] Short selling with a borrow fee **[mixed]**
- [ ] Margin and leverage so buying power exceeds cash **[simulate]**
- [ ] Margin calls and forced liquidation when equity falls too far **[simulate]**

## More to trade

- [ ] ETFs, indices, commodities, and treasuries via Yahoo symbols such as the S&P 500, gold, oil, and the VIX **[keyless]**
- [ ] Options with expiry and exercise, which is a project in its own right **[mixed]**

## Analytics, risk and taxes

- [ ] A per-player equity curve over time **[keyless]**
- [ ] Benchmark performance against the S&P 500 **[keyless]**
- [ ] Volatility, maximum drawdown, and a Sharpe ratio **[keyless]**
- [ ] Realized versus unrealized profit with FIFO tax lots **[keyless]**
- [ ] Capital-gains tax on realized profit, split into short and long term **[simulate]**
- [ ] A sector or asset-class allocation view; crypto rank is keyless, stock sectors need tagging **[mixed]**

## Engagement

- [ ] Watchlists and in-app price alerts **[keyless]**
- [ ] Candlestick charts with volume and faster intraday ticks **[keyless]**
- [ ] News headlines per asset and an earnings or economic calendar **[keyless]**
- [ ] Seasons, with leaderboards that reset weekly or monthly **[no data needed]**
- [ ] Achievements, and trading halts or circuit breakers on extreme moves **[simulate]**

## Suggested first wave

Limit and stop orders with the fill engine, commissions and a simulated spread,
market-hours awareness, and dividends plus cash interest. Those four are mostly
keyless, they reinforce each other, and together they move the game from a single
magic price to something that behaves like a brokerage. Short selling and margin
make a strong second wave once the order engine exists.
