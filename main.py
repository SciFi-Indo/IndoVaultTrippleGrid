import os
import math
import threading
import tkinter as tk
import time
import queue
from functools import partial
from binance.exceptions import BinanceAPIException
from config import Config
from api import BinanceAPI
from classes import ButtonHandler, DataHandler, UIHelper, UIGridHelper


class EntryHandler:
    def __init__(self, data_handler, entry_data_middle, entry_data_bottom, binance_api, middle_grid_manager):
        self.data_handler = data_handler
        self.entry_data_middle = entry_data_middle
        self.entry_data_bottom = entry_data_bottom
        self.binance_api = binance_api
        self.middle_grid_manager = middle_grid_manager

    def on_enter_middle(self, event, row, column=None):
        entry_widget = event.widget
        entry_text = entry_widget.get().strip()

        if column == 1:  # COINS column
            coin_pair = entry_text
            if self.binance_api.is_valid_coin_pair(coin_pair):
                try:
                    price = self.binance_api.get_coin_price(coin_pair)
                    if price:
                        self.entry_data_middle[f"row_{row}_price"] = price
                        self.entry_data_middle[f"row_{row}_column_2"] = f"${price}"
                        self.middle_grid_manager.create_value_label(row, 2, text=f"${price}")
                    else:
                        self.middle_grid_manager.create_value_label(row, 2, text="Error fetching price")
                except Exception:
                    self.middle_grid_manager.create_value_label(row, 2, text="Error fetching price")
            else:
                self.middle_grid_manager.create_value_label(row, 2, text="Invalid coin pair")

        elif column == 6:  # INVESTED column (now in column 6, formerly column 5)
            entry_text = "$" + entry_text.lstrip("0") if not entry_text.startswith("$") else entry_text
            self.entry_data_middle[f"row_{row}_column_6"] = entry_text or "$0"
            self.save_invested_and_holdings(row)

        elif column == 5:  # PROFIT column (now in column 5, formerly column 6)
            # Here, we will calculate and update the profit based on the formula
            invested = self.entry_data_middle.get(f"row_{row}_column_6", "$0")
            holdings = self.entry_data_middle.get(f"row_{row}_column_8", "0")

            invested_value = float(invested.lstrip('$') if invested else 0)
            holdings_value = float(holdings if holdings else 0)
            if invested_value and holdings_value:
                profit = (invested_value * holdings_value) - invested_value
                self.entry_data_middle[f"row_{row}_column_5"] = f"${profit:.2f}"
                self.middle_grid_manager.create_value_label(row, 5, f"${profit:.2f}")
            else:
                self.middle_grid_manager.create_value_label(row, 5, "Invalid")

        elif column == 8:  # This is for HOLDINGS column
            entry_text = entry_text.lstrip("$") or "0"  # Strip leading $ and default to 0 if empty
            self.entry_data_middle[f"row_{row}_column_8"] = entry_text
            self.save_invested_and_holdings(row)

        else:
            self.entry_data_middle[f"row_{row}_column_{column}"] = entry_text

        self.data_handler.save_data(self.entry_data_middle, grid_type='middle')
        entry_widget.master.focus_set()

    def save_invested_and_holdings(self, row):
        # Get INVESTED and HOLDINGS from the relevant columns
        invested = self.entry_data_middle.get(f"row_{row}_column_6", 0).lstrip('$')
        holdings = self.entry_data_middle.get(f"row_{row}_column_8", 0)

        # Convert holdings to string to handle potential integer values
        invested = str(invested).replace('$', '')  # Removing the dollar sign if present
        holdings = str(holdings)  # Ensure holdings is treated as a string

        # Ensure both are valid numbers
        invested = float(invested) if invested.replace(".", "", 1).isdigit() else 0.0
        holdings = float(holdings) if holdings.replace(".", "", 1).isdigit() else 0.0

        # Save the values
        self.entry_data_middle[f"row_{row}_invested"] = invested
        self.entry_data_middle[f"row_{row}_holdings"] = holdings

        # Save to the data file
        self.data_handler.save_data(self.entry_data_middle, grid_type='middle')

    def on_enter_bottom(self, event, row, column=None):
        entry_widget = event.widget
        entry_text = entry_widget.get()

        if column == 6 and row == 1:
            deposited_amount = entry_text.strip("DEPOSITED $").strip()
            self.entry_data_bottom[f"row_{row}_column_6"] = deposited_amount
            entry_widget.config(bg="lightgreen")
        else:
            self.entry_data_bottom[f"row_{row}_column_{column}"] = entry_text

        self.data_handler.save_data(self.entry_data_bottom, grid_type='bottom')
        entry_widget.master.focus_set()


