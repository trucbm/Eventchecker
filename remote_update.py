import json
import os
import re
import hashlib
import time
import sys

import requests

APP_NAME = "EventInspector"
CHANNEL_ID = "v230"
CONFIG_FILENAME = "remote_update_config_v230.json"
STATE_FILENAME = "update_state_v230.json"
UPDATES_DIRNAME = "updates_v230"
DEFAULT_MANIFEST_URLS = [
    "https://cdn.jsdelivr.net/gh/trucbm/Eventchecker@main/Updates_2_3/remote_manifest.json",
    "https://raw.githubusercontent.com/trucbm/Eventchecker/main/Updates_2_3/remote_manifest.json",
    "https://github.com/trucbm/Eventchecker/raw/main/Updates_2_3/remote_manifest.json",
]
DEFAULT_MANIFEST_URL = DEFAULT_MANIFEST_URLS[0]
DEFAULT_FILE_URL_BASES = [
    "https://cdn.jsdelivr.net/gh/trucbm/Eventchecker@main",
    "https://raw.githubusercontent.com/trucbm/Eventchecker/main",
    "https://github.com/trucbm/Eventchecker/raw/main",
]


def _user_data_dir():
    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, APP_NAME)
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~/Library/Application Support"), APP_NAME)
    return os.path.join(os.path.expanduser("~"), f".{APP_NAME.lower()}")


def _config_paths():
    user_dir = _user_data_dir()
    return [
        os.getenv("EVENTINSPECTOR_UPDATE_CONFIG_V210"),
        os.path.join(user_dir, CONFIG_FILENAME),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME),
    ]


def _load_config():
    for p in _config_paths():
        if p and os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                cfg.setdefault("enabled", True)
                cfg.setdefault("manifest_url", DEFAULT_MANIFEST_URL)
                cfg.setdefault("manifest_urls", DEFAULT_MANIFEST_URLS)
                cfg.setdefault("timeout_sec", 10)
                # Always prefer checking remote on launch. Existing user configs
                # may still contain stale throttling values from older builds.
                cfg["min_interval_sec"] = 0
                return cfg
    return {
        "enabled": True,
        "manifest_url": DEFAULT_MANIFEST_URL,
        "manifest_urls": DEFAULT_MANIFEST_URLS,
        "timeout_sec": 10,
        "min_interval_sec": 0,
    }


def _ensure_user_config_template():
    user_dir = _user_data_dir()
    os.makedirs(user_dir, exist_ok=True)
    cfg_path = os.path.join(user_dir, CONFIG_FILENAME)
    desired = {
        "enabled": True,
        "manifest_url": DEFAULT_MANIFEST_URL,
        "manifest_urls": DEFAULT_MANIFEST_URLS,
        "timeout_sec": 10,
        "min_interval_sec": 0,
    }
    current = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                current = json.load(f)
        except Exception:
            current = {}
    current.update(desired)
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    return cfg_path


def _state_path():
    return os.path.join(_user_data_dir(), STATE_FILENAME)


def _load_state():
    path = _state_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_state(state):
    os.makedirs(_user_data_dir(), exist_ok=True)
    with open(_state_path(), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url, timeout):
    # Handle Google Drive confirm page for large files
    session = requests.Session()
    r = session.get(url, allow_redirects=True, timeout=timeout)
    if r.headers.get("content-type", "").startswith("text/html"):
        m = re.search(r"confirm=([0-9A-Za-z_]+)", r.text)
        if m:
            confirm = m.group(1)
            sep = "&" if "?" in url else "?"
            url2 = f"{url}{sep}confirm={confirm}"
            r = session.get(url2, allow_redirects=True, timeout=timeout)
    r.raise_for_status()
    return r.content


def _unique_urls(urls):
    seen = set()
    out = []
    for url in urls or []:
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def _candidate_manifest_urls(cfg):
    urls = []
    urls.extend(cfg.get("manifest_urls") or [])
    single = (cfg.get("manifest_url") or "").strip()
    if single:
        urls.append(single)
    urls.extend(DEFAULT_MANIFEST_URLS)
    return _unique_urls(urls)


def _default_repo_file_urls(rel_path):
    rel = (rel_path or "").lstrip("/")
    return [f"{base}/{rel}" for base in DEFAULT_FILE_URL_BASES]


