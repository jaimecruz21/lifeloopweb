import os
import sys
import time

import requests


def main():
    print("Waiting for the webserver to become available...")
    retries = int(os.environ.get("TEST_RETRIES", 3))
    sleep = int(os.environ.get("TEST_SLEEP", 5))
    host = os.environ.get("TEST_HOST", "127.0.0.1")
    port = os.environ.get("TEST_PORT", 5000)
    success = False
    for _current_try in range(retries):
        try:
            requests.get("http://{}:{}/".format(host, port))
            success = True
        except Exception:
            print("Service isn't up yet...")
            time.sleep(sleep)
    if not success:
        sys.exit(1)
    print("Service is up")


if __name__ == "__main__":
    main()
