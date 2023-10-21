class CarryAndTrendAlphaModel(AlphaModel):
    futures = []
    BUSINESS_DAYS_IN_YEAR = 256
    TREND_FORECAST_SCALAR_BY_SPAN = {64: 1.91, 32: 2.79, 16: 4.1, 8: 5.95, 4: 8.53, 2: 12.1}  # Table 29 on page 177
    CARRY_FORECAST_SCALAR = 30  # Provided on p.216
    FDM_BY_RULE_COUNT = {  # Table 52 on page 234
        1: 1.0,
        2: 1.02,
        3: 1.03,
        4: 1.23,
        5: 1.25,
        6: 1.27,
        7: 1.29,
        8: 1.32,
        9: 1.34,
    }

    def __init__(self, algorithm, emac_filters, abs_forecast_cap, sigma_span, target_risk, blend_years):
        self.algorithm = algorithm

        self.emac_spans = [2 ** x for x in range(4, emac_filters + 1)]
        self.fast_ema_spans = self.emac_spans
        self.slow_ema_spans = [fast_span * 4 for fast_span in self.emac_spans]
        self.all_ema_spans = sorted(list(set(self.fast_ema_spans + self.slow_ema_spans)))
        self.carry_spans = [5, 20, 60, 120]
        self.annulaization_factor = self.BUSINESS_DAYS_IN_YEAR ** 0.5
        self.abs_forecast_cap = abs_forecast_cap

        self.sigma_span = sigma_span
        self.target_risk = target_risk
        self.blend_years = blend_years
        self.idm = 1.5  # Instrument Diversification Multiplier.
        self.categories = categories
        self.total_lookback = timedelta(sigma_span * (7 / 5) + blend_years * 365)
        self.day = -1

        def OnSecuritiesChanged(self, algorithm: QCAlgorithm, changes: SecurityChanges) -> None:
            for security in changes.AddedSecurities:
                symbol = security.Symbol
                # Create a consolidator to update the history
                security.consolidator = TradeBarConsolidator(timedelta(1))
                security.consolidator.DataConsolidated += self.consolidation_handler
                algorithm.SubscriptionManager.AddConsolidator(symbol, security.consolidator)
                # Get raw and adjusted history
                security.raw_history = pd.Series()
                if symbol.IsCanonical():
                    security.adjusted_history = pd.Series()
                    security.annualized_raw_carry_history = pd.Series()
                    # Create indicators for the continuous contract
                    ema_by_span = {span: algorithm.EMA(symbol, span, Resolution.Daily) for span in self.all_ema_spans}
                    security.ewmac_by_span = {}
                    for i, fast_span in enumerate(self.emac_spans):
                        security.ewmac_by_span[fast_span] = IndicatorExtensions.Minus(ema_by_span[fast_span],
                                                                                      ema_by_span[
                                                                                          self.slow_ema_spans[i]])
                    security.automatic_indicators = ema_by_span.values()
                    self.futures.append(security)
            for security in changes.RemovedSecurities:
                # Remove consolidator + indicators
                algorithm.SubscriptionManager.RemoveConsolidator(security.Symbol, security.consolidator)
                if security.Symbol.IsCanonical():
                    for indicator in security.automatic_indicators:
                        algorithm.DeregisterIndicator(indicator)

        def consolidation_handler(self, sender: object, consolidated_bar: TradeBar) -> None:
            security = self.algorithm.Securities[consolidated_bar.Symbol]
            end_date = consolidated_bar.EndTime.date()
            if security.Symbol.IsCanonical():
                # Update adjusted history
                security.adjusted_history.loc[end_date] = consolidated_bar.Close
                security.adjusted_history = security.adjusted_history[
                    security.adjusted_history.index >= end_date - self.total_lookback]
            else:
                # Update raw history
                continuous_contract = self.algorithm.Securities[security.Symbol.Canonical]
                if hasattr(continuous_contract,
                           "latest_mapped") and consolidated_bar.Symbol == continuous_contract.latest_mapped:
                    continuous_contract.raw_history.loc[end_date] = consolidated_bar.Close
                    continuous_contract.raw_history = continuous_contract.raw_history[
                        continuous_contract.raw_history.index >= end_date - self.total_lookback]

                # Update raw carry history
                security.raw_history.loc[end_date] = consolidated_bar.Close
                security.raw_history = security.raw_history.iloc[-1:]

        def Update(self, algorithm: QCAlgorithm, data: Slice) -> List[Insight]:
            if data.QuoteBars.Count:
                for future in self.futures:
                    future.latest_mapped = future.Mapped
            # Rebalance daily
            if self.day == data.Time.day or data.QuoteBars.Count == 0:
                return []
            # Update annualized carry data
            for future in self.futures:
                # Get the near and far contracts
                contracts = self.get_near_and_further_contracts(algorithm.Securities, future.Mapped)
                if contracts is None:
                    continue
                near_contract, further_contract = contracts[0], contracts[1]

                # Save near and further contract for later
                future.near_contract = near_contract
                future.further_contract = further_contract
                # Check if the daily consolidator has provided a bar for these contracts yet
                if not hasattr(near_contract, "raw_history") or not hasattr(further_contract,
                                                                            "raw_history") or near_contract.raw_history.empty or further_contract.raw_history.empty:
                    continue
                # Update annualized raw carry history
                raw_carry = near_contract.raw_history.iloc[0] - further_contract.raw_history.iloc[0]
                months_between_contracts = round((further_contract.Expiry - near_contract.Expiry).days / 30)
                expiry_difference_in_years = abs(months_between_contracts) / 12
                annualized_raw_carry = raw_carry / expiry_difference_in_years
                future.annualized_raw_carry_history.loc[near_contract.raw_history.index[0]] = annualized_raw_carry
            # If warming up and still > 7 days before start date, don't do anything
            # We use a 7-day buffer so that the algorithm has active insights when warm-up ends
            if algorithm.StartDate - algorithm.Time > timedelta(7):
                self.day = data.Time.day
                return []

            # Estimate the standard deviation of % daily returns for each future
            sigma_pcts_by_future = {}
            for future in self.futures:
                sigma_pcts = self.estimate_std_of_pct_returns(future.raw_history, future.adjusted_history)
                # Check if there is sufficient history
                if sigma_pcts is None:
                    continue
                sigma_pcts_by_future[future] = sigma_pcts
            # Create insights
            insights = []
            weight_by_symbol = GetPositionSize(
                {future.Symbol: self.categories[future.Symbol].classification for future in
                 sigma_pcts_by_future.keys()})
            for symbol, instrument_weight in weight_by_symbol.items():
                future = algorithm.Securities[symbol]
                target_contract = [future.near_contract, future.further_contract][
                    self.categories[future.Symbol].contract_offset]
                sigma_pct = sigma_pcts_by_future[future]
                daily_risk_price_terms = sigma_pct / (
                    self.annulaization_factor) * target_contract.Price  # "The price should be for the expiry date we currently hold (not the back-adjusted price)" (p.55)
                # Calculate target position
                position = (algorithm.Portfolio.TotalPortfolioValue * self.idm * instrument_weight * self.target_risk) \
                           / (future.SymbolProperties.ContractMultiplier * daily_risk_price_terms * (
                    self.annulaization_factor))
                # Calculate forecast type 1: EMAC
                trend_forecasts = self.calculate_emac_forecasts(future.ewmac_by_span, daily_risk_price_terms)
                if not trend_forecasts:
                    continue
                emac_combined_forecasts = sum(trend_forecasts) / len(
                    trend_forecasts)  # Aggregate EMAC factors -- equal-weight
                # Calculate factor type 2: Carry
                carry_forecasts = self.calculate_carry_forecasts(future.annualized_raw_carry_history,
                                                                 daily_risk_price_terms)
                if not carry_forecasts:
                    continue
                carry_combined_forecasts = sum(carry_forecasts) / len(
                    carry_forecasts)  # Aggregate Carry factors -- equal-weight

                # Aggregate factors -- 60% for trend, 40% for carry
                raw_combined_forecast = 0.6 * emac_combined_forecasts + 0.4 * carry_combined_forecasts
                scaled_combined_forecast = raw_combined_forecast * self.FDM_BY_RULE_COUNT[len(trend_forecasts) + len(
                    carry_forecasts)]  # Apply a forecast diversification multiplier to keep the average forecast at 10 (p 193-194)
                capped_combined_forecast = max(min(scaled_combined_forecast, self.abs_forecast_cap),
                                               -self.abs_forecast_cap)
                if capped_combined_forecast * position == 0:
                    continue
                target_contract.forecast = capped_combined_forecast
                target_contract.position = position

                local_time = Extensions.ConvertTo(algorithm.Time, algorithm.TimeZone, future.Exchange.TimeZone)
                expiry = future.Exchange.Hours.GetNextMarketOpen(local_time, False) - timedelta(seconds=1)
                insights.append(Insight.Price(target_contract.Symbol, expiry,
                                              InsightDirection.Up if capped_combined_forecast * position > 0 else InsightDirection.Down))

            if insights:
                self.day = data.Time.day
            return insights

        def calculate_emac_forecasts(self, ewmac_by_span, daily_risk_price_terms):
            forecasts = []
            for span in self.emac_spans:
                risk_adjusted_ewmac = ewmac_by_span[span].Current.Value / daily_risk_price_terms
                scaled_forecast_for_ewmac = risk_adjusted_ewmac * self.TREND_FORECAST_SCALAR_BY_SPAN[span]
                capped_forecast_for_ewmac = max(min(scaled_forecast_for_ewmac, self.abs_forecast_cap),
                                                -self.abs_forecast_cap)
                forecasts.append(capped_forecast_for_ewmac)
            return forecasts

        def calculate_carry_forecasts(self, annualized_raw_carry, daily_risk_price_terms):
            carry_forecast = annualized_raw_carry / daily_risk_price_terms
            forecasts = []
            for span in self.carry_spans:
                ## Smooth out carry forecast
                smoothed_carry_forecast = carry_forecast.ewm(span=span, min_periods=span).mean().dropna()
                if smoothed_carry_forecast.empty:
                    continue
                smoothed_carry_forecast = smoothed_carry_forecast.iloc[-1]
                ## Apply forecast scalar (p. 264)
                scaled_carry_forecast = smoothed_carry_forecast * self.CARRY_FORECAST_SCALAR
                ## Cap forecast
                capped_carry_forecast = max(min(scaled_carry_forecast, self.abs_forecast_cap), -self.abs_forecast_cap)
                forecasts.append(capped_carry_forecast)
            return forecasts