class FutureData:
    def __init__(self, classification, contract_offset):
        self.classification = classification
        self.contract_offset = contract_offset
categories = {
    pair[0]: FutureData(pair[1], pair[2]) for pair in [
        (Symbol.Create(Futures.Indices.SP500EMini, SecurityType.Future, Market.CME), ("Equity", "US"), 0),
        (Symbol.Create(Futures.Indices.NASDAQ100EMini, SecurityType.Future, Market.CME), ("Equity", "US"), 0),
        (Symbol.Create(Futures.Indices.Russell2000EMini, SecurityType.Future, Market.CME), ("Equity", "US"), 0),
        (Symbol.Create(Futures.Indices.VIX, SecurityType.Future, Market.CFE), ("Volatility", "US"), 0),
        (Symbol.Create(Futures.Energies.NaturalGas, SecurityType.Future, Market.NYMEX), ("Energies", "Gas"), 1),
        (Symbol.Create(Futures.Energies.CrudeOilWTI, SecurityType.Future, Market.NYMEX), ("Energies", "Oil"), 0),
        (Symbol.Create(Futures.Grains.Corn, SecurityType.Future, Market.CBOT), ("Agricultural", "Grain"), 0),
        (Symbol.Create(Futures.Metals.Copper, SecurityType.Future, Market.COMEX), ("Metals", "Industrial"), 0),
        (Symbol.Create(Futures.Metals.Gold, SecurityType.Future, Market.COMEX), ("Metals", "Precious"), 0),
        (Symbol.Create(Futures.Metals.Silver, SecurityType.Future, Market.COMEX), ("Metals", "Precious"), 0)
    ]
}