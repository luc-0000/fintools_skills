# Business Logic And Workflows

## Source Anchors

- Source: end_points/get_rule/operations/get_rule_opts.py
- Source: end_points/get_rule/operations/agent_utils.py
- Source: end_points/get_earn/operations/get_earn_utils.py
- Source: end_points/get_simulator/operations/get_simulator_opts.py
- Source: end_points/get_simulator/operations/get_simulator_utils.py

## Workflow 1: Rule Execution

1. Client triggers rule run for `rule_id`.
2. System resolves remote-agent execution prerequisites for that rule.
3. If pools are assigned, system expands those pools to stock codes for a bulk run.
4. If no pools are assigned, the run path returns a structured pool-missing signal instead of silently inventing stock scope.
5. For each selected stock:
   - if `Rule.type == remote_agent`, call the shared skill adapter using `Rule.info` as base URL
6. Agent result is normalized:
   - `True` -> `indicating`
   - non-`True` -> `not_indicating`
7. System upserts one `AgentTrading` row for `(rule_id, stock, trading_date)`.
8. `Rule.updated_at` is refreshed on successful run.

### Edge Cases

- stock code suffixes like `.SH` or `.SZ` are stripped before persistence in several paths
- pool absence blocks new bulk scope selection, but does not invalidate existing `AgentTrading` rows already available for simulator replay

## Workflow 2: Pool/Rule Earn Aggregation

1. Rule-to-pool relation is read from `rule_pool`.
2. Per-stock precomputed earnings are read from `stock_rule_earn`.
3. Per-pool aggregate rows are recalculated into `pool_rule_earn`.
4. Rule-level aggregate is computed as weighted combination of pool summaries.

This is a read/update sidecar workflow used to enrich list endpoints.

## Workflow 3: Simulator Replay

1. Simulator identifies its `rule_id`.
2. All `AgentTrading` rows for that rule are read.
3. Each row becomes `{stock_code, indicating_date}`.
4. For each stock:
   - historical data is fetched with `stockDataFrameFromTushare`
   - signal dates are converted into trading items
5. The replay engine synthesizes:
   - `indicating`
   - `fail_to_buy`
   - `buy`
   - `fail_to_sell`
   - `sell`
   - `not_sufficient_to_buy`
6. The engine writes `SimTrading` events and HTML log lines.
7. Aggregate simulator metrics and serialized `earning_info` are updated.

Pool membership is not a hard prerequisite for this replay path.
If valid `AgentTrading` rows already exist for the rule, simulator replay can proceed even when the rule currently has no assigned pool.

## Trading Decision Rules

### Buy Rule

- A signal at day `t` attempts a buy at day `t+1` close.
- If next-day close rises by at least `HIGH_LIMIT = 9.5%` from the indicating close, buy fails.
- Otherwise the position is opened.

### Sell Rule

The earliest day satisfying any of the following wins:

- profit exit:
  - `(sell_price - buy_price) / buy_price >= profit_threshold / 100`
- stop loss:
  - `(buy_price - sell_price) / buy_price >= stop_loss / 100`
- time exit:
  - reached `max_holding_days`

### Limit-Down Sell Failure

- If daily drop from previous close is `<= -9.5%` and max holding window is not yet exhausted, the system records `fail_to_sell` and waits.

### Capital Allocation

- Each buy uses `INIT_MONEY_PER_STOCK = INIT_MONEY / 3`
- Buy proceeds only if:
  - `INIT_MONEY_PER_STOCK >= 100 * trade_price`
  - available cash is at least `INIT_MONEY_PER_STOCK`

## Derived Metrics

- `cum_earn`: total percent return vs `init_money`
- `avg_earn`: weighted average of per-trade returns
- `earning_rate`: percent of profitable closed trades
- `max_drawback`: minimum realized earn in the series
- `sharpe`: annualized Sharpe over realized trade returns
- `annual_earn`: `cum_earn * 365 / days_since_first_trade`

## Failure And Recovery Semantics

- most service methods rollback DB session on exception
- simulator log writes are best-effort file appends
- duplicate simulator trading events are suppressed by pre-insert existence check
- duplicate agent trade events are prevented by the canonical `AgentTrading` upsert path