def _download_first(urls, timeout):
    last_error = None
    for url in _unique_urls(urls):
        try:
            return _download(url, timeout), url
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise ValueError("no_download_urls")


def load_prepared_update_dir():
    _ensure_user_config_template()
    cfg = _load_config()

    if not cfg.get("enabled"):
        return None

    state = _load_state()
    update_dir = state.get("update_dir")
    expected_files = state.get("files") or []
    if not update_dir or not os.path.isdir(update_dir):
        return None
    for rel_path in expected_files:
        if rel_path and not os.path.exists(os.path.join(update_dir, rel_path)):
            return None
    return update_dir


def check_for_updates():
    _ensure_user_config_template()
    cfg = _load_config()

    if not cfg.get("enabled"):
        return None

    manifest_urls = _candidate_manifest_urls(cfg)
    if not manifest_urls:
        return None

    timeout = float(cfg.get("timeout_sec", 10))
    state = _load_state()

    try:
        manifest_bytes, manifest_url = _download_first(manifest_urls, timeout)
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except Exception:
        return {"ok": False, "status": "error", "error": "manifest_download_failed", "update_dir": load_prepared_update_dir()}

    update_dir = os.path.join(_user_data_dir(), UPDATES_DIRNAME)
    tmp_update_dir = os.path.join(_user_data_dir(), f"{UPDATES_DIRNAME}_tmp")
    os.makedirs(tmp_update_dir, exist_ok=True)

    state_version = state.get("version")
    manifest_version = manifest.get("version")
    existing_update_dir = state.get("update_dir") or update_dir
    manifest_files = manifest.get("files", [])
    if (
        state_version == manifest_version
        and existing_update_dir
        and os.path.isdir(existing_update_dir)
        and all(os.path.exists(os.path.join(existing_update_dir, item.get("path", ""))) for item in manifest_files if item.get("path"))
    ):
        state.update({
            "last_check": time.time(),
            "version": manifest_version,
            "update_dir": existing_update_dir,
            "manifest_url": manifest_url,
            "files": [item.get("path") for item in manifest_files if item.get("path")],
        })
        _save_state(state)
        return {"ok": True, "status": "up_to_date", "version": manifest_version, "update_dir": existing_update_dir}

    ok = True
    for item in manifest_files:
        rel_path = item.get("path")
        url = item.get("url")
        urls = list(item.get("urls") or [])
        sha256 = item.get("sha256")
        if not rel_path or not url:
            if not rel_path:
                ok = False
                break

        target = os.path.join(tmp_update_dir, rel_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            candidate_urls = []
            if url:
                candidate_urls.append(url)
            candidate_urls.extend(urls)
            candidate_urls.extend(_default_repo_file_urls(rel_path))
            data, _used_url = _download_first(candidate_urls, timeout)
            tmp = f"{target}.tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            if sha256:
                if _sha256_file(tmp).lower() != sha256.lower():
                    os.remove(tmp)
                    ok = False
                    break
            os.replace(tmp, target)
        except Exception:
            ok = False
            break

    if ok:
        # Replace old updates atomically
        try:
            if os.path.exists(update_dir):
                for root, dirs, files in os.walk(update_dir, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
        except Exception:
            pass
        # Move tmp -> update_dir
        try:
            if not os.path.exists(update_dir):
                os.makedirs(update_dir, exist_ok=True)
            for root, dirs, files in os.walk(tmp_update_dir):
                rel = os.path.relpath(root, tmp_update_dir)
                dest_root = update_dir if rel == '.' else os.path.join(update_dir, rel)
                os.makedirs(dest_root, exist_ok=True)
                for name in files:
                    src = os.path.join(root, name)
                    dst = os.path.join(dest_root, name)
                    os.replace(src, dst)
        except Exception:
            return {"ok": False, "status": "error", "error": "replace_failed", "update_dir": load_prepared_update_dir()}

        state.update({
            "last_check": time.time(),
            "version": manifest.get("version"),
            "update_dir": update_dir,
            "manifest_url": manifest_url,
            "files": [item.get("path") for item in manifest_files if item.get("path")],
        })
        _save_state(state)
        return {"ok": True, "status": "updated", "version": manifest.get("version"), "update_dir": update_dir}

    return {"ok": False, "status": "error", "error": "download_failed", "update_dir": load_prepared_update_dir()}


def check_and_prepare_updates():
    result = check_for_updates()
    return result.get("update_dir")

    return state.get("update_dir")
