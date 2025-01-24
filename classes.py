import json
import os
import tkinter as tk
from functools import partial
import threading
import queue


class UIHelper:
    @staticmethod
    def is_light_color(color):
        if color.startswith("#"):
            color = color[1:]
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
        else:
            colors = {
                "white": (255, 255, 255), "black": (0, 0, 0), "lightgrey": (211, 211, 211),
                "grey": (169, 169, 169), "red": (255, 0, 0), "blue": (0, 0, 255), "green": (0, 255, 0),
                "yellow": (255, 255, 0), "cyan": (0, 255, 255), "purple": (128, 0, 128),
                "pink": (255, 182, 193), "orange": (255, 165, 0), "violet": (238, 130, 238),
                "indigo": (75, 0, 130), "teal": (0, 128, 128), "lime": (0, 255, 0), "gold": (255, 215, 0),
            }
            r, g, b = colors.get(color.lower(), (0, 0, 0))
        brightness = (r * 0.299 + g * 0.587 + b * 0.114) / 255
        return brightness > 0.5

    @staticmethod
    def get_contrast_color(bg_color):
        if bg_color.startswith("#"):
            color = bg_color[1:]
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
        else:
            colors = {
                "white": (255, 255, 255), "black": (0, 0, 0), "lightgrey": (211, 211, 211),
                "grey": (169, 169, 169), "red": (255, 0, 0), "blue": (0, 0, 255), "green": (0, 255, 0),
                "yellow": (255, 255, 0), "cyan": (0, 255, 255), "purple": (128, 0, 128),
                "pink": (255, 182, 193), "orange": (255, 165, 0), "violet": (238, 130, 238),
                "indigo": (75, 0, 130), "teal": (0, 128, 128), "lime": (0, 255, 0), "gold": (255, 215, 0),
            }
            r, g, b = colors.get(bg_color.lower(), (0, 0, 0))
        brightness = (r * 0.299 + g * 0.587 + b * 0.114) / 255
        return "black" if brightness > 0.5 else "white"

    @staticmethod
    def adjust_font_color(entry_widget, bg_color):
        contrast_color = UIHelper.get_contrast_color(bg_color)
        entry_widget.config(fg=contrast_color)

    @staticmethod
    def adjust_entry_bg_color(entry_widget, wallet_name, wallet_colors):
        color = wallet_colors.get(wallet_name, "lightgrey")  # Default to lightgrey if no match
        entry_widget.config(bg=color)
        UIHelper.adjust_font_color(entry_widget, color)

    @staticmethod
    def generate_purple_shades(num_shades):
        purple_start = (75, 0, 130)
        purple_end = (238, 130, 238)
        shades = []
        for i in range(num_shades):
            r = int(purple_start[0] + (purple_end[0] - purple_start[0]) * (i / (num_shades - 1)))
            g = int(purple_start[1] + (purple_end[1] - purple_start[1]) * (i / (num_shades - 1)))
            b = int(purple_start[2] + (purple_end[2] - purple_start[2]) * (i / (num_shades - 1)))
            shades.append(f"#{r:02x}{g:02x}{b:02x}")
        return shades


