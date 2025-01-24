import os
import threading
import tkinter as tk
from functools import partial
from config import Config
from api import BinanceAPI
from classes import ButtonHandler, DataHandler, UIHelper, UIGridHelper, EntryCreator
from price_fetcher import PriceFetcher
from price_updater import PriceUpdater


class NetValueCalculator:
    @staticmethod
    def calculate_total_profit(entry_data, start_row=0, end_row=30):
        total_profit = 0
        for row in range(start_row, end_row):
            # Ensure to get the latest profit value from entry_data
            profit = entry_data.get(f"row_{row}_profit", 0.0)
            try:
                total_profit += float(profit)  # Sum the profit for each row
            except ValueError:
                pass  # If it's not a valid number, skip it
        return total_profit

    @staticmethod
    def calculate_net_value(total_profit, deposited_value):
        if total_profit is None or deposited_value is None:
            return None
        return total_profit - deposited_value

    @staticmethod
    def format_net_value(net_value):
        if net_value is None:
            return "NET VALUE - $0.00"
        formatted_value = f"NET VALUE - ${net_value:,.2f}" if not net_value.is_integer() else f"NET VALUE - ${int(net_value):,}"
        return formatted_value

    @staticmethod
    def update_net_value(net_value_label, deposited_value, total_profit, config):
        net_value = NetValueCalculator.calculate_net_value(total_profit, deposited_value)
        net_value_display = NetValueCalculator.format_net_value(net_value)
        if net_value_label is not None:
            net_value_label.config(text=net_value_display)
            print(f"Updated Net Value Label: {net_value_display}")

    @staticmethod
    def get_deposited_value(deposited_entry):
        # Ensure you are getting the correct value from the Entry widget
        deposited_text = deposited_entry.get().strip("DEPOSITED $").replace(",", "").strip()
        try:
            return float(deposited_text)  # Convert it to float after cleaning
        except ValueError:
            return 0.0  # Default if conversion fails


class EntryHandler:
    def __init__(self, data_handler, entry_data_middle, entry_data_bottom, binance_api, middle_grid_manager, entry_formatter):
        self.data_handler = data_handler
        self.entry_data_middle = entry_data_middle
        self.entry_data_bottom = entry_data_bottom
        self.binance_api = binance_api
        self.middle_grid_manager = middle_grid_manager
        self.entry_formatter = entry_formatter

    def on_enter_middle(self, event, row, column=None):
        entry_widget = event.widget
        entry_text = entry_widget.get().strip()

        column_handler = ColumnHandler(self.binance_api, self.middle_grid_manager, self.entry_data_middle, self.entry_formatter, self.data_handler)
        column_handler.handle_column(entry_widget, entry_text, row, column)

        self.save_entry_data(self.entry_data_middle, "middle", entry_widget)

    def save_entry_data(self, entry_data, grid_type, entry_widget):
        self.data_handler.save_data(entry_data, grid_type=grid_type)
        entry_widget.master.focus_set()

    def on_enter_bottom(self, event, row, column=None):
        entry_widget = event.widget
        entry_text = entry_widget.get()

        if column == 6 and row == 1:
            DepositHandler(self.entry_formatter, self.entry_data_bottom).handle(entry_widget, entry_text, row)
        else:
            self.entry_data_bottom[f"row_{row}_column_{column}"] = entry_text
        self.data_handler.save_data(self.entry_data_bottom, grid_type="bottom")
        entry_widget.master.focus_set()


