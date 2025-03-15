from alpha import CarryAndTrendAlphaModel

class FuturesCombinedCarryAndTrendAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2020, 7, 1)
        self.SetEndDate(2023, 7, 1)
        self.SetCash(1_000_000)
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)
        self.SetSecurityInitializer \
            (BrokerageModelSecurityInitializer(self.BrokerageModel, FuncSecuritySeeder(self.GetLastKnownPrices)))
        self.Settings.MinimumOrderMarginPortfolioPercentage = 0
        self.UniverseSettings.DataNormalizationMode = DataNormalizationMode.BackwardsPanamaCanal
        self.UniverseSettings.DataMappingMode = DataMappingMode.LastTradingDay
        self.AddUniverseSelection(AdvancedFuturesUniverseSelectionModel())
        self.AddAlpha(CarryAndTrendAlphaModel(
            self,
            self.GetParameter("emac_filters", 6),
            self.GetParameter("abs_forecast_cap", 20),  # Hardcoded on p.173
            self.GetParameter("sigma_span", 32),  # Hardcoded to 32 on p.604
            self.GetParameter("target_risk", 0.2),  # Recommend value is 0.2 on p.75
            self.GetParameter("blend_years", 3)  # Number of years to use when blending sigma estimates
        ))