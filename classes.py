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
        color = wallet_colors.get(wallet_name, "lightgrey")
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


class UIGridHelper:
    def __init__(self, root, config, on_focus_in, on_focus_out):
        self.root = root
        self.config = config
        self.on_focus_in = on_focus_in
        self.on_focus_out = on_focus_out
        self.existing_labels = {}

    def create_default_label(self, row, col, row_color):
        """Create a default label for the grid at a given row and column."""
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
        """Create or update a value label for a given row and column, with flashing background colors for price updates."""
        entry_height = (self.config.screen_height - 2 * self.config.strip_height) / 30
        col_width_middle = self.config.column_width_middle
        purple_shades = UIHelper.generate_purple_shades(30)

        if bg_color is None:
            bg_color = purple_shades[row]  # Default background color

        label_key = (row, col)

        if label_key in self.existing_labels:
            label = self.existing_labels[label_key]
            label.config(text=text, bg=bg_color)
        else:
            label = tk.Label(self.root, bg=bg_color, text=text, font=("Arial", 15), fg="black", anchor="center")
            x_position = col * col_width_middle
            y_position = self.config.strip_height + row * entry_height
            label.place(x=int(x_position), y=int(y_position), width=int(col_width_middle), height=int(entry_height))
            self.existing_labels[label_key] = label

        UIHelper.adjust_font_color(label, bg_color)

        # Only animate if the price is updated and it's a valid price
        if text != "$0" and text != "Loading...":
            self.animate_price_update(row, col, text, label)

    def animate_price_update(self, row, col, text, price_label):
        """Animate flashing background color effect for price updates (red, yellow, green)."""
        # Apply flashing only for PRICE (column 2), BREAK EVEN (column 3), BALANCE (column 4), and PROFIT (column 5)
        if col not in [2, 3, 4, 5]:
            return

        flash_color = "yellow"  # Default color for price updates
        if not text or text == "Loading..." or text == "Invalid" or text == "Error":
            flash_color = "yellow"
        else:
            previous_price = self.config.entry_data_middle.get(f"row_{row}_price", None)

            if previous_price is not None:
                try:
                    current_price = float(text[1:])  # Remove "$" and convert to float
                    previous_price_value = previous_price if isinstance(previous_price, float) else float(previous_price[1:])

                    if current_price > previous_price_value:
                        flash_color = "green"  # If the price increased, show green
                    elif current_price < previous_price_value:
                        flash_color = "red"  # If the price decreased, show red
                    else:
                        flash_color = "yellow"  # No change, show yellow
                except ValueError:
                    flash_color = "yellow"  # Default to yellow if there's a value error
            else:
                flash_color = "yellow"  # Default to yellow if no previous price

        original_color = price_label.cget("bg")
        price_label.config(bg=flash_color)
        self.root.after(200, lambda: price_label.config(bg=original_color))  # Revert after 200ms

        # Update the price in the entry data for future comparisons
        self.config.entry_data_middle[f"row_{row}_price"] = text

    def create_entry(self, row, col, column_id, entry_data, entries, enforce_dollar_sign, on_enter):
        entry = tk.Entry(self.root, font=("Arial", 14, "bold"), fg="black", bg="lightgrey", justify="center", bd=0,
                         relief="flat")
        entry_height = (self.config.screen_height - 2 * self.config.strip_height) / 30
        col_width_middle = self.config.column_width_middle
        purple_shades = UIHelper.generate_purple_shades(30)

        row_color = purple_shades[row]  # Here, row_color is determined from purple_shades
        entry.config(bg=row_color)

        x_position = col * col_width_middle
        y_position = self.config.strip_height + row * entry_height

        # Adjust the column widths
        if col == 8:
            col_width_middle = self.root.winfo_width() - (8 * self.config.column_width_middle)
        elif col == 7:
            col_width_middle = self.root.winfo_width() - ((7) * self.config.column_width_middle) - (
                    self.root.winfo_width() - (8 * self.config.column_width_middle))
        elif col == 6:
            col_width_middle = self.root.winfo_width() - ((6) * self.config.column_width_middle) - (
                    self.root.winfo_width() - (7 * self.config.column_width_middle))

        entry.place(x=int(x_position), y=int(y_position), width=int(col_width_middle), height=int(entry_height))

        entry.column_idx = column_id

        # Load the saved value if available
        if f"row_{row}_column_{column_id}" not in entry_data:
            default_value = "$0" if column_id == 6 else "0"
            entry.insert(0, default_value)
        else:
            saved_value = entry_data[f"row_{row}_column_{column_id}"]
            if column_id == 6 and not saved_value.startswith("$"):
                saved_value = "$" + saved_value
            entry.insert(0, saved_value)

        entries.append(entry)

        # Bind event handlers
        entry.bind("<Return>", partial(on_enter, row=row, column=column_id))
        entry.bind("<KeyRelease>", enforce_dollar_sign)
        entry.bind("<FocusIn>", partial(self.on_focus_in, entry=entry))

        # Adjust font color
        UIHelper.adjust_font_color(entry, row_color)

    def enforce_dollar_sign(self, event):
        entry = event.widget
        text = entry.get()
        if getattr(entry, 'column_idx', None) == 8:
            return
        if not text.startswith("$"):
            entry.insert(0, "$")
        text = entry.get()
        clean_text = "$" + ''.join(c for c in text[1:] if c.isdigit())
        if text != clean_text:
            entry.delete(0, "end")
            entry.insert(0, clean_text)
        entry.icursor(len(entry.get()))

    def create_wallet_entry_middle(self, row, col, entry_data_middle, wallet_colors,
                                   entries, on_enter_middle, on_focus_out):
        entry = tk.Entry(self.root, font=("Arial", 12, "bold"), fg="black", bg="lightgrey", justify="center")
        entry.place(x=col * self.config.column_width_middle,
                    y=self.config.strip_height + row * (self.config.screen_height - 2 * self.config.strip_height) / 30,
                    width=self.config.column_width_middle,
                    height=(self.config.screen_height - 2 * self.config.strip_height) / 30)
        entry_key = f"row_{row}_column_9_middle"
        if entry_key in entry_data_middle:
            entry.insert(0, entry_data_middle[entry_key] or "")
        entries.append(entry)
        entry.bind("<Return>", partial(on_enter_middle, row=row, column=9))
        entry.bind("<FocusOut>", lambda event: on_focus_out(row=row, column=9, entry=entry))
        entry.bind("<FocusIn>", partial(self.on_focus_in, entry=entry))
        wallet_name = entry.get().strip().upper()
        color = wallet_colors.get(wallet_name, "lightgrey")
        entry.config(bg=color)
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
                return json.load(file)
        except Exception as e:
            print(f"Error loading data from {file_path}: {e}")
        return {}

    def save_data(self, entry_data, grid_type='middle'):
        file_path = self.middle_grid_file_path if grid_type == 'middle' else self.bottom_grid_file_path
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(entry_data, file, ensure_ascii=False, indent=4)
        except Exception as e:
            # Optional: Log errors in a quieter manner if needed
            pass

    def load_and_update(self, grid_type='middle', entries=None, fetch_prices=True):
        data = self.load_data(grid_type)

        for row in range(30):
            for col in range(10):
                entry_key = f"row_{row}_column_{col}"
                if entry_key in data:
                    value = data[entry_key]
                    if col == 2:
                        coin_name = data.get(f"row_{row}_column_0", "").strip()
                        if coin_name and fetch_prices:
                            price = self.binance_api.get_price(coin_name)
                            if price:
                                data[entry_key] = f"${price}"
                                entries[row][col].delete(0, "end")
                                entries[row][col].insert(0, f"${price}")
                            else:
                                data[entry_key] = "Invalid"
                                entries[row][col].delete(0, "end")
                                entries[row][col].insert(0, "Invalid")
                        else:
                            data[entry_key] = "loading..."
                            entries[row][col].delete(0, "end")
                            entries[row][col].insert(0, "loading...")

        self.save_data(data, grid_type)