class ColumnHandler:
    def __init__(self, binance_api, middle_grid_manager, entry_data_middle, entry_formatter, data_handler):
        self.binance_api = binance_api
        self.middle_grid_manager = middle_grid_manager
        self.entry_data_middle = entry_data_middle
        self.entry_formatter = entry_formatter
        self.data_handler = data_handler

    def handle_column(self, entry_widget, entry_text, row, column):
        if column == 1:  # Coin column
            self.handle_coin_column(entry_widget, entry_text, row)
        elif column == 6:  # Invested column
            self.handle_value_column(entry_widget, entry_text, row, "column_6", self.entry_formatter.format_invested_value)
        elif column == 7:  # Holdings column
            self.handle_value_column(entry_widget, entry_text, row, "column_7", self.entry_formatter.format_holdings_value)
        elif column == 8:  # Wallet column
            self.handle_wallet_column(entry_widget, entry_text, row)
        else:  # Generic column
            self.handle_generic_column(entry_widget, entry_text, row, column)

    def handle_coin_column(self, entry_widget, entry_text, row):
        coin_pair = entry_text
        if self.binance_api.is_valid_coin_pair(coin_pair):
            price = self.binance_api.get_coin_price(coin_pair)
            price_text = f"${price}" if price else "Error fetching price"
            self.entry_data_middle[f"row_{row}_price"] = price
            self.middle_grid_manager.create_value_label(row, 2, text=price_text)
        else:
            self.middle_grid_manager.create_value_label(row, 2, text="Invalid coin pair")

    def handle_value_column(self, entry_widget, entry_text, row, column_key, formatter_method):
        formatted_text = formatter_method(entry_text)
        self.entry_data_middle[f"row_{row}_{column_key}"] = formatted_text
        self.entry_formatter.update_entry_widget(entry_widget, formatted_text, row)
        self.save_invested_and_holdings(row)

    def handle_wallet_column(self, entry_widget, entry_text, row):
        wallet_name = entry_text.upper()
        self.entry_data_middle[f"row_{row}_column_8"] = wallet_name
        self.entry_formatter.apply_wallet_color(entry_widget, wallet_name)
        self.entry_formatter.update_entry_widget(entry_widget, wallet_name, row)

    def handle_generic_column(self, entry_widget, entry_text, row, column):
        self.entry_data_middle[f"row_{row}_column_{column}"] = entry_text

    def save_invested_and_holdings(self, row):
        invested = self.entry_data_middle.get(f"row_{row}_column_6", "$0").lstrip("$").replace(",", "")
        holdings = self.entry_data_middle.get(f"row_{row}_column_7", "0").replace(",", "")
        invested, holdings = self.format_values(invested, holdings)
        self.entry_data_middle[f"row_{row}_invested"] = f"${invested:,.2f}"
        self.entry_data_middle[f"row_{row}_holdings"] = holdings
        self.data_handler.save_data(self.entry_data_middle, grid_type="middle")

    def format_values(self, invested, holdings):
        invested = self.safe_float_conversion(invested)
        holdings = self.safe_float_conversion(holdings)
        return invested, holdings

    def safe_float_conversion(self, value):
        try:
            return float(value) if value else 0.0
        except ValueError:
            return 0.0


class DepositHandler:
    def __init__(self, entry_formatter, entry_data_bottom):
        self.entry_formatter = entry_formatter
        self.entry_data_bottom = entry_data_bottom

    def handle(self, entry_widget, entry_text, row):
        deposited_amount = entry_text.strip("DEPOSITED $").strip()
        formatted_deposit = self.format_deposit(deposited_amount)
        self.entry_data_bottom[f"row_{row}_column_6"] = float(deposited_amount)
        entry_widget.config(bg="lightgreen")
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, formatted_deposit)

    def format_deposit(self, deposited_amount):
        try:
            return f"DEPOSITED ${float(deposited_amount):,.2f}"
        except ValueError:
            return "Invalid deposit"


class EntryFormatter:
    def __init__(self, wallet_colors):
        self.wallet_colors = wallet_colors

    def format_value(self, entry_text, precision=8, symbol="$"):
        """Generic method to format values, including precision handling."""
        try:
            value = float(entry_text.replace(",", ""))
            formatted_value = f"{symbol}{value:,.{precision}f}"

            if formatted_value.endswith('.00'):
                formatted_value = formatted_value[:-3]
            elif formatted_value.endswith('0'):
                formatted_value = formatted_value.rstrip('0')

            return formatted_value
        except ValueError:
            return f"{symbol}0.00"

    def format_invested_value(self, entry_text):
        return self.format_value(entry_text)

    def format_holdings_value(self, entry_text):
        return self.format_value(entry_text, precision=8, symbol="")

    def update_entry_widget(self, entry_widget, formatted_text, row):
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, formatted_text)
        entry_widget.icursor("end")

        row_color = self.get_row_color(row)
        entry_widget.config(bg=row_color)
        UIHelper.adjust_font_color(entry_widget, row_color)

    def get_row_color(self, row):
        purple_shades = UIHelper.generate_purple_shades(30)
        return purple_shades[row]

    def apply_wallet_color(self, entry_widget, wallet_name):
        color = self.wallet_colors.get(wallet_name, "lightgrey")
        entry_widget.config(bg=color)
        UIHelper.adjust_font_color(entry_widget, color)


