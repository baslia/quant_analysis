from Selection.FutureUniverseSelectionModel import FutureUniverseSelectionModel
from futures import categories


class AdvancedFuturesUniverseSelectionModel(FutureUniverseSelectionModel):
    def __init__(self) -> None:
        super().__init__(timedelta(1), self.select_future_chain_symbols)
        self.symbols = list(categories.keys())
    def select_future_chain_symbols(self, utc_time: datetime) -> List[Symbol]:
        return self.symbols
    def Filter(self, filter: FutureFilterUniverse) -> FutureFilterUniverse:
        return filter.Expiration(0, 365)