class GridManagerBase:
    def __init__(self, config):
        self.config = config
        self.ui_grid_helper = UIGridHelper(self.config.root, self.config, self.config.focus_handler.on_focus_in, self.config.focus_handler.on_focus_out)
        self.entries_middle = []
        self.entries_bottom = []

    def create_value_label(self, row, col, text="", bg_color=None):
        return self.ui_grid_helper.create_value_label(row, col, text=text, bg_color=bg_color)

    def create_wallet_entry(self, row, col, entry_data, entries, color_map, on_enter, on_focus_out):
        return self.ui_grid_helper.create_wallet_entry_middle(row, col, entry_data, color_map, entries, on_enter,
                                                               on_focus_out)

    def create_entry(self, row, col, column_id, entry_data, entries, enforce_dollar_sign, on_enter):
        return self.ui_grid_helper.create_entry(row, col, column_id, entry_data, entries, enforce_dollar_sign,
                                                 on_enter)


class TopGridManager(GridManagerBase):
    def __init__(self, config):
        super().__init__(config)

    def setup_top_grid(self):
        headers = ["COINS", "ICONS", "PRICE", "BREAK EVEN", "BALANCE", "PROFIT", "INVESTED", "HOLDINGS", "WALLET"]  # Updated order
        purple_shades = UIHelper.generate_purple_shades(9)
        for i in range(9):
            label = tk.Label(self.config.root, bg=purple_shades[i], text=headers[i], font=("Arial", 32), fg="white",
                             anchor="center", bd=2, relief="solid", highlightbackground="lavender",
                             highlightthickness=1)
            label.place(x=i * self.config.column_width_top, y=0, width=self.config.column_width_top, height=self.config.strip_height)
            UIHelper.adjust_font_color(label, purple_shades[i])