def format_deposit(value):
    try:
        value = float(value) if value else 0.0
    except ValueError:
        value = 0.0
    if value.is_integer():
        return f"DEPOSITED ${int(value):,}"
    else:
        return f"DEPOSITED ${value:,.2f}"


class GridManagerBase:
    def __init__(self, config):
        self.config = config
        self.ui_grid_helper = UIGridHelper(self.config.root, self.config, self.config.focus_handler.on_focus_in, self.config.focus_handler.on_focus_out)
        self.entry_creator = EntryCreator(self.config.root, self.config, self.config.focus_handler.on_focus_in, self.config.focus_handler.on_focus_out)
        self.entries_middle = []
        self.entries_bottom = []
        self.net_value_label = self.create_value_label(row=0, col=0, text="NET VALUE - $0.00")

    def create_value_label(self, row, col, text="", bg_color=None):
        return self.ui_grid_helper.create_value_label(row, col, text=text, bg_color=bg_color)

    def create_wallet_entry(self, row, col, entry_data, entries, color_map, on_enter, on_focus_out):
        return self.ui_grid_helper.create_wallet_entry_middle(row, col, entry_data, color_map, entries, on_enter,
                                                              on_focus_out)

    def create_entry(self, row, col, column_id, entry_data, entries, enforce_dollar_sign, on_enter):
        self.entry_creator.create_entry(row, col, column_id, entry_data, entries, enforce_dollar_sign, on_enter)

    def update_net_value(self, deposited_value: float, total_profit: float):
        # Calls static method in NetValueCalculator to update net value label
        NetValueCalculator.update_net_value(self.net_value_label, deposited_value, total_profit, self.config)


class TopGridManager(GridManagerBase):
    def __init__(self, config):
        super().__init__(config)

    def setup_top_grid(self):
        headers = ["COINS", "ICONS", "PRICE", "BREAK EVEN", "BALANCE", "PROFIT", "INVESTED", "HOLDINGS", "WALLET"]
        purple_shades = UIHelper.generate_purple_shades(9)
        for i in range(9):
            label = tk.Label(self.config.root, bg=purple_shades[i], text=headers[i], font=("Arial", 32), fg="white",
                             anchor="center", bd=2, relief="solid", highlightbackground="lavender",
                             highlightthickness=1)
            label.place(x=i * self.config.column_width_top, y=0, width=self.config.column_width_top, height=self.config.strip_height)
            UIHelper.adjust_font_color(label, purple_shades[i])


