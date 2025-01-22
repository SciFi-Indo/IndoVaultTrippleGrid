from binance.client import Client


class BinanceAPI:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

        # Initialize the Binance client using the API key and secret
        self.client = Client(self.api_key, self.api_secret)

    def is_valid_coin_pair(self, coin_pair):
        """Check if the coin pair is valid on Binance."""
        try:
            exchange_info = self.client.get_exchange_info()  # Fetch exchange info
            symbols = exchange_info.get('symbols', [])

            print(f"Total available symbols: {len(symbols)}")  # Debugging the number of available symbols

            # Check if the coin pair exists in available symbols (case-insensitive)
            coin_pair = coin_pair.upper()  # Ensure the coin pair is in uppercase
            is_valid = any(symbol['symbol'] == coin_pair for symbol in symbols)

            if not is_valid:
                print(f"Coin pair {coin_pair} not found in available symbols.")  # Debug print
            else:
                print(f"Coin pair {coin_pair} is valid.")  # Debug print

            return is_valid

        except Exception as e:
            print(f"Error while checking coin pair {coin_pair}: {e}")
            return False