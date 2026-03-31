import socket
import threading
import time
import webview

from Log_checker import run_server

HOST = "127.0.0.1"
PORT = 5001


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
    server_thread = threading.Thread(
        target=run_server,
        kwargs={"host": HOST, "port": PORT},
        daemon=True
    )
    server_thread.start()

    _wait_for_server(HOST, PORT, timeout=15)

    webview.create_window(
        "Event Inspector",
        f"http://{HOST}:{PORT}",
        width=1400,
        height=900
    )
    webview.start()


if __name__ == "__main__":
    main()