class MiddleGridManager(GridManagerBase):
    def __init__(self, config):
        super().__init__(config)

    def setup_middle_grid(self, on_enter_middle):
        total_height = self.config.screen_height - 2 * self.config.strip_height
        row_height_middle = total_height // 30
        remaining_height = total_height - (row_height_middle * 30)
        extra_height_per_row = remaining_height // 30
        row_height_middle += extra_height_per_row
        purple_shades = UIHelper.generate_purple_shades(30)

        for row in range(30):
            row_color = purple_shades[row]  # Color for the row (used in all columns)
            for col in range(9):
                self.create_entry_or_label(row, col, row_color, purple_shades, row_height_middle, on_enter_middle)

    def create_entry_or_label(self, row, col, row_color, purple_shades, row_height_middle, on_enter_middle):
        if col == 0:
            self.create_name_entry(row, row_color, on_enter_middle, row_height_middle)
        elif col == 1:
            self.create_value_label(row, col, text="", bg_color=row_color)  # ICONS column
        elif col == 2:  # PRICE column
            coin_pair = self.config.entry_data_middle.get(f"row_{row}_column_0", "")
            if coin_pair:
                price = self.config.entry_data_middle.get(f"row_{row}_price")
                if price:
                    self.create_value_label(row, col, text=f"${price}", bg_color=row_color)
                else:
                    self.create_value_label(row, col, text="", bg_color=row_color)
            else:
                self.create_value_label(row, col, text="", bg_color=row_color)
        elif col == 3:  # BREAK EVEN column
            # Display "$0.00" initially
            self.create_value_label(row, col, text="$0.00", bg_color=row_color)
        elif col == 4:  # BALANCE column
            # Display "$0.00" initially
            self.create_value_label(row, col, text="$0.00", bg_color=row_color)
        elif col == 5:  # PROFIT column (formerly column 6)
            self.create_value_label(row, col, text="$0.00", bg_color=row_color)
        elif col == 6:  # INVESTED column (formerly column 5)
            self.ui_grid_helper.create_entry(row, col, 6, self.config.entry_data_middle, self.entries_middle,
                                             self.ui_grid_helper.enforce_dollar_sign, on_enter_middle)
        elif col == 7:  # HOLDINGS column (entry)
            self.ui_grid_helper.create_entry(row, col, 8, self.config.entry_data_middle, self.entries_middle,
                                             self.ui_grid_helper.enforce_dollar_sign, on_enter_middle)
        elif col == 8:  # WALLET column (entry)
            self.create_wallet_entry(row, col, self.config.entry_data_middle, self.entries_middle,
                                     self.config.wallet_colors, on_enter_middle,
                                     self.config.focus_handler.on_focus_out)
        else:
            self.create_value_label(row, col, text="", bg_color=row_color)


    def create_name_entry(self, row, row_color, on_enter_middle, row_height_middle):
        purple_shades = UIHelper.generate_purple_shades(30)
        row_color = purple_shades[row]
        entry_height = (self.config.screen_height - 2 * self.config.strip_height) / 30
        col_width_middle = self.config.column_width_middle
        entry_width = col_width_middle

        entry = tk.Entry(self.config.root, font=("Helvetica", 15, "bold"), fg="black", bg=row_color, justify="center",
                         relief="flat", bd=0)

        entry.place(
            x=0,
            y=self.config.strip_height + row * entry_height,
            width=entry_width,
            height=entry_height
        )

        if f"row_{row}_name" in self.config.entry_data_middle:
            entry.insert(0, self.config.entry_data_middle[f"row_{row}_name"])

        self.entries_middle.append(entry)

        entry.bind("<Return>", partial(on_enter_middle, row=row, column=1))

        UIHelper.adjust_font_color(entry, row_color)

        entry.bind("<FocusIn>", partial(self.config.focus_handler.on_focus_in, entry=entry))
        entry.bind("<FocusOut>", lambda event: self.config.focus_handler.on_focus_out(row=row, column=1, entry=entry))


class BottomGridManager(GridManagerBase):
    def __init__(self, config):
        super().__init__(config)

    def setup_bottom_grid(self, on_enter_bottom):
        net_value_label = tk.Label(self.config.root, bg="purple", text="NET VALUE - $0", font=("Arial", 60), fg="white",
                                   anchor="center", bd=2, relief="solid", highlightbackground="lavender",
                                   highlightthickness=1)
        net_value_label.place(x=0, y=self.config.screen_height - self.config.strip_height, width=self.config.column_width_bottom,
                              height=self.config.strip_height)
        UIHelper.adjust_font_color(net_value_label, "purple")

        deposited_value = self.config.entry_data_bottom.get("row_1_column_6", "0")
        deposited_value_display = f"DEPOSITED ${deposited_value}"
        deposited_entry = tk.Entry(self.config.root, font=("Arial", 40), fg="black", bg="lime", justify="center",
                                   relief="solid", bd=2)
        deposited_entry.insert(0, deposited_value_display)
        deposited_entry.place(x=self.config.column_width_bottom, y=self.config.screen_height - self.config.strip_height,
                              width=self.config.column_width_bottom, height=self.config.strip_height)
        UIHelper.adjust_font_color(deposited_entry, "lime")
        deposited_entry.bind("<KeyRelease>", lambda event, entry_widget=deposited_entry:
                             self.config.button_handler.on_deposited_keyrelease(event, entry_widget))
        deposited_entry.bind("<Return>", lambda event, entry_widget=deposited_entry:
                             on_enter_bottom(event, 1, 6))


