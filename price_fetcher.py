from price_fetcher_worker import PriceFetcherWorker
from progress_logger import ProgressLogger
from price_updater import PriceUpdater
import threading
import queue
import time


class PriceFetcher:
    def __init__(self, binance_api, entry_data, grid_manager, data_handler, root):
        self.binance_api = binance_api
        self.entry_data = entry_data
        self.grid_manager = grid_manager
        self.data_handler = data_handler
        self.root = root
        self.exit_flag = threading.Event()
        self.queue = queue.Queue()
        self.fetch_thread = None
        self.worker = PriceFetcherWorker(self.binance_api, self.entry_data, self.grid_manager, self.queue)
        self.logger = ProgressLogger()

        self.price_updater = PriceUpdater(entry_data, grid_manager, root)

    def start_fetching_prices(self):
        if not self.fetch_thread or not self.fetch_thread.is_alive():
            self.fetch_thread = threading.Thread(target=self.fetch_prices, daemon=True)
            self.fetch_thread.start()

    def fetch_prices(self):
        while not self.exit_flag.is_set():
            for row in range(30):
                coin_name = self.entry_data.get(f"row_{row}_name", "").strip()
                if coin_name:
                    self.logger.total_attempts_last_minute += 1  # Increment the attempt count
                    formatted_price, raw_price = self.worker.fetch_coin_price(coin_name)
                    if formatted_price:
                        self.logger.total_fetches_last_minute += 1  # Increment successful fetch count
                        self.price_updater.update_price(row, formatted_price, raw_price)
                    else:
                        self.queue.put(('update_price', row, 2, "Invalid"))
                else:
                    self.queue.put(('update_price', row, 2, "Loading..."))
            self.process_queue()
            if self.all_prices_fetched():
                self.short_cooldown()
            else:
                for _ in range(20):
                    if self.exit_flag.is_set():
                        break
                    time.sleep(0.1)
            self.logger.log_progress()

    def all_prices_fetched(self):
        return all(self.entry_data.get(f"row_{row}_price", "") != "" for row in range(30))

    def short_cooldown(self):
        for _ in range(5):
            if self.exit_flag.is_set():
                break
            time.sleep(0.1)

    def process_queue(self):
        try:
            while True:
                message = self.queue.get_nowait()
                if message[0] == 'update_price':
                    row, col, text = message[1], message[2], message[3]
                    self.grid_manager.create_value_label(row, col, text)
        except queue.Empty:
            pass

    def stop_fetching_prices(self):
        self.exit_flag.set()
        if self.fetch_thread and self.fetch_thread.is_alive():
            self.fetch_thread.join(timeout=1.0)
