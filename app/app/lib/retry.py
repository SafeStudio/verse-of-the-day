import time


class Retry:
    def __init__(self):
        self.retry_count = 0
        self.sleep = 5
        self.is_retry = False

    def __call__(self, func):
        def retried_func(*args, **kwargs):
            while True:
                resp = func(*args, **kwargs)
                if resp is False:
                    self.is_retry = True
                    self.retry_count += 1
                    sleep_time = self.sleep * self.retry_count
                    time.sleep(sleep_time)
                    print("Retry after", sleep_time, "second(s)")
                else:
                    break

            return resp

        return retried_func

    def check_retry(self):
        if self.is_retry:
            self.is_retry = False
            self.retry_count = 0
            self.sleep = 5