class EntryCreator:
    def __init__(self, root, config, on_focus_in, on_focus_out):
        self.root = root
        self.config = config
        self.on_focus_in = on_focus_in
        self.on_focus_out = on_focus_out

    def create_entry(self, row, col, column_id, entry_data, entries, enforce_dollar_sign, on_enter):
        entry = tk.Entry(self.root, font=("Arial", 14, "bold"), fg="black", bg="lightgrey", justify="center", bd=0,
                         relief="flat")
        entry_height = (self.config.screen_height - 2 * self.config.strip_height) / 30
        col_width_middle = self.config.column_width_middle
        purple_shades = UIHelper.generate_purple_shades(30)
        row_color = purple_shades[row]
        entry.config(bg=row_color)
        entry.place(x=int(col * col_width_middle), y=int(self.config.strip_height + row * entry_height),
                    width=int(col_width_middle), height=int(entry_height))
        entry.column_idx = column_id
        saved_value = entry_data.get(f"row_{row}_column_{column_id}", "")
        saved_value_cleaned = ""
        if saved_value:
            saved_value_cleaned = saved_value.replace("$", "").replace(",", "")
            if column_id == 6:
                try:
                    saved_value = f"${float(saved_value_cleaned):,.2f}"
                except ValueError:
                    saved_value = "$0"
            elif column_id == 7:
                try:
                    saved_value = f"{float(saved_value_cleaned):,.2f}"
                except ValueError:
                    saved_value = "0"
        if saved_value_cleaned:
            saved_value = DecimalHelper(self.config).apply_decimal_threshold(float(saved_value_cleaned))
        if column_id == 6 and not saved_value.startswith("$"):
            saved_value = "$" + saved_value
        entry.insert(0, saved_value)
        entries.append(entry)
        entry.bind("<Return>", partial(on_enter, row=row, column=column_id))
        entry.bind("<FocusOut>", lambda event: self.enforce_dollar_sign(entry))  # Enforce dollar sign
        UIHelper.adjust_font_color(entry, row_color)

    def enforce_dollar_sign(self, entry):
        text = entry.get()
        column_idx = getattr(entry, 'column_idx', None)

        if column_idx == 6:
            self.format_dollar_entry(entry, text)
        elif column_idx == 7:
            self.format_general_entry(entry, text)

        entry.icursor(tk.END)

    def format_dollar_entry(self, entry, text):
        if not text.startswith("$"):
            text = "$" + text
        raw_text = text[1:].replace(",", "")
        try:
            if raw_text.replace(".", "", 1).isdigit():
                value = float(raw_text)
                formatted_text = f"${value:,.8f}".rstrip('0').rstrip('.')
                if value == 0:
                    formatted_text = "$0"
            else:
                formatted_text = "$"
        except ValueError:
            formatted_text = "$"

        entry.delete(0, tk.END)
        entry.insert(0, formatted_text)

    def format_general_entry(self, entry, text):
        raw_text = text.replace(",", "")
        try:
            if raw_text.replace(".", "", 1).isdigit():
                value = float(raw_text)
                formatted_text = f"{value:,.8f}".rstrip('0').rstrip('.')
                if formatted_text == "":
                    formatted_text = "0"
            else:
                formatted_text = ""
        except ValueError:
            formatted_text = ""

        entry.delete(0, tk.END)
        entry.insert(0, formatted_text)


class DecimalHelper:
    def __init__(self, config):
        self.config = config
        self.thresholds = [
            (1, 2), (0.01, 3), (0.001, 4), (0.0001, 5), (0.00001, 6), (0.000001, 7), (0.0000001, 8)
        ]

    def apply_decimal_threshold(self, value):
        for threshold_value, decimals in self.thresholds:
            if value >= threshold_value:
                formatted_value = f"{value:,.{decimals}f}"
                return formatted_value.rstrip('0').rstrip('.')
        return f"{value:,.8f}".rstrip('0').rstrip('.')


class UIGridHelper:
    def __init__(self, root, config, on_focus_in, on_focus_out):
        self.root = root
        self.config = config
        self.on_focus_in = on_focus_in
        self.on_focus_out = on_focus_out
        self.existing_labels = {}  # Initialize the dictionary to store existing labels

    def create_default_label(self, row, col, row_color):
        entry_height = (self.config.screen_height - 2 * self.config.strip_height) / 30
        bg_color = "white" if (row + col) % 2 == 0 else "lightgrey"
        label = tk.Label(self.root, bg=bg_color, text=f"R{row + 1} C{col + 1}",
                         font=("Arial", 15), fg="black", anchor="center")
        label.place(
            x=col * self.config.column_width_middle,
            y=self.config.strip_height + row * entry_height,
            width=self.config.column_width_middle,
            height=entry_height
        )
        UIHelper.adjust_font_color(label, bg_color)

    def create_value_label(self, row, col, text="$0", bg_color=None):
        entry_height = (self.config.screen_height - 2 * self.config.strip_height) / 30
        col_width_middle = self.config.column_width_middle
        purple_shades = UIHelper.generate_purple_shades(30)
        if bg_color is None:
            bg_color = purple_shades[row]
        label_key = (row, col)
        if label_key in self.existing_labels:
            label = self.existing_labels[label_key]
            label.config(text=text, bg=bg_color)
        else:
            label = tk.Label(self.root, bg=bg_color, text=text, font=("Arial", 15), fg="black", anchor="center")
            label.place(x=int(col * col_width_middle), y=int(self.config.strip_height + row * entry_height),
                        width=int(col_width_middle), height=int(entry_height))
            self.existing_labels[label_key] = label
        UIHelper.adjust_font_color(label, bg_color)
        if text != "$0" and text != "Loading...":
            self.animate_price_update(row, col, text, label)

    def animate_price_update(self, row, col, text, price_label):
        if col not in [2, 3, 4, 5]:
            return
        flash_color = "yellow"
        if not text or text == "Loading..." or text == "Invalid" or text == "Error":
            flash_color = "yellow"
        else:
            previous_price = self.config.entry_data_middle.get(f"row_{row}_price", None)
            if previous_price is not None:
                try:
                    current_price = float(text[1:])
                    previous_price_value = previous_price if isinstance(previous_price, float) else float(previous_price[1:])
                    if current_price > previous_price_value:
                        flash_color = "green"
                    elif current_price < previous_price_value:
                        flash_color = "red"
                    else:
                        flash_color = "yellow"
                except ValueError:
                    flash_color = "yellow"
            else:
                flash_color = "yellow"
        original_color = price_label.cget("bg")
        price_label.config(bg=flash_color)
        self.root.after(75, lambda: price_label.config(bg=original_color))
        self.config.entry_data_middle[f"row_{row}_price"] = text

    def create_wallet_entry_middle(self, row, col, entry_data_middle, wallet_colors, entries, on_enter_middle,
                                   on_focus_out):
        # Original entry creation logic
        entry = tk.Entry(self.root, font=("Arial", 12, "bold"), fg="black", bg="lightgrey", justify="center")
        entry.place(x=col * self.config.column_width_middle,
                    y=self.config.strip_height + row * (self.config.screen_height - 2 * self.config.strip_height) / 30,
                    width=self.config.column_width_middle,
                    height=(self.config.screen_height - 2 * self.config.strip_height) / 30)

        # Key for entry data retrieval
        entry_key = f"row_{row}_column_8_middle"
        saved_value = entry_data_middle.get(entry_key, "")
        entry.insert(0, saved_value)

        # Store the widget in entry_data_middle for future reference
        entry_data_middle[f"row_{row}_column_8_widget"] = entry
        entries.append(entry)

        # Bind the on_enter and on_focus_out events
        entry.bind("<Return>", partial(on_enter_middle, row=row, column=8))
        entry.bind("<FocusOut>", lambda event: on_focus_out(row=row, column=8, entry=entry))
        entry.bind("<FocusIn>", partial(self.on_focus_in, entry=entry))

        # Apply background color based on wallet name
        wallet_name = saved_value.strip().upper()
        color = wallet_colors.get(wallet_name, "lightgrey")
        entry.config(bg=color)

        # Adjust font color based on background
        UIHelper.adjust_font_color(entry, color)


