import time


class ProgressLogger:
    def __init__(self):
        self.total_fetches = 0
        self.total_attempts = 0
        self.total_fetches_last_minute = 0
        self.total_attempts_last_minute = 0
        self.minute_counter = 0
        self.start_time = time.time()

    def log_progress(self):
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        if elapsed_time >= 60:
            self.minute_counter += 1
            self.total_fetches += self.total_fetches_last_minute
            self.total_attempts += self.total_attempts_last_minute
            print(f"Minute {self.minute_counter}: {self.total_fetches_last_minute} prices fetched in {self.total_attempts_last_minute} attempts")
            print(f"Total fetches: {self.total_fetches} in total attempts {self.total_attempts}")
            self.total_fetches_last_minute = 0
            self.total_attempts_last_minute = 0
            self.start_time = time.time()
