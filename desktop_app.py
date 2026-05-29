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
DEFAULT_BUNDLED_UPDATE_BUILD = 50


def _user_data_dir():
    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "EventInspector")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~/Library/Application Support"), "EventInspector")
    return os.path.join(os.path.expanduser("~"), ".eventinspector")


def _extract_build_number_from_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read(200000)
    except Exception:
        return None
    import re
    matches = re.findall(r"v2\.3\.0\((\d+)\)", data)
    if not matches:
        return None
    try:
        return max(int(item) for item in matches)
    except Exception:
        return None


def _bundled_log_checker_path():
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "Log_checker.py"))
    candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Log_checker.py"))
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return ""


def _get_bundled_update_build():
    bundled_path = _bundled_log_checker_path()
    build = _extract_build_number_from_file(bundled_path) if bundled_path else None
    if build is not None:
        return build
    return DEFAULT_BUNDLED_UPDATE_BUILD

def _setup_logging():
    log_dir = _user_data_dir()
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


def _is_port_available(host, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, port))
        return True
    except OSError:
        return False


def _pick_server_port(host, preferred_port):
    if _is_port_available(host, preferred_port):
        return preferred_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        _, port = sock.getsockname()
    logging.warning(
        "Preferred port %s is busy; using fallback port %s instead",
        preferred_port,
        port,
    )
    return port


def main():
    log_path = _setup_logging()
    port = _pick_server_port(HOST, PORT)
    bundled_build = _get_bundled_update_build()
    os.environ["EVENTINSPECTOR_BUNDLED_BUILD"] = str(bundled_build)

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
            prepared_update = remote_update.get_prepared_update_info()
            update_dir = prepared_update.get("update_dir") if prepared_update else None
            if update_dir:
                updated_build = prepared_update.get("build")
                requested_from_bundle_build = prepared_update.get("requested_from_bundle_build")
                if (
                    updated_build is not None
                    and updated_build < bundled_build
                    and requested_from_bundle_build != bundled_build
                ):
                    logging.info(
                        "Ignoring stale prepared update %s because bundled build is %s and requested build is %s",
                        updated_build,
                        bundled_build,
                        requested_from_bundle_build,
                    )
                    update_dir = None
            if update_dir:
                os.environ["EVENTINSPECTOR_UPDATE_DIR"] = update_dir
                if update_dir not in sys.path:
                    sys.path.insert(0, update_dir)
                logging.info("Loaded prepared update from: %s", update_dir)
        except Exception:
            logging.exception("Prepared update load failed:\n%s", traceback.format_exc())

    def _load_run_server():
        update_dir = os.environ.get("EVENTINSPECTOR_UPDATE_DIR")
        updated_log_checker = os.path.join(update_dir, "Log_checker.py") if update_dir else ""
        if updated_log_checker and os.path.exists(updated_log_checker):
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("eventinspector_updated_log_checker", updated_log_checker)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                logging.info("Loaded Log_checker from update file: %s", updated_log_checker)
                return module.run_server
            except Exception:
                logging.exception("Updated Log_checker load failed, falling back to bundled module:\n%s", traceback.format_exc())
        from Log_checker import run_server as bundled_run_server
        logging.info("Loaded bundled Log_checker module")
        return bundled_run_server

    run_server = _load_run_server()

    def _server_entry():
        try:
            run_server(host=HOST, port=port)
        except Exception:
            logging.exception("Server crashed:\n%s", traceback.format_exc())

    server_thread = threading.Thread(target=_server_entry, daemon=True)
    server_thread.start()

    if not _wait_for_server(HOST, port, timeout=15):
        message = f"Local server failed to start on {HOST}:{port}. See log: {log_path}"
        logging.error(message)
        raise RuntimeError(message)

    webview.create_window(
        "Event Inspector",
        f"http://{HOST}:{port}",
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