class ButtonHandler:
    def __init__(self, root, screen_width, screen_height, column_width_bottom, strip_height, focus_handler, price_fetcher, grid_manager):
        self.root = root
        self.on_focus_in = focus_handler.on_focus_in
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.column_width_bottom = column_width_bottom
        self.strip_height = strip_height
        self.price_fetcher = price_fetcher
        self.grid_manager = grid_manager
        self.root.after(100, self.process_queue)

    def stop_all_threads(self):
        print("Stopping all threads...")
        if self.price_fetcher:
            self.price_fetcher.stop_fetching_prices()

    def on_enter(self, event, button):
        button.config(bg="#cc3333", fg="white")

    def on_leave(self, event, button):
        button.config(bg="#ff4d4d", fg="white")

    def on_enter_gmt(self, event, button):
        button.config(bg="#3385cc", fg="white")

    def on_leave_gmt(self, event, button):
        button.config(bg="#4d94ff", fg="white")

    def exit_program(self):
        print("Exit button clicked, stopping threads...")
        self.stop_all_threads()
        # Small after delay or immediate cleanup:
        self.root.after(200, self.cleanup)

    def cleanup(self):
        """Clean up resources and exit the program."""
        self.root.quit()  # This will exit the main loop
        self.root.destroy()  # This will destroy the root window and clean up

    def process_queue(self):
        """Process the queue of price updates."""
        try:
            while True:
                message = self.price_fetcher.queue.get_nowait()
                if message[0] == 'update_price':
                    row, col, text = message[1], message[2], message[3]
                    self.grid_manager.create_value_label(row, col, text)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def gmt_mode(self):
        """Switch to GMT mode after stopping all ongoing processes."""
        print("Switching to GMT mode, stopping ongoing processes...")
        self.stop_all_threads()  # Stop any ongoing threads or processes
        self.root.after(200, self.cleanup_gmt_mode)

    def cleanup_gmt_mode(self):
        """Clean up resources and transition to GMT mode."""
        for widget in self.root.winfo_children():
            widget.place_forget()  # Clear existing widgets
        self.create_exit_button(self.screen_width, self.screen_height,
                                self.column_width_bottom, self.strip_height)

    def on_deposited_keyrelease(self, event, entry_widget):
        text = entry_widget.get()
        cleaned_text = ''.join([char for char in text if char.isdigit() or char == '.'])
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, f"DEPOSITED ${cleaned_text or '0'}")

    def create_exit_button(self, screen_width, screen_height, column_width_bottom, strip_height):
        """Create the exit button and bind event handlers."""
        exit_button = tk.Button(self.root, text="EXIT", font=("Arial", 30), bg="#ff4d4d",
                                fg="white", relief="raised", bd=8,
                                command=self.exit_program,  # No need to pass self.root.price_fetcher
                                activebackground="#ff6666", activeforeground="white")
        exit_button.place(x=3 * column_width_bottom, y=screen_height - strip_height,
                          width=column_width_bottom, height=strip_height)
        exit_button.bind("<Enter>", lambda event: self.on_enter(event, exit_button))
        exit_button.bind("<Leave>", lambda event: self.on_leave(event, exit_button))

    def create_gmt_button(self, screen_width, screen_height, column_width_bottom,
                          strip_height):
        gmt_button = tk.Button(self.root, text="GMT Mode", font=("Arial", 30),
                               bg="#4d94ff", fg="white", relief="raised", bd=8,
                               command=self.gmt_mode, activebackground="#66b3ff",
                               activeforeground="white")
        gmt_button.place(x=2 * column_width_bottom, y=screen_height - strip_height,
                         width=column_width_bottom, height=strip_height)
        gmt_button.bind("<Enter>", lambda event: self.on_enter_gmt(event, gmt_button))
        gmt_button.bind("<Leave>", lambda event: self.on_leave_gmt(event, gmt_button))

    def create_deposited_entry(self, root, crypto_tracker_app, row, col,
                               column_width_bottom, screen_height, strip_height):
        entry = tk.Entry(root, font=("Arial", 12), fg="black", bg="lightgrey", justify="center")
        entry.place(x=col * column_width_bottom, y=strip_height + row *
                                                   (screen_height - 2 * strip_height) / 30,
                    width=column_width_bottom, height=(screen_height - 2 * strip_height) / 30)
        key = f"bottom_row_{row}_column_{col}"
        deposited_value = crypto_tracker_app.entry_data.get(key, "DEPOSITED $0")
        entry.insert(0, deposited_value)
        entry.bind("<KeyRelease>", lambda event: crypto_tracker_app.on_deposited_keyrelease(event, entry))
        entry.bind("<Return>", lambda event: crypto_tracker_app.on_enter(event, row=row, column=col, grid_type="bottom"))
        entry.bind("<FocusIn>", partial(self.on_focus_in, entry=entry))
        return entry