class MiddleGridManager(GridManagerBase):
    def __init__(self, config, deposited_entry=None):
        super().__init__(config)
        self.deposited_entry = deposited_entry  # Store deposited_entry if passed

    def setup_middle_grid(self, on_enter_middle):
        total_height = self.config.screen_height - 2 * self.config.strip_height
        row_height_middle = total_height // 30
        remaining_height = total_height - (row_height_middle * 30)
        extra_height_per_row = remaining_height // 30
        row_height_middle += extra_height_per_row
        purple_shades = UIHelper.generate_purple_shades(30)
        for row in range(30):
            row_color = purple_shades[row]
            for col in range(9):
                self.create_entry_or_label(row, col, row_color, purple_shades, row_height_middle, on_enter_middle)

    # Add a method for setting the deposited entry
    def set_deposited_entry(self, deposited_value):
        self.deposited_entry = deposited_value


    def create_entry_or_label(self, row, col, row_color, purple_shades, row_height_middle, on_enter_middle):
        if col == 0:
            self.create_name_entry(row, row_color, on_enter_middle, row_height_middle)
        elif col == 1:
            self.create_value_label(row, col, text="", bg_color=row_color)
        elif col == 2:
            price = self.config.entry_data_middle.get(f"row_{row}_price", "")
            self.create_value_label(row, col, text=f"${price}" if price else "", bg_color=row_color)
        elif col in [3, 4, 5]:
            self.create_value_label(row, col, text="$0.00", bg_color=row_color)
        elif col == 6:
            self.entry_creator.create_entry(row, col, 6, self.config.entry_data_middle, self.entries_middle,
                                            self.entry_creator.enforce_dollar_sign, on_enter_middle)
        elif col == 7:
            self.entry_creator.create_entry(row, col, 7, self.config.entry_data_middle, self.entries_middle,
                                            self.entry_creator.enforce_dollar_sign, on_enter_middle)
        elif col == 8:
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
    def __init__(self, config, price_updater=None, net_value_calculator=None):
        super().__init__(config)
        self.config = config
        self.deposited_entry = None
        self.net_value_label = None
        self.price_updater = price_updater
        self.net_value_calculator = net_value_calculator
        self.first_update = True  # Flag for first update

    def set_updater_and_calculator(self, price_updater, net_value_calculator):
        # This method sets the updater and calculator after initialization
        self.price_updater = price_updater
        self.net_value_calculator = net_value_calculator

    def setup_bottom_grid(self, on_enter_bottom):
        # Setup net value label and deposited entry
        self.net_value_label = tk.Label(self.config.root, bg="purple", text="NET VALUE - $0", font=("Arial", 35),
                                        fg="white", anchor="center", bd=2, relief="solid",
                                        highlightbackground="lavender",
                                        highlightthickness=1)
        self.net_value_label.place(x=0, y=self.config.screen_height - self.config.strip_height,
                                   width=self.config.column_width_bottom, height=self.config.strip_height)
        UIHelper.adjust_font_color(self.net_value_label, "purple")

        deposited_value = self.config.entry_data_bottom.get("row_1_column_6", 0.0)
        try:
            deposited_value = float(deposited_value)
        except ValueError:
            deposited_value = 0.0
        deposited_value_display = f"DEPOSITED ${deposited_value:,.2f}" if not deposited_value.is_integer() else f"DEPOSITED ${int(deposited_value):,}"
        self.deposited_entry = tk.Entry(self.config.root, font=("Arial", 35), fg="black", bg="lime", justify="center",
                                        relief="solid", bd=2)
        self.deposited_entry.insert(0, deposited_value_display)
        self.deposited_entry.place(x=self.config.column_width_bottom,
                                   y=self.config.screen_height - self.config.strip_height,
                                   width=self.config.column_width_bottom, height=self.config.strip_height)
        UIHelper.adjust_font_color(self.deposited_entry, "lime")

        # This will trigger net value update when price fetching is done
        if self.price_updater:
            self.price_updater.on_price_fetched_callback = self.update_net_value

        self.deposited_entry.bind("<KeyRelease>", lambda event: self.update_net_value())
        self.deposited_entry.bind("<Return>", lambda event, entry_widget=self.deposited_entry:
                                  on_enter_bottom(event, 1, 6))

        self.update_net_value()  # Initially called here

    def update_net_value(self, deposited_value=None, total_profit=None):
        if self.first_update:
            self.first_update = False  # Set flag to False after first update

            # Introduce a short delay for the first update (e.g., 0.5 seconds)
            self.config.root.after(500, self._do_update_net_value, deposited_value, total_profit)
        else:
            # If not the first update, call the update immediately
            self._do_update_net_value(deposited_value, total_profit)

    def _do_update_net_value(self, deposited_value=None, total_profit=None):
        if deposited_value is None:
            deposited_value = NetValueCalculator.get_deposited_value(self.deposited_entry)
        if total_profit is None:
            total_profit = self.net_value_calculator.calculate_total_profit(self.config.entry_data_bottom)

        # Now update the net value label
        NetValueCalculator.update_net_value(self.net_value_label, deposited_value, total_profit, self.config)


