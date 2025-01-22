import tkinter as tk

class Config:
    def __init__(self,
                 root: tk.Tk,
                 screen_width: int,
                 screen_height: int,
                 strip_height: int,
                 column_width_top: int,
                 column_width_middle: int,
                 column_width_bottom: int,
                 wallet_colors: dict,
                 entry_data_middle: dict,
                 entry_data_bottom: dict,
                 data_handler=None,
                 focus_handler=None,
                 button_handler=None):
        # Initialize configuration data
        self.root = root
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.strip_height = strip_height
        self.column_width_top = column_width_top
        self.column_width_middle = column_width_middle
        self.column_width_bottom = column_width_bottom
        self.wallet_colors = wallet_colors
        self.entry_data_middle = entry_data_middle
        self.entry_data_bottom = entry_data_bottom
        self.data_handler = data_handler
        self.focus_handler = focus_handler
        self.button_handler = button_handler

        # Validate the configuration
        self.validate()

    def validate(self):
        if not isinstance(self.screen_width, int) or self.screen_width <= 0:
            raise ValueError("Invalid screen_width")
        if not isinstance(self.screen_height, int) or self.screen_height <= 0:
            raise ValueError("Invalid screen_height")
        # More validation checks can be added here