class FocusHandler:
    def __init__(self, entry_data_middle, wallet_colors, data_handler):
        self.entry_data_middle = entry_data_middle
        self.wallet_colors = wallet_colors
        self.data_handler = data_handler
        self.original_bg_colors = {}  # Dictionary to track the original background colors

    def on_focus_in(self, event, entry):
        # Store the original background color before making changes
        self.original_bg_colors[entry] = entry.cget("bg")

        if entry.get() in ["DEPOSITED $0", "$0", "0"]:
            entry.delete(0, tk.END)
        entry.config(bg="#e3f2fd", fg="black")

    def on_focus_out(self, row, column, entry):
        value = entry.get().strip().upper()

        # Retrieve the original background color from the dictionary (or use default if not found)
        original_bg_color = self.original_bg_colors.get(entry, entry.cget("bg"))

        # Logic for handling "invested" and "holdings" columns
        if column == 1:  # If it's a coin name (column 1)
            self.entry_data_middle[f"row_{row}_name"] = value
        elif column == 9:  # If it's the holdings column (column 9)
            entry_key = f"row_{row}_column_9_middle"
            self.entry_data_middle[entry_key] = value
            color = self.wallet_colors.get(value, "lightgrey")
            entry.config(bg=color)
            UIHelper.adjust_font_color(entry, color)

        # If it's any other column, restore its original background color
        entry.config(bg=original_bg_color)

        self.data_handler.save_data(self.entry_data_middle, grid_type='middle')
        entry.master.focus_set()


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
        self.thresholds = [
            (1, 2),
            (0.01, 3),
            (0.001, 4),
            (0.0001, 5),
            (0.00001, 6),
            (0.000001, 7),
            (0.0000001, 8),
        ]

        # Track total fetches and attempts across all minutes
        self.total_fetches = 0
        self.total_attempts = 0

        # Track fetches and attempts for the current minute
        self.total_fetches_last_minute = 0
        self.total_attempts_last_minute = 0

        self.minute_counter = 0
        self.start_time = time.time()

    def start_fetching_prices(self):
        """Start fetching prices continuously."""
        if not self.fetch_thread or not self.fetch_thread.is_alive():
            self.fetch_thread = threading.Thread(target=self.fetch_prices, daemon=True)
            self.fetch_thread.start()

    def fetch_prices(self):
        """Fetch the prices for the coins continuously every 2 seconds."""
        while not self.exit_flag.is_set():
            for row in range(30):
                coin_name = self.entry_data.get(f"row_{row}_name", "").strip()
                if coin_name:
                    formatted_price, raw_price = self.fetch_coin_price(coin_name)
                    self.total_attempts_last_minute += 1
                    if formatted_price:
                        self.update_price(row, formatted_price, raw_price)
                        self.total_fetches_last_minute += 1
                    else:
                        self.queue.put(('update_price', row, 2, "Invalid"))
                else:
                    self.queue.put(('update_price', row, 2, "Loading..."))

            self.process_queue()

            if self.all_prices_fetched():
                self.short_cooldown()  # Skip the long cooldown after fetching the full list
            else:
                # Sleep for responsiveness only if not all prices are fetched
                for _ in range(20):  # 20 * 0.1 = 2 seconds total
                    if self.exit_flag.is_set():
                        break
                    time.sleep(0.1)

            self.log_progress()

    def all_prices_fetched(self):
        """Check if all prices have been fetched."""
        return all(self.entry_data.get(f"row_{row}_price", "") != "" for row in range(30))

    def short_cooldown(self):
        """Reduce cooldown time when all prices have been fetched."""
        for _ in range(5):  # Reduce cooldown to 0.5 seconds total
            if self.exit_flag.is_set():
                break
            time.sleep(0.1)  # 0.1 seconds per iteration

    def fetch_coin_price(self, coin_name):
        """Fetch the coin price from Binance and return it in a formatted way."""
        symbol = coin_name.upper().replace(" ", "")
        try:
            price = self.binance_api.client.get_symbol_ticker(symbol=symbol)
            if price and 'price' in price:
                raw_price = float(price['price'])
                return self.format_price(raw_price), raw_price
        except Exception:
            pass
        return None, None

    def format_price(self, raw_price):
        """Format the raw price according to the defined thresholds and add commas for readability."""
        for threshold, decimals in self.thresholds:
            if raw_price >= threshold:
                return self.truncate_price(raw_price, decimals)
        return None

    def truncate_price(self, raw_price, decimals):
        """Truncate the raw price based on the given decimals and format it with commas."""
        truncated_price = round(raw_price, decimals)
        # Format the price with commas if it's >= 1
        return f"{truncated_price:,.2f}" if truncated_price >= 1 else f"{truncated_price:.2f}"

    def update_price(self, row, formatted_price, raw_price):
        """Update the price in the grid and calculate additional fields."""
        self.grid_manager.create_value_label(row, 2, f"${formatted_price}")  # Update the price label (column 2)
        invested, holdings = self.get_invested_and_holdings(row)

        if invested != 0 and holdings != 0:
            break_even, balance, profit = self.calculate_values(invested, holdings, raw_price)
            self.update_labels(row, break_even, balance, profit)
        else:
            self.update_labels(row, "Invalid", "Invalid", "Invalid")

    def get_invested_and_holdings(self, row):
        """Get and parse the INVESTED and HOLDINGS values for the given row."""
        invested = self.entry_data.get(f"row_{row}_invested", 0)
        holdings = self.entry_data.get(f"row_{row}_holdings", 0)
        return self._parse_input_value(invested), self._parse_input_value(holdings)

    def _parse_input_value(self, value):
        """Helper function to clean up and convert input values to float."""
        try:
            value = str(value).strip().replace('$', '').replace(',', '')  # Remove any $ and commas
            return float(value) if value else 0.0
        except ValueError:
            return 0.0

    def calculate_values(self, invested, holdings, raw_price):
        """Calculate the BREAK EVEN, BALANCE, and PROFIT based on the INVESTED and HOLDINGS values."""
        break_even = invested / holdings
        balance = raw_price * holdings
        profit = balance - invested
        return break_even, balance, profit

    def update_labels(self, row, break_even, balance, profit):
        """Update the labels for BREAK EVEN, BALANCE, and PROFIT columns with comma formatting."""
        self.grid_manager.create_value_label(
            row, 3, f"${break_even:,.2f}" if break_even != "Invalid" else "Invalid"  # BREAK EVEN in column 3
        )
        self.grid_manager.create_value_label(
            row, 4, f"${balance:,.2f}" if balance != "Invalid" else "Invalid"  # BALANCE in column 4
        )
        self.grid_manager.create_value_label(
            row, 5, f"${profit:,.2f}" if profit != "Invalid" else "Invalid"  # PROFIT in column 5
        )

    def process_queue(self):
        """Process the queue of price updates."""
        try:
            while True:
                message = self.queue.get_nowait()
                if message[0] == 'update_price':
                    row, col, text = message[1], message[2], message[3]
                    self.grid_manager.create_value_label(row, col, text)
        except queue.Empty:
            pass

    def stop_fetching_prices(self):
        """Stop fetching prices gracefully."""
        self.exit_flag.set()
        if self.fetch_thread and self.fetch_thread.is_alive():
            self.fetch_thread.join(timeout=1.0)

    def log_progress(self):
        """Log progress every minute."""
        current_time = time.time()
        elapsed_time = current_time - self.start_time

        # Check if 60 seconds have passed
        if elapsed_time >= 60:
            self.minute_counter += 1
            self.total_fetches += self.total_fetches_last_minute
            self.total_attempts += self.total_attempts_last_minute

            print(
                f"Minute {self.minute_counter}: {self.total_fetches_last_minute} prices fetched in {self.total_attempts_last_minute} attempts")
            print(f"Total fetches: {self.total_fetches} in total attempts {self.total_attempts}")

            # Reset counters for the next minute
            self.total_fetches_last_minute = 0
            self.total_attempts_last_minute = 0
            self.start_time = current_time  # Reset the start time to the current time