class EntryFocusHandler:
    def __init__(self, entry_data_middle, wallet_colors, data_handler, entry_data_updater):
        self.entry_data_middle = entry_data_middle
        self.wallet_colors = wallet_colors
        self.data_handler = data_handler
        self.entry_data_updater = entry_data_updater
        self.original_bg_colors = {}

    def on_focus_in(self, event, entry):
        self.store_original_bg_color(entry)
        self.highlight_entry(entry)

    def on_focus_out(self, row, column, entry):
        value = entry.get().strip()
        caret_position = entry.index(tk.INSERT)
        original_bg_color = self.original_bg_colors.get(entry, entry.cget("bg"))
        self.entry_data_updater.update_entry_data(row, column, value)
        self.restore_caret_position(entry, caret_position)
        self.restore_background_color(row, column, entry, original_bg_color)
        self.data_handler.save_data(self.entry_data_middle, grid_type="middle")
        entry.master.focus_set()

    def store_original_bg_color(self, entry):
        self.original_bg_colors[entry] = entry.cget("bg")

    def highlight_entry(self, entry):
        if entry.get() in ["DEPOSITED $0", "$0", "0"]:
            entry.delete(0, tk.END)
        entry.config(bg="#e3f2fd", fg="black")

    def restore_caret_position(self, entry, caret_position):
        entry.icursor(caret_position)

    def restore_background_color(self, row, column, entry, original_bg_color):
        if column != 8:
            if column in [6, 7]:
                purple_shades = UIHelper.generate_purple_shades(30)
                row_color = purple_shades[row]
                entry.config(bg=row_color)
            else:
                entry.config(bg=original_bg_color)


class EntryDataUpdater:
    def __init__(self, entry_data_middle, wallet_colors):
        self.entry_data_middle = entry_data_middle
        self.wallet_colors = wallet_colors

    def update_entry_data(self, row, column, value):
        formatted_value = self.format_value(value, column)
        if column == 1:
            self.entry_data_middle[f"row_{row}_name"] = value.upper()
        elif column == 6:
            self.entry_data_middle[f"row_{row}_column_6"] = formatted_value
        elif column == 7:
            self.entry_data_middle[f"row_{row}_column_7"] = formatted_value
        elif column == 8:
            self.entry_data_middle[f"row_{row}_column_8_middle"] = value.upper()
            self.update_wallet_color(row, column, value)
        else:
            self.entry_data_middle[f"row_{row}_column_{column}"] = value
        self.update_entry_widget(row, column, formatted_value)

    def update_entry_widget(self, row, column, formatted_value):
        entry_widget = self.get_entry_widget(row, column)
        if entry_widget:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, formatted_value)
            entry_widget.icursor("end")

    def update_wallet_color(self, row, column, value):
        entry_widget = self.get_entry_widget(row, column)
        if entry_widget is None:
            return
        color = self.wallet_colors.get(value.upper(), "lightgrey")
        entry_widget.config(bg=color)
        UIHelper.adjust_font_color(entry_widget, color)

    def get_entry_widget(self, row, column):
        try:
            return self.entry_data_middle[f"row_{row}_column_{column}_widget"]
        except KeyError:
            return None

    def format_value(self, value, column):
        if column == 6:
            return self.format_invested_value(value)
        elif column == 7:
            return self.format_holdings_value(value)
        return value

    def format_invested_value(self, value):
        raw_value = value.lstrip("$").replace(",", "")
        try:
            value_float = float(raw_value)
            return f"${value_float:,.2f}".rstrip("0").rstrip(".")
        except ValueError:
            return "$0.00"

    def format_holdings_value(self, value):
        raw_value = value.replace(",", "")
        try:
            value_float = float(raw_value)
            return f"{value_float:,.2f}".rstrip("0").rstrip(".")
        except ValueError:
            return "0"