class DataHandler:
    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.middle_grid_file_path = r"C:\Users\lette\PycharmProjects\IndoVaultTrippleGrid\middle_grid_data.json"
        self.bottom_grid_file_path = r"C:\Users\lette\PycharmProjects\IndoVaultTrippleGrid\bottom_grid_data.json"
        if self.api_key and self.api_secret:
            from api import BinanceAPI
            self.binance_api = BinanceAPI(api_key=self.api_key, api_secret=self.api_secret)
        else:
            self.binance_api = None

    def load_data(self, grid_type='middle'):
        file_path = self.middle_grid_file_path if grid_type == 'middle' else self.bottom_grid_file_path
        if not os.path.exists(file_path):
            return {}
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data
        except Exception:
            return {}

    def save_data(self, entry_data, grid_type='middle'):
        file_path = self.middle_grid_file_path if grid_type == 'middle' else self.bottom_grid_file_path
        cleaned_data = {key: value for key, value in entry_data.items() if not isinstance(value, tk.Entry)}

        for key, value in cleaned_data.items():
            if "column_6" in key:
                if isinstance(value, str) and not value.startswith("$"):
                    cleaned_data[key] = f"${value}"

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(cleaned_data, file, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def load_and_update(self, grid_type='middle', entries=None, fetch_prices=True):
        data = self.load_data(grid_type)

        for row in range(30):
            for col in range(9):
                entry_key = f"row_{row}_column_{col}"
                value = data.get(entry_key, "")

                if value:
                    if col == 6:
                        if value.startswith("DEPOSITED $"):
                            value = value[len("DEPOSITED $"):].strip()

                        entries[row][col].delete(0, tk.END)
                        entries[row][col].insert(0, f"DEPOSITED ${value}")

                    elif col == 7:
                        try:
                            value = float(value.replace(",", "")) if isinstance(value, str) else float(value)
                            formatted_value = f"{value:,.0f}"
                        except ValueError:
                            formatted_value = "0"
                        entries[row][col].delete(0, tk.END)
                        entries[row][col].insert(0, formatted_value)

                    elif col == 8:
                        if not isinstance(value, str):
                            value = ""
                        value = value.upper()
                        entries[row][col].delete(0, tk.END)
                        entries[row][col].insert(0, value)

                    else:
                        entries[row][col].delete(0, tk.END)
                        entries[row][col].insert(0, value)

        self.save_data(data, grid_type)
