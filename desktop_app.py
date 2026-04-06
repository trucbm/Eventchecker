import socket
import threading
import time
import os
import sys
import logging
import traceback

if sys.platform.startswith("win"):
    os.environ["PYWEBVIEW_GUI"] = "qt"

import webview

# Remote update loader (optional)
try:
    import remote_update
except Exception:
    remote_update = None

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

    # Provide restart command for in-app restart
    restart_cmd = sys.executable
    restart_args = ''
    if getattr(sys, 'frozen', False):
        restart_cmd = sys.executable
        restart_args = ''
    else:
        restart_cmd = sys.executable
        restart_args = os.path.abspath(__file__)
    os.environ['EVENTINSPECTOR_RESTART_CMD'] = restart_cmd
    os.environ['EVENTINSPECTOR_RESTART_ARGS'] = restart_args

    # Load any already-downloaded update, but do not check remote on launch.
    if remote_update:
        try:
            update_dir = remote_update.load_prepared_update_dir()
            if update_dir:
                os.environ["EVENTINSPECTOR_UPDATE_DIR"] = update_dir
                if update_dir not in sys.path:
                    sys.path.insert(0, update_dir)
                logging.info("Loaded prepared update from: %s", update_dir)
        except Exception:
            logging.exception("Prepared update load failed:\n%s", traceback.format_exc())

    from Log_checker import run_server

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
        height=900,
        maximized=True
    )
    try:
        if sys.platform.startswith("win"):
            # Force Qt on Windows so we never silently fall back to browser mode.
            webview.start(gui="qt")
        else:
            webview.start()
    except Exception:
        logging.exception("WebView crashed:\n%s", traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