class CryptoTrackerAppCore:
    def __init__(self, root):
        self.root = root
        self.configure_root()  # Make sure this is called to set fullscreen
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

    def configure_root(self):
        self.root.attributes("-fullscreen", True)  # Ensure fullscreen is enabled here
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
        self.entry_data_updater = EntryDataUpdater(self.entry_data_middle, self.wallet_colors)
        self.entry_focus_handler = EntryFocusHandler(
            self.entry_data_middle, self.wallet_colors, self.data_handler, self.entry_data_updater
        )
        self.config = Config(
            self.root, self.screen_width, self.screen_height, self.strip_height,
            self.screen_width / 9, self.screen_width / 9, self.screen_width / 4,
            self.wallet_colors, self.entry_data_middle, self.entry_data_bottom,
            self.data_handler, self.entry_focus_handler, None
        )

    def initialize_grid_managers(self):
        # Initialize other grid managers first
        self.middle_grid_manager = MiddleGridManager(self.config)
        self.top_grid_manager = TopGridManager(self.config)

        # Initialize BottomGridManager (with no price_updater or net_value_calculator yet)
        self.bottom_grid_manager = BottomGridManager(self.config)

        # Initialize NetValueCalculator
        self.net_value_calculator = NetValueCalculator()

        # Initialize PriceUpdater with BottomGridManager (not MiddleGridManager)
        self.price_updater = PriceUpdater(self.config.entry_data_bottom, self.bottom_grid_manager, self.config.root)

        # Set PriceUpdater and NetValueCalculator in BottomGridManager
        self.bottom_grid_manager.set_updater_and_calculator(self.price_updater, self.net_value_calculator)

    def initialize_price_fetcher(self):
        self.price_fetcher = PriceFetcher(
            self.binance_api,
            self.entry_data_middle,
            self.middle_grid_manager,
            self.data_handler,
            self.root
        )

    def initialize_button_handler(self):
        self.config.button_handler = ButtonHandler(
            self.root, self.screen_width, self.screen_height, self.screen_width / 4,
            self.strip_height, self.entry_focus_handler,
            self.price_fetcher, self.middle_grid_manager
        )


class CryptoTrackerAppUI:
    def __init__(self, root, core_initializer):
        self.root = root
        self.core_initializer = core_initializer

        self.initialize_entry_formatter()
        self.initialize_entry_handler()
        self.setup_grid()
        self.start_fetching_prices()

    def initialize_entry_formatter(self):
        self.entry_formatter = EntryFormatter(self.core_initializer.wallet_colors)

    def initialize_entry_handler(self):
        self.entry_handler = EntryHandler(
            self.core_initializer.data_handler, self.core_initializer.entry_data_middle,
            self.core_initializer.entry_data_bottom, self.core_initializer.binance_api,
            self.core_initializer.middle_grid_manager,
            self.entry_formatter
        )

    def setup_grid(self):
        self.core_initializer.top_grid_manager.setup_top_grid()
        self.core_initializer.middle_grid_manager.setup_middle_grid(self.entry_handler.on_enter_middle)
        self.core_initializer.bottom_grid_manager.setup_bottom_grid(self.entry_handler.on_enter_bottom)

        self.core_initializer.config.button_handler.create_exit_button(self.core_initializer.screen_width,
                                                                      self.core_initializer.screen_height,
                                                                      self.core_initializer.screen_width / 4,
                                                                      self.core_initializer.strip_height)
        self.core_initializer.config.button_handler.create_gmt_button(self.core_initializer.screen_width,
                                                                     self.core_initializer.screen_height,
                                                                     self.core_initializer.screen_width / 4,
                                                                     self.core_initializer.strip_height)

    def start_fetching_prices(self):
        threading.Thread(target=self.core_initializer.price_fetcher.start_fetching_prices, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()

    # Initialize the core setup (data loading, API setup, etc.)
    core_initializer = CryptoTrackerAppCore(root)

    # Initialize the UI setup (grid setup, buttons, etc.)
    app_ui = CryptoTrackerAppUI(root, core_initializer)

    # Start the Tkinter main loop
    root.mainloop()
