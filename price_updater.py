class PriceUpdater:
    def __init__(self, entry_data, grid_manager, root, get_deposited_value_func=None):
        self.entry_data = entry_data
        self.grid_manager = grid_manager
        self.root = root
        self.get_deposited_value = get_deposited_value_func  # Receive the function reference

    def update_price(self, row, formatted_price, raw_price):
        self.grid_manager.create_value_label(row, 2, f"${formatted_price}")

        invested, holdings = self.get_invested_and_holdings(row)

        if invested != 0 and holdings != 0:
            break_even, balance, profit = self.calculate_values(invested, holdings, raw_price)
            self.update_labels(row, break_even, balance, profit)
            self.update_total_profit()
        else:
            self.update_labels(row, "Invalid", "Invalid", "Invalid")
            self.update_total_profit()

        # Force UI update
        self.root.update_idletasks()

    def get_invested_and_holdings(self, row):
        invested = self.entry_data.get(f"row_{row}_invested", 0)
        holdings = self.entry_data.get(f"row_{row}_holdings", 0)
        return self._parse_input_value(invested), self._parse_input_value(holdings)

    def calculate_values(self, invested, holdings, raw_price):
        break_even = invested / holdings if holdings != 0 else 0
        balance = raw_price * holdings
        profit = balance - invested
        return break_even, balance, profit

    def update_labels(self, row, break_even, balance, profit):
        self.grid_manager.create_value_label(
            row, 3, f"${break_even:,.2f}" if break_even != "Invalid" else "Invalid"
        )
        self.grid_manager.create_value_label(
            row, 4, f"${balance:,.2f}" if balance != "Invalid" else "Invalid"
        )
        self.grid_manager.create_value_label(
            row, 5, f"${profit:,.2f}" if profit != "Invalid" else "Invalid"
        )

    def update_total_profit(self):
        total_profit = 0
        for row in range(30):
            invested, holdings = self.get_invested_and_holdings(row)
            raw_price = self._parse_input_value(self.entry_data.get(f"row_{row}_price", 0))
            profit = (raw_price * holdings) - invested
            if invested > 0 and holdings > 0:
                self.entry_data[f"row_{row}_profit"] = f"${profit:,.2f}"
                total_profit += profit

        # Check if deposited_value is callable and fetch its value
        if self.get_deposited_value:
            deposited_value = self.get_deposited_value(self.grid_manager.deposited_entry) if self.grid_manager.deposited_entry else 0
        else:
            deposited_value = 0  # Set to 0 if the function is not passed or if grid_manager.deposited_entry is None

        # Update net value if grid_manager is available
        if self.grid_manager:
            self.grid_manager.update_net_value(deposited_value=deposited_value, total_profit=total_profit)

    def _parse_input_value(self, value):
        try:
            value = str(value).strip().replace('$', '').replace(',', '')
            return float(value) if value else 0.0
        except ValueError:
            return 0.0