class CryptoTrackerApp:
    def __init__(self, root):
        self.root = root
        self.configure_root()
        self.load_api_keys()
        self.initialize_binance_api()
        self.initialize_data_handler()
        self.load_entry_data()
        self.set_wallet_colors()
        self.configure_screen_dimensions()
        self.initialize_config()
        self.initialize_grid_managers()
        self.initialize_price_fetcher()
        self.initialize_button_handler()
        self.initialize_entry_handler()
        self.setup_grid()
        self.start_fetching_prices()

    def configure_root(self):
        self.root.attributes("-fullscreen", True)
        self.root.title("Crypto Tracker - Static Grids")
        self.root.config(bg="lavender")

    def load_api_keys(self):
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_API_SECRET")
        if not self.api_key or not self.api_secret:
            print("Error: API key or secret is not set in environment variables.")
        else:
            print("API key and secret successfully loaded.")

    def initialize_binance_api(self):
        self.binance_api = BinanceAPI(api_key=self.api_key, api_secret=self.api_secret)

    def initialize_data_handler(self):
        self.data_handler = DataHandler(api_key=self.api_key, api_secret=self.api_secret)

    def load_entry_data(self):
        self.entry_data_middle = self.data_handler.load_data(grid_type='middle')
        self.entry_data_bottom = self.data_handler.load_data(grid_type='bottom')

    def set_wallet_colors(self):
        self.wallet_colors = {
            "TREZOR": "blue", "EXODUS": "green", "NAUTILUS": "yellow", "NEON": "orange", "BINANCE": "red",
            "RABBY": "purple", "NA": "grey", "STOICWALLET": "cyan", "ETICA": "pink"
        }

    def configure_screen_dimensions(self):
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.strip_height = self.screen_height // 10
        remaining_height = self.screen_height - 2 * self.strip_height
        row_height_middle = remaining_height // 30
        if remaining_height - (row_height_middle * 30) > 0:
            row_height_middle += 1

    def initialize_config(self):
        self.config = Config(
            self.root, self.screen_width, self.screen_height, self.strip_height,
            self.screen_width / 9, self.screen_width / 9, self.screen_width / 4,
            self.wallet_colors, self.entry_data_middle, self.entry_data_bottom,
            self.data_handler,
            FocusHandler(self.entry_data_middle, self.wallet_colors, self.data_handler),
            None
        )

    def initialize_grid_managers(self):
        self.top_grid_manager = TopGridManager(self.config)
        self.middle_grid_manager = MiddleGridManager(self.config)  # Ensuring updated column flow
        self.bottom_grid_manager = BottomGridManager(self.config)

    def initialize_price_fetcher(self):
        self.price_fetcher = PriceFetcher(
            self.binance_api, self.entry_data_middle, self.middle_grid_manager, self.data_handler, self.root
        )

    def initialize_button_handler(self):
        self.config.button_handler = ButtonHandler(
            self.root, self.screen_width, self.screen_height, self.screen_width / 4,
            self.strip_height, FocusHandler(self.entry_data_middle, self.wallet_colors, self.data_handler),
            self.price_fetcher, self.middle_grid_manager
        )

    def initialize_entry_handler(self):
        self.entry_handler = EntryHandler(
            self.data_handler, self.entry_data_middle, self.entry_data_bottom, self.binance_api,
            self.middle_grid_manager
        )

    def setup_grid(self):
        self.top_grid_manager.setup_top_grid()
        self.middle_grid_manager.setup_middle_grid(self.entry_handler.on_enter_middle)  # Updated method
        self.bottom_grid_manager.setup_bottom_grid(self.entry_handler.on_enter_bottom)

        self.config.button_handler.create_exit_button(self.screen_width, self.screen_height, self.screen_width / 4,
                                                      self.strip_height)
        self.config.button_handler.create_gmt_button(self.screen_width, self.screen_height, self.screen_width / 4,
                                                     self.strip_height)

    def start_fetching_prices(self):
        # Start the price fetching in a background thread
        threading.Thread(target=self.price_fetcher.start_fetching_prices, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoTrackerApp(root)
    root.mainloop()

