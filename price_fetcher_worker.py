class PriceFetcherWorker:
    def __init__(self, binance_api, entry_data, grid_manager, queue):
        self.binance_api = binance_api
        self.entry_data = entry_data
        self.grid_manager = grid_manager  # This will be passed in, no import necessary
        self.queue = queue
        self.thresholds = [
            (1, 2),
            (0.01, 3),
            (0.001, 4),
            (0.0001, 5),
            (0.00001, 6),
            (0.000001, 7),
            (0.0000001, 8),
        ]

    def fetch_coin_price(self, coin_name):
        symbol = coin_name.upper().replace(" ", "")
        try:
            price = self.binance_api.client.get_symbol_ticker(symbol=symbol)
            if price and 'price' in price:
                raw_price = float(price['price'])
                return self.format_price(raw_price), raw_price
        except Exception as e:
            print(f"Error fetching price for {coin_name}: {e}")
        return None, None

    def format_price(self, raw_price):
        for threshold, decimals in self.thresholds:
            if raw_price >= threshold:
                return self.truncate_price(raw_price, decimals)
        return None

    def truncate_price(self, raw_price, decimals):
        truncated_price = round(raw_price, decimals)
        return f"{truncated_price:,.2f}" if truncated_price >= 1 else f"{truncated_price:.2f}"
