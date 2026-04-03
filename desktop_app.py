import socket
import threading
import time
import webview
import os
import sys
import logging
import traceback
import webbrowser

from Log_checker import run_server

HOST = "127.0.0.1"
PORT = 5001

def _setup_logging():
    base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    log_dir = os.path.join(base, "EventInspector")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "app.log")
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.info("Starting EventInspector")
    return log_path


def _wait_for_server(host, port, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main():
    log_path = _setup_logging()

    def _server_entry():
        try:
            run_server(host=HOST, port=PORT)
        except Exception:
            logging.exception("Server crashed:\n%s", traceback.format_exc())

    server_thread = threading.Thread(target=_server_entry, daemon=True)
    server_thread.start()

    _wait_for_server(HOST, PORT, timeout=15)

    webview.create_window(
        "Event Inspector",
        f"http://{HOST}:{PORT}",
        width=1400,
        height=900
    )
    try:
        webview.start()
    except Exception:
        logging.exception("WebView crashed:\n%s", traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
