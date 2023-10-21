
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