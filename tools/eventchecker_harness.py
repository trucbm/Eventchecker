#!/usr/bin/env python3
"""Lightweight harness for catching repeat regressions in EventInspector.

Run this before pushing changes:

    python3 tools/eventchecker_harness.py

The harness intentionally focuses on the brittle parts of the app:
- update manifest shape
- exact-match parsing contracts
- installation-id state transitions
- package-code mapping
- release payload/source sync for every build target

It does not start the UI or connect to devices.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import hashlib
import sys
import tempfile
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Log_checker as lc  # noqa: E402
# desktop_app only needs webview after main() starts; keep the harness usable
# in a plain Python environment that has not installed the UI dependency.
sys.modules.setdefault("webview", types.ModuleType("webview"))
import desktop_app as desktop  # noqa: E402


@dataclass
class HarnessResult:
    name: str
    passed: bool
    message: str = ""


def _reset_runtime_state() -> None:
    lc.active_platform = "android"
    lc.connected_devices_info = []
    lc.installation_id_state.clear()
    lc.sdk_check_runtime_state.clear()
    lc.sdk_check_expected_map.clear()
    lc.sdk_check_expected_order.clear()
    lc.sdk_check_search_list.clear()
    lc.sdk_check_current_network.clear()
    lc.is_paused = False


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected={expected!r} actual={actual!r}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_path_candidates(manifest_path: Path, item: dict) -> List[Path]:
    rel_path = str(item.get("path", "")).strip()
    if not rel_path:
        return []
    payload_dir = manifest_path.parent
    candidates = [payload_dir / rel_path, ROOT / rel_path]
    return candidates


def _valid_payload_urls(manifest_path: Path, rel_path: str, payload_path: Path) -> set[str]:
    repo_rel = payload_path.relative_to(ROOT).as_posix()
    return {
        f"https://github.com/trucbm/Eventchecker/raw/main/{repo_rel}",
        f"https://raw.githubusercontent.com/trucbm/Eventchecker/main/{repo_rel}",
        f"https://cdn.jsdelivr.net/gh/trucbm/Eventchecker@main/{repo_rel}",
    }


def _manifest_paths() -> List[Path]:
    candidates = [
        ROOT / "Updates_2_3" / "remote_manifest.json",
        ROOT / "Updates_2_4" / "remote_manifest.json",
    ]
    return [path for path in candidates if path.exists()]


def test_manifest_contract() -> None:
    manifests = _manifest_paths()
    _assert(manifests, "No release manifest files found")
    for manifest_path in manifests:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        _assert("version" in data and str(data["version"]).strip(), f"{manifest_path.name} missing version")
        files = data.get("files") or []
        _assert(files, f"{manifest_path.name} missing files list")
        log_checker_files = [item for item in files if str(item.get("path", "")).strip() == "Log_checker.py"]
        _assert(log_checker_files, f"{manifest_path.name} missing Log_checker.py payload")
        for item in files:
            _assert(str(item.get("path", "")).strip(), f"{manifest_path.name} contains file entry without path")
            _assert(str(item.get("url", "")).strip(), f"{manifest_path.name} contains file entry without url")
            _assert(str(item.get("sha256", "")).strip(), f"{manifest_path.name} contains file entry without sha256")


def test_manifest_payload_integrity() -> None:
    manifests = _manifest_paths()
    _assert(manifests, "No release manifest files found")
    for manifest_path in manifests:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in data.get("files") or []:
            rel_path = str(item.get("path", "")).strip()
            if not rel_path:
                continue
            candidates = _payload_path_candidates(manifest_path, item)
            payload_path = next((candidate for candidate in candidates if candidate.exists()), None)
            _assert(payload_path is not None, f"{manifest_path.name} payload missing for {rel_path}")

            expected_sha = str(item.get("sha256", "")).strip().lower()
            actual_sha = _sha256_file(payload_path).lower()
            _assert_equal(actual_sha, expected_sha, f"{manifest_path.name} sha mismatch for {rel_path}")

            valid_urls = _valid_payload_urls(manifest_path, rel_path, payload_path)
            url = str(item.get("url", "")).strip()
            _assert(
                url in valid_urls,
                f"{manifest_path.name} url points outside {manifest_path.parent.name} for {rel_path}: {url}",
            )
            for extra_url in item.get("urls") or []:
                extra_url = str(extra_url).strip()
                _assert(
                    extra_url in valid_urls,
                    f"{manifest_path.name} urls entry points outside {manifest_path.parent.name} for {rel_path}: {extra_url}",
                )


def test_package_code_mapping() -> None:
    expected = {
        "com.indiez.nonogram": "NG",
        "com.indiez.train.miner": "TM",
        "com.indiez.idletycoon.horse.racing": "HR",
        "com.indiez.solitaire.word.card.puzzle": "SW",
        "com.nostel.dot.line.puzzle": "KN",
        "com.nostel.parking.car": "CP",
        "com.afk.idle.cat.food.restaurent": "CR",
        "tap.monster.block.away": "TP",
    }
    for package_id, game_code in expected.items():
        _assert_equal(lc._game_code_for_package(package_id), game_code, f"wrong game code for {package_id}")
    _assert_equal(lc._game_code_for_package("com.example.unknown"), "Unknown", "unknown package should stay Unknown")


def test_installation_id_state_machine() -> None:
    _reset_runtime_state()
    device_id = "device-1"

    lc._update_installation_id_runtime(device_id, package_id="com.indiez.nonogram", installation_id="id-old", force_emit=True)
    _assert_equal(lc.installation_id_state[device_id]["installation_id"], "id-old", "initial installation id not stored")

    lc._update_installation_id_runtime(device_id, package_id="com.indiez.nonogram", installation_id="id-old-2")
    _assert_equal(lc.installation_id_state[device_id]["installation_id"], "id-old-2", "same package should accept the newest installation id")

    lc._update_installation_id_runtime(device_id, package_id="com.nostel.parking.car", installation_id="", force_emit=True)
    _assert_equal(lc.installation_id_state[device_id]["installation_id"], "", "package switch should clear stale installation id")
    _assert_equal(lc.installation_id_state[device_id]["game_code"], "CP", "package switch should refresh game code")

    lc._update_installation_id_runtime(device_id, package_id="com.nostel.parking.car", installation_id="id-new", force_emit=True)
    _assert_equal(lc.installation_id_state[device_id]["installation_id"], "id-new", "new package should accept a fresh installation id")


def test_installation_id_log_parsing() -> None:
    _reset_runtime_state()
    device_id = "device-2"

    original_get_package = lc._get_android_foreground_package
    try:
        lc._get_android_foreground_package = lambda _device_id: "com.indiez.nonogram"
        lc.process_installation_id_log(
            '16:31:37.056 SS S21 Unity 07-02 16:31:37.056  3425  3954 I Unity   : [Firebase] FirebaseInstallationIdPostInitHandler->_DebugInstallationId: {"idTask":{"idTask.IsFaulted":false,"idTask.Result":"d_vP_hhkSc2Z2c1b215kBR"}}',
            device_id,
        )
        _assert_equal(lc.installation_id_state[device_id]["installation_id"], "d_vP_hhkSc2Z2c1b215kBR", "json installation id log not parsed")

        lc._get_android_foreground_package = lambda _device_id: "com.nostel.parking.car"
        lc.process_installation_id_log("18:11:37.095\tUnity\tInstallations id fg88SZWfT6e_L4CxDX04Gp", device_id)
        _assert_equal(lc.installation_id_state[device_id]["installation_id"], "fg88SZWfT6e_L4CxDX04Gp", "plain installation id log not parsed")
        _assert_equal(lc.installation_id_state[device_id]["game_code"], "CP", "installation id log should follow active package")
    finally:
        lc._get_android_foreground_package = original_get_package


def test_sdk_exact_contracts() -> None:
    _reset_runtime_state()
    android_line = "Initializing Firebase Crashlytics 20.0.5"
    ios_line = "[Firebase/Crashlytics] Version 12.12.0"
    _assert("Initializing Firebase Crashlytics 20.0.5" in android_line, "android crashlytics contract changed")
    _assert("[Firebase/Crashlytics] Version 12.12.0" in ios_line, "ios crashlytics contract changed")
    _assert_equal(lc._extract_sdk_comparable_version(android_line), "20.0.5", "android crashlytics version should stay exact")
    _assert_equal(lc._extract_sdk_comparable_version(ios_line), "12.12.0", "ios crashlytics version should stay exact")


def test_cloudx_sdk_adapter_metadata() -> None:
    original_platform = lc.active_platform
    original_devices = lc.connected_devices_info
    original_sdk_active = lc.sdk_check_active
    original_search_list = list(lc.sdk_check_search_list)
    try:
        lc.active_platform = "android"
        lc.connected_devices_info = []
        lc.sdk_check_active = True
        lc.sdk_check_expected_map = {}
        lc.sdk_check_expected_order = []
        lc.sdk_check_runtime_state = {}
        lc.sdk_check_current_network = {}

        labels = [
            ("Digital Turbine (fyber) - Cloudx", "Fyber", "1.0.0"),
            ("InMobi - Cloudx", "InMobi", "2.0.0"),
            ("Liftoff Monetization (vungle) - Cloudx", "Vungle", "3.0.0"),
            ("Meta Audience Network - Cloudx", "Meta", "4.0.0"),
            ("Mintegral - Cloudx", "Mintegral", "5.0.0"),
            ("Mobilefuse - Cloudx", "Mobilefuse", "6.0.0"),
            ("Moloco - Cloudx", "Moloco", "7.0.0"),
            ("Pangle - Cloudx", "Pangle", "8.0.0"),
            ("UnityAds - Cloudx", "Unity", "9.0.0"),
            ("Verve / Pubnative - Cloudx", "Pubnative", "10.0.0"),
            ("TaurusX - Cloudx", "TaurusX", "11.0.0"),
        ]

        cloudx_parsed = lc._parse_sdk_expected_line("CloudX\t4.5.0\t4.5.0")
        _assert(cloudx_parsed is not None, "CloudX network label not accepted")
        _assert_equal(cloudx_parsed.get("source"), "", "CloudX must not be treated as a - Cloudx row")
        lc._register_sdk_expected("CloudX", adapter="4.5.0", sdk="4.5.0")
        cloudx_http_log = (
            '08-14 17:18:30.818 D CloudX [CloudXHttpClient] '
            '[{"sdk":{"sdkVersion":"4.5.0","pluginVersion":"unity-4.5.0"}}]'
        )
        _assert(
            lc._process_sdk_cloudx_http_metadata_line(cloudx_http_log, "cloudx-device"),
            "CloudX telemetry log was not parsed",
        )
        cloudx_state = lc.sdk_check_runtime_state["cloudx-device"]["cloudx"]
        _assert_equal(cloudx_state.get("adapter_version"), "4.5.0", "CloudX plugin version was not normalized")
        _assert_equal(cloudx_state.get("sdk_version"), "4.5.0", "CloudX SDK version was not parsed")
        _assert(
            not lc._process_sdk_cloudx_http_metadata_line(
                '[CloudXHttpClientExtra] [{"sdk":{"sdkVersion":"9.9.9","pluginVersion":"unity-9.9.9"}}]',
                "cloudx-device",
            ),
            "CloudX parser must require the exact CloudXHttpClient marker",
        )
        suffix_state = lc.sdk_check_runtime_state["cloudx-device"].get("mintegralcloudx")
        _assert(not suffix_state, "CloudX telemetry must not update a - Cloudx network")

        for display_name, _, expected_version in labels:
            parsed = lc._parse_sdk_expected_line(display_name)
            _assert(parsed is not None, f"Cloudx network label not accepted: {display_name}")
            _assert_equal(parsed.get("source"), "cloudx", f"Cloudx source missing for {display_name}")
            lc._register_sdk_expected(
                display_name,
                adapter=expected_version,
                source=parsed.get("source", ""),
                match_network=parsed.get("match_network", ""),
            )

        for _, actual_name, actual_version in labels:
            line = (
                "*[AdapterMetadataResolver] Discovered adapter metadata: "
                f"network={actual_name}, adapterVersion={actual_version},*"
            )
            lc._process_sdk_cloudx_adapter_metadata_line(line, "cloudx-device")

        _assert_equal(len(lc.sdk_check_expected_map), len(labels) + 1, "Cloudx network count mismatch")
        for display_name, _, expected_version in labels:
            expected_key = lc._normalize_sdk_network_name(display_name)
            actual = lc.sdk_check_runtime_state["cloudx-device"][expected_key]["adapter_version"]
            _assert_equal(actual, expected_version, f"Cloudx adapter version mismatch for {display_name}")

        cloudx_native_versions = {
            "digitalturbinefybercloudx": "8.4.7",
            "inmobicloudx": "11.4.0",
            "liftoffmonetizationvunglecloudx": "7.7.7",
            "metaaudiencenetworkcloudx": "6.22.0",
            "mintegralcloudx": "17.1.71",
            "mobilefusecloudx": "1.11.0",
            "molococloudx": "4.11.0",
            "panglecloudx": "8.2.0.4",
            "unityadscloudx": "4.19.0",
            "vervepubnativecloudx": "3.9.0",
            "taurusxcloudx": "1.18.3",
        }
        cloudx_actual_names = {
            "digitalturbinefybercloudx": "Fyber",
            "inmobicloudx": "InMobi",
            "liftoffmonetizationvunglecloudx": "Vungle",
            "metaaudiencenetworkcloudx": "Meta",
            "mintegralcloudx": "Mintegral",
            "mobilefusecloudx": "Mobilefuse",
            "molococloudx": "Moloco",
            "panglecloudx": "Pangle",
            "unityadscloudx": "Unity",
            "vervepubnativecloudx": "Pubnative",
            "taurusxcloudx": "TaurusX",
        }
        for expected_key, native_version in cloudx_native_versions.items():
            lc.sdk_check_expected_map[expected_key]["sdk"] = native_version

        mintegral_key = lc._normalize_sdk_network_name("Mintegral - Cloudx")
        lc._process_sdk_cloudx_adapter_metadata_line(
            "08-14 15:26:50.991 com.indiez.nonogram 20641 20791 D CloudX "
            "[AdapterMetadataResolver] Discovered adapter metadata: "
            "network=Mintegral, adapterVersion=17.1.71.0, "
            "networkSdkVersion=17.1.71, minimumSdkVersion=4.2.0, "
            "minimumSdkVersionCode=4002000, adapterApiVersion=1, extras=Bundle[]",
            "cloudx-device",
        )
        mintegral_cloudx_state = lc.sdk_check_runtime_state["cloudx-device"][mintegral_key]
        _assert_equal(mintegral_cloudx_state.get("adapter_version"), "17.1.71.0", "Mintegral Cloudx adapter version mismatch")
        _assert_equal(mintegral_cloudx_state.get("native_version"), "17.1.71", "Mintegral Cloudx native version was not parsed")

        for expected_key, native_version in cloudx_native_versions.items():
            display_name = lc.sdk_check_expected_map[expected_key]["display_name"]
            lc._process_sdk_cloudx_adapter_metadata_line(
                f"[AdapterMetadataResolver] Discovered adapter metadata: network={cloudx_actual_names[expected_key]}, "
                f"adapterVersion=1.0.0, networkSdkVersion={native_version}, minimumSdkVersion=1.0.0",
                "cloudx-native-device",
            )
            _assert_equal(
                lc.sdk_check_runtime_state["cloudx-native-device"][expected_key].get("native_version"),
                native_version,
                f"Cloudx native version mismatch for {display_name}",
            )

        emitted = []
        original_emit = lc.socketio.emit
        try:
            lc.connected_devices_info = [{"id": "cloudx-native-device", "name": "CloudX device"}]
            lc.socketio.emit = lambda event, payload: emitted.append((event, payload))
            lc._emit_sdk_check_results()
        finally:
            lc.socketio.emit = original_emit
        emitted_rows = next(payload for event, payload in emitted if event == "update_sdk_check_table")
        native_rows = [row for row in emitted_rows if row.get("display_text", "").startswith("Native Version")]
        _assert_equal(len(native_rows), len(cloudx_native_versions), "Cloudx native result row count changed")
        _assert(all(row.get("status") == "PASSED" for row in native_rows), "Cloudx native result must pass matching versions")

        lc._process_sdk_cloudx_adapter_metadata_line(
            "[AdapterMetadataResolver] Discovered adapter metadata: "
            "network=Mintegral, adapterVersion=17.1.71.0, networkSdkVersion=17.1.70",
            "cloudx-native-device",
        )
        emitted = []
        original_emit = lc.socketio.emit
        try:
            lc.socketio.emit = lambda event, payload: emitted.append((event, payload))
            lc._emit_sdk_check_results()
        finally:
            lc.socketio.emit = original_emit
        emitted_rows = next(payload for event, payload in emitted if event == "update_sdk_check_table")
        mintegral_native_rows = [
            row for row in emitted_rows
            if row.get("display_text", "").startswith("Native Version")
            and "17.1.70" in row.get("display_text", "")
        ]
        _assert_equal(len(mintegral_native_rows), 1, "Mintegral Cloudx native mismatch row missing")
        _assert_equal(mintegral_native_rows[0].get("status"), "FAILED", "wrong Cloudx native version must fail")

        lc._register_sdk_expected("Mintegral", adapter="5.0.0", sdk="17.1.71")
        lc._process_sdk_check_line("IntegrationHelper ----- Mintegral -----", "cloudx-device")
        lc._process_sdk_check_line("IntegrationHelper Adapter Version - 5.0.0", "cloudx-device")
        mintegral_standard_key = lc._normalize_sdk_network_name("Mintegral")
        _assert_equal(
            lc.sdk_check_runtime_state["cloudx-device"][mintegral_standard_key]["adapter_version"],
            "5.0.0",
            "IntegrationHelper Mintegral state was not kept separate",
        )
        _assert_equal(
            lc.sdk_check_runtime_state["cloudx-device"][mintegral_key].get("native_version"),
            "17.1.71",
            "IntegrationHelper Mintegral changed Cloudx native state",
        )

        lc._register_sdk_expected("Meta Audience Network", adapter="1.0.0")
        lc._process_sdk_check_line("IntegrationHelper ----- Meta Audience Network -----", "cloudx-device")
        lc._process_sdk_check_line("IntegrationHelper Adapter Version - 1.0.0", "cloudx-device")
        _assert_equal(
            lc.sdk_check_runtime_state["cloudx-device"]["metaaudiencenetwork"]["adapter_version"],
            "1.0.0",
            "IntegrationHelper state was not kept separate",
        )
        _assert_equal(
            lc.sdk_check_runtime_state["cloudx-device"]["metaaudiencenetworkcloudx"]["adapter_version"],
            "4.0.0",
            "Cloudx state was overwritten by IntegrationHelper",
        )

        _assert_equal(
            lc._match_sdk_expected_key("Liftoff Monetization"),
            "",
            "IntegrationHelper matcher must not fall through to Cloudx-only entries",
        )
        lc._register_sdk_expected("Liftoff Monetization (vungle)", adapter="12.0.0")
        liftoff_key = lc._normalize_sdk_network_name("Liftoff Monetization (vungle)")
        _assert_equal(
            lc._match_sdk_expected_key("Liftoff Monetization"),
            liftoff_key,
            "Liftoff Monetization alias did not match the list label",
        )
        _assert_equal(
            lc._match_sdk_expected_key("Liftoff Monetize"),
            liftoff_key,
            "Liftoff Monetize alias did not match the list label",
        )
        lc._process_sdk_check_line("IntegrationHelper ----- Liftoff Monetize -----", "cloudx-device")
        lc._process_sdk_check_line("IntegrationHelper Adapter Version - 12.0.0", "cloudx-device")
        _assert_equal(
            lc.sdk_check_runtime_state["cloudx-device"][liftoff_key]["adapter_version"],
            "12.0.0",
            "IntegrationHelper Liftoff alias did not update the standard entry",
        )
        _assert_equal(
            lc.sdk_check_runtime_state["cloudx-device"]["liftoffmonetizationvunglecloudx"].get("adapter_version"),
            "3.0.0",
            "IntegrationHelper Liftoff alias overwrote Cloudx state",
        )
    finally:
        lc.active_platform = original_platform
        lc.connected_devices_info = original_devices
        lc.sdk_check_active = original_sdk_active
        lc.sdk_check_search_list[:] = original_search_list
        lc.sdk_check_expected_map = {}
        lc.sdk_check_expected_order = []
        lc.sdk_check_runtime_state = {}
        lc.sdk_check_current_network = {}


def test_sdk_check_preset_contract() -> None:
    presets = lc._load_sdk_check_presets()
    _assert("C-190-Android" in presets, "C-190 Android SDK preset is missing")
    _assert("C-190-iOS" in presets, "C-190 iOS SDK preset is missing")
    _assert("C-180-Android" in presets, "C-180 Android SDK preset is missing")
    _assert("C-180-iOS" in presets, "C-180 iOS SDK preset is missing")
    preset = presets["C-190-Android"]
    _assert_equal(preset.get("platform"), "android", "C-190 Android preset platform changed")
    ios_preset = presets["C-190-iOS"]
    _assert_equal(ios_preset.get("platform"), "ios", "C-190 iOS preset platform changed")
    _assert_equal(ios_preset.get("lines"), [], "C-190 iOS preset must remain empty")
    c180_ios_preset = presets["C-180-iOS"]
    _assert_equal(c180_ios_preset.get("platform"), "ios", "C-180 iOS preset platform changed")
    c180_ios_lines = c180_ios_preset.get("lines") or []
    _assert_equal(len(c180_ios_lines), 31, "C-180 iOS preset line count changed")
    _assert_equal(c180_ios_lines[0], "Ads Network\tAdapter\tSDK", "C-180 iOS preset header changed")
    _assert("ironSource\t9.4.2.1\t9.4.2" in c180_ios_lines, "C-180 iOS ironSource entry changed")
    _assert("Appsflyer\tremoved\tremoved" in c180_ios_lines, "C-180 iOS Appsflyer entry changed")
    _assert("Firebase Crashlytics\t\t12.15.0" in c180_ios_lines, "C-180 iOS Firebase Crashlytics entry changed")
    _assert(all("http://" not in line and "https://" not in line for line in c180_ios_lines), "C-180 iOS preset must not contain links")
    c180_preset = presets["C-180-Android"]
    _assert_equal(c180_preset.get("platform"), "android", "C-180 preset platform changed")
    c180_lines = c180_preset.get("lines") or []
    _assert_equal(len(c180_lines), 33, "C-180 preset line count changed")
    _assert_equal(c180_lines[0], "Ads Network\tAdapter\tNative", "C-180 preset header changed")
    _assert("Appsflyer\t\tRemoved" in c180_lines, "C-180 Appsflyer entry changed")
    _assert(not any(line.startswith("AdQuality\t") for line in c180_lines), "C-180 AdQuality entry must remain absent")
    _assert(all("http://" not in line and "https://" not in line for line in c180_lines), "C-180 preset must not contain links")
    lines = preset.get("lines") or []
    _assert_equal(len(lines), 44, "C-190 Android preset line count changed")
    _assert_equal(lines[0], "Ads Network\tAdapter\tNative", "C-190 preset header changed")
    _assert(all("http://" not in line and "https://" not in line for line in lines), "C-190 preset must not contain documentation links")
    _assert("CloudX\t4.5.0\t4.5.0" in lines, "C-190 CloudX entry changed")
    _assert(any(line.startswith("Digital Turbine (fyber) - Cloudx\t") for line in lines), "C-190 Cloudx entries are missing")
    _assert("Meta Audience Network\t5.4.0\t6.22.0" in lines, "C-190 Meta Audience Network adapter changed")
    _assert("Mintegral - Cloudx\t17.1.71.0\t17.1.71" in lines, "Mintegral Cloudx native version changed")
    _assert("Yandex\t5.12.0\t8.3.0" in lines, "C-190 Yandex versions changed")
    _assert("Adverty\t5.2.9\t" in lines, "C-190 Adverty version changed")
    _assert("Gadsme\t1.12.6\t" in lines, "C-190 Gadsme version changed")
    _assert("AppMetrica SDK\t\t8.4.1" in lines, "C-190 AppMetrica version changed")
    cloudx_lines = [line for line in lines if " - Cloudx\t" in line]
    _assert(cloudx_lines and all(len(line.split("\t")) >= 3 and line.split("\t")[2].strip() for line in cloudx_lines), "Cloudx native versions are missing")
    _assert("Adjust\t\t5.6.1" in lines, "C-190 single SDK entry changed")

    for line in lines[1:]:
        parsed = lc._parse_sdk_expected_line(line)
        _assert(parsed is not None, f"C-190 Android entry cannot be parsed: {line}")
    for line in c180_lines[1:]:
        parsed = lc._parse_sdk_expected_line(line)
        _assert(parsed is not None, f"C-180 Android entry cannot be parsed: {line}")
    for line in c180_ios_lines[1:]:
        parsed = lc._parse_sdk_expected_line(line)
        _assert(parsed is not None, f"C-180 iOS entry cannot be parsed: {line}")

    source_text = (ROOT / "Log_checker.py").read_text(encoding="utf-8", errors="ignore")
    _assert("sdkCheckPresetPanel" in source_text, "SDK preset panel is missing")
    _assert("applySdkCheckPreset" in source_text, "SDK preset action is missing")
    _assert("/api/sdk-check-presets" in source_text, "remote SDK preset endpoint is missing")
    _assert("loadSdkCheckPresetsFromGit" in source_text, "SDK preset remote load action is missing")
    _assert("sdkCheckInput" in source_text, "manual SDK input fallback is missing")
    _assert(source_text.count('id="reloadSdkCheckPresetsBtn"') == 1, "SDK preset reload button must exist exactly once")
    _assert("clean_lines" in source_text and '"lines": clean_lines' in source_text, "empty SDK presets must remain valid")
    _assert('"Accept-Encoding": "identity"' in source_text, "SDK preset fetch must bypass stale compressed cache")


def test_rendered_sdk_preset_javascript_contract() -> None:
    response = lc.app.test_client().get("/")
    _assert_equal(response.status_code, 200, "local UI route must render")
    html = response.get_data(as_text=True)
    expected_join = r"input.value = lines.join('\n');"
    broken_join = "input.value = lines.join('" + "\n" + "');"
    _assert(expected_join in html, "rendered SDK preset JavaScript must keep the newline escape")
    _assert(broken_join not in html, "rendered SDK preset JavaScript contains a literal newline inside a string")
    _assert(
        html.index('id="sdkCheckPresetPanel"') < html.index('id="startSdkCheckBtn"'),
        "SDK preset selector must remain above Start Checking",
    )
    _assert('id="reloadSdkCheckPresetsBtn"' in html, "rendered SDK preset reload button is missing")
    _assert("loadSdkCheckPresetsFromGit();" in html, "SDK presets must reload when the app UI starts")
    _assert("loadSdkCheckPresetsFromGit(true);" in html, "preset Reload button must force a fresh GitHub request")
    _assert("reloadSdkCheckPresetsBtn" in html and "loadSdkCheckPresetsFromGit" in html, "reload button handler is missing")


def test_sdk_failed_groups_sort_first() -> None:
    groups = [
        [{"status": "PASSED"}, {"status": "PASSED"}],
        [{"status": "FAILED"}],
        [{"status": "FOUND"}],
        [{"status": "PASSED"}, {"status": "FAILED"}],
    ]
    ordered = sorted(groups, key=lc._sdk_result_group_sort_key)
    _assert(ordered[0][0]["status"] == "FAILED", "failed SDK group must be first")
    _assert(ordered[1][1]["status"] == "FAILED", "mixed failed SDK group must remain before passed groups")
    _assert(ordered[-1][0]["status"] == "FOUND", "found-only SDK group must remain after passed groups")
    _assert_equal(lc._sdk_result_status("", "1.18.3.0"), "FAILED", "missing actual with expected version must fail")
    _assert_equal(lc._sdk_result_status("", ""), "NOT_FOUND", "empty expected version must be not found")
    _assert_equal(lc._sdk_result_status("NOT FOUND", "Removed"), "PASSED", "removed SDK with missing actual must pass")
    _assert_equal(lc._sdk_result_status("MISSING", "Removed"), "PASSED", "removed SDK with missing marker must pass")


def test_release_build_marker() -> None:
    text = (ROOT / "Log_checker.py").read_text(encoding="utf-8", errors="ignore")
    _assert("v2.4.0(25)" in text, "Log_checker.py must be prepared for release 25")


def test_rewarded_bidding_filter_contract() -> None:
    source_text = (ROOT / "Log_checker.py").read_text(encoding="utf-8", errors="ignore")
    needle = 'data-message-needle="[Ad,RewardedBidding"'
    _assert(source_text.count('value="rewarded_bidding"') == 1, "RewardedBidding filter must exist exactly once")
    _assert(source_text.count('value="rewardedcap"') == 1, "RewardedCap filter must exist exactly once")
    _assert(source_text.count(needle) == 1, "RewardedBidding must use the exact message needle")
    _assert('data-message-needle="[Ad,RewardedBidding,"' not in source_text, "RewardedBidding filter must not require a trailing comma")
    _assert('data-android-only="true"' in source_text, "RewardedBidding must be Android-only")
    _assert("exactMessage.includes(state.quickMessage)" in source_text, "message filter must remain case-sensitive")
    _assert("flex items-start justify-start gap-32" in source_text, "RewardedBidding layout must stay beside the first filter column")


def test_price_rotation_exact_parser() -> None:
    source_text = (ROOT / "Log_checker.py").read_text(encoding="utf-8", errors="ignore")
    _assert('onclick="switchTab(\'PriceRotation\')">Rewarded Bidding</button>' in source_text, "Price Rotation tab label must be Rewarded Bidding")
    _assert(source_text.count('id="priceRotationTypeWaterfall"') == 1, "Waterfall filter must exist exactly once")
    _assert('value="waterfall"' in source_text, "Waterfall filter value is missing")
    valid = 'Unity : [Ad,RewardedBidding, CloudX] Raise: {"act":"demandFailedObserved","error":"WinnerBid not found"}'
    parsed = lc._parse_price_rotation_log(valid, "device-price")
    _assert(parsed is not None, "Price Rotation parser must accept the exact marker")
    _assert_equal(parsed["type"], "CloudX", "Price Rotation type should come from the marker")
    _assert('"act": "demandFailedObserved"' in parsed["details"], "Price Rotation details should format JSON")
    waterfall = lc._parse_price_rotation_log('Unity : [Ad,RewardedBidding, Waterfall] Raise: {"act":"bid"}', "device-price")
    _assert(waterfall is not None, "Price Rotation parser must accept the Waterfall marker")
    _assert_equal(waterfall["type"], "Waterfall", "Waterfall type should come from the marker")
    cap = lc._parse_price_rotation_log('Unity : [Ad,RewardedBidding] RewardedCapService: {"act":"cap"}', "device-price")
    _assert(cap is not None, "Price Rotation parser must accept the RewardedCapService marker")
    _assert_equal(cap["type"], "RewardedCap", "RewardedCapService must use the RewardedCap type")
    plain = lc._parse_price_rotation_log('Unity : [Ad,RewardedBidding] Raise: {"act":"bid"}', "device-price")
    _assert(plain is not None, "Price Rotation parser must accept a plain RewardedBidding marker")
    _assert_equal(plain["type"], "RewardedBidding", "A plain marker must use the RewardedBidding type")
    _assert(lc._parse_price_rotation_log(valid.replace("[Ad,RewardedBidding,", "[Ad,RewardedBiddingX,"), "device-price") is None, "Price Rotation marker must be exact")


def test_release_payload_sync() -> None:
    source_text = (ROOT / "Log_checker.py").read_text(encoding="utf-8", errors="ignore")
    payload_text = (ROOT / "Updates_2_3" / "Log_checker.py").read_text(encoding="utf-8", errors="ignore")

    _assert_equal(payload_text, source_text, "source and release payload must be byte-for-byte identical")

    markers = {
        "release_badge": r"v2\.4\.0\((\d+)\)",
        "html_title": r"<title>([^<]+)</title>",
        "brightsdk_tab": r"switchTab\('BrightSDK'\)",
        "tm_ios_package": r'data-ios-value="([^"]+)"\s+data-ios-label="TM - ([^"]+)"',
        "check_update_call": r"result = remote_update\.check_for_updates\(\)",
    }

    for label, pattern in markers.items():
        source_match = re.search(pattern, source_text)
        payload_match = re.search(pattern, payload_text)
        _assert(source_match is not None, f"source missing {label}")
        _assert(payload_match is not None, f"payload missing {label}")
        _assert_equal(
            source_match.groups() or (source_match.group(0),),
            payload_match.groups() or (payload_match.group(0),),
            f"source/payload drift detected for {label}",
        )


def test_update_candidate_does_not_downgrade() -> None:
    candidates = [
        {"update_dir": "/tmp/v15", "build": 15, "source": "old"},
        {"update_dir": "/tmp/v16", "build": 16, "source": "current"},
    ]
    selected = desktop._select_prepared_update_candidate(candidates, bundled_build=16)
    _assert_equal(selected["build"], 16, "bundled v16 must not load a v15 prepared update")
    _assert_equal(
        desktop._select_prepared_update_candidate(candidates[:1], bundled_build=16),
        None,
        "a stale prepared update must be ignored when no newer payload exists",
    )
    _assert_equal(
        desktop._select_prepared_update_candidate(candidates[:1], bundled_build=None)["build"],
        15,
        "legacy clients without a detected bundled build must keep update compatibility",
    )
    compatibility_candidate = [{"update_dir": "/tmp/v25", "build": 55, "source": "channel_state"}]
    _assert_equal(
        desktop._select_prepared_update_candidate(compatibility_candidate, bundled_build=47)["build"],
        55,
        "legacy v2.3.0(47) clients must accept the v2.4.0(25) compatibility payload",
    )


def test_update_flow_legacy_to_v25() -> None:
    import remote_update as updater

    manifest_bytes = (ROOT / "Updates_2_3" / "remote_manifest.json").read_bytes()
    payloads = {
        "Log_checker.py": (ROOT / "Updates_2_3" / "Log_checker.py").read_bytes(),
        "remote_update.py": (ROOT / "remote_update.py").read_bytes(),
        "sdk_check_presets.json": (ROOT / "sdk_check_presets.json").read_bytes(),
    }
    original_home = os.environ.get("HOME")
    original_bundle_build = os.environ.get("EVENTINSPECTOR_BUNDLED_BUILD")
    original_bundle_source = os.environ.get("EVENTINSPECTOR_BUNDLED_BUILD_SOURCE")
    original_download_first = updater._download_first
    original_download_verified = updater._download_verified
    try:
        with tempfile.TemporaryDirectory(prefix="eventinspector_harness_") as temp_home:
            os.environ["HOME"] = temp_home
            os.environ["EVENTINSPECTOR_BUNDLED_BUILD"] = "47"
            os.environ["EVENTINSPECTOR_BUNDLED_BUILD_SOURCE"] = "detected"

            def fake_download_first(_urls, _timeout):
                return manifest_bytes, "harness://remote_manifest.json"

            def fake_download_verified(urls, _timeout, _expected_sha256=""):
                rel_path = next((path for path in payloads if any(url.endswith("/" + path) for url in urls)), None)
                _assert(rel_path is not None, f"unexpected update payload URL list: {urls}")
                return payloads[rel_path], f"harness://{rel_path}"

            updater._download_first = fake_download_first
            updater._download_verified = fake_download_verified

            first = updater.check_for_updates(force_refresh=True)
            _assert_equal(first.get("status"), "updated", "legacy v2.3.0(47) client must prepare v2.4.0(25) payload")
            _assert_equal(first.get("version"), "2026-08-14-1-2.4.0-55", "prepared payload compatibility version mismatch")
            prepared = updater.get_prepared_update_info()
            _assert_equal(prepared.get("build"), 55, "prepared payload compatibility build mismatch")
            _assert(os.path.exists(os.path.join(prepared["update_dir"], "Log_checker.py")), "prepared Log_checker.py missing")
            _assert(os.path.exists(os.path.join(prepared["update_dir"], "sdk_check_presets.json")), "prepared SDK preset file missing")

            second = updater.check_for_updates()
            _assert_equal(second.get("status"), "up_to_date", "same v2.4.0(25) payload must not download repeatedly")
    finally:
        updater._download_first = original_download_first
        updater._download_verified = original_download_verified
        if original_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = original_home
        if original_bundle_build is None:
            os.environ.pop("EVENTINSPECTOR_BUNDLED_BUILD", None)
        else:
            os.environ["EVENTINSPECTOR_BUNDLED_BUILD"] = original_bundle_build
        if original_bundle_source is None:
            os.environ.pop("EVENTINSPECTOR_BUNDLED_BUILD_SOURCE", None)
        else:
            os.environ["EVENTINSPECTOR_BUNDLED_BUILD_SOURCE"] = original_bundle_source


def test_build_scripts_clean_outputs() -> None:
    mac_script = (ROOT / "build" / "macos" / "build_macos.sh").read_text(encoding="utf-8", errors="ignore")
    win_portable_script = (ROOT / "build" / "windows" / "build_portable.bat").read_text(encoding="utf-8", errors="ignore")
    win_installer_script = (ROOT / "build" / "windows" / "build_windows.bat").read_text(encoding="utf-8", errors="ignore")

    mac_expected = [
        'rm -rf "dist/EventInspector.app"',
        'rm -f "dist/EventInspector.dmg"',
        'rm -rf "build/EventInspector"',
    ]
    for needle in mac_expected:
        _assert(needle in mac_script, f"build_macos.sh must clean stale artifact: {needle}")

    _assert('MACOS_TARGET_ARCH="${MACOS_TARGET_ARCH:-universal2}"' in mac_script, "macOS build must default to universal2")
    _assert('--target-arch "$MACOS_TARGET_ARCH"' in mac_script, "macOS build must pass the target architecture")
    _assert('--exclude-module "markupsafe._speedups"' in mac_script, "macOS universal build must avoid the arm64-only MarkupSafe speedup")
    _assert('--add-data "Log_checker.py:."' in mac_script, "macOS build must package the bundled release marker")
    _assert('--add-data "sdk_check_presets.json:."' in mac_script, "macOS build must package SDK presets")
    _assert('--add-data "sdk_check_presets.json;."' in win_portable_script, "Windows portable build must package SDK presets")
    _assert('--add-data "sdk_check_presets.json;."' in win_installer_script, "Windows installer build must package SDK presets")
    spec_text = (ROOT / "EventInspector.spec").read_text(encoding="utf-8", errors="ignore")
    _assert("('sdk_check_presets.json', '.')" in spec_text, "PyInstaller spec must package SDK presets")

    win_expected = [
        'if exist "dist\\EventInspector" rmdir /s /q "dist\\EventInspector"',
        'if exist "build\\EventInspector" rmdir /s /q "build\\EventInspector"',
    ]
    for needle in win_expected:
        _assert(needle in win_portable_script, f"build_portable.bat must clean stale artifact: {needle}")
        _assert(needle in win_installer_script, f"build_windows.bat must clean stale artifact: {needle}")


def test_windows_update_recovery_script() -> None:
    script_path = ROOT / "tools" / "reset_update_state_windows.bat"
    text = script_path.read_text(encoding="utf-8", errors="ignore")
    _assert('TARGET_VERSION=2026-08-14-1-2.4.0-55' in text, "windows recovery script must target the current compatibility sequence")
    _assert('remote_manifest.json' in text, "windows recovery script must seed the current manifest")
    legacy_scripts = sorted((ROOT / "tools").glob("bootstrap_windows_to_v*.bat"))
    _assert(not legacy_scripts, f"remove legacy Windows bootstrap scripts: {[p.name for p in legacy_scripts]}")


TESTS: List[Callable[[], None]] = [
    test_manifest_contract,
    test_manifest_payload_integrity,
    test_package_code_mapping,
    test_installation_id_state_machine,
    test_installation_id_log_parsing,
    test_sdk_exact_contracts,
    test_cloudx_sdk_adapter_metadata,
    test_sdk_check_preset_contract,
    test_rendered_sdk_preset_javascript_contract,
    test_sdk_failed_groups_sort_first,
    test_release_build_marker,
    test_rewarded_bidding_filter_contract,
    test_price_rotation_exact_parser,
    test_release_payload_sync,
    test_update_candidate_does_not_downgrade,
    test_update_flow_legacy_to_v25,
    test_build_scripts_clean_outputs,
    test_windows_update_recovery_script,
]


def run_tests(selected: Iterable[Callable[[], None]]) -> List[HarnessResult]:
    results: List[HarnessResult] = []
    for test in selected:
        try:
            test()
            results.append(HarnessResult(test.__name__, True, "ok"))
        except Exception as exc:  # pragma: no cover - harness should surface the failure directly
            results.append(HarnessResult(test.__name__, False, str(exc)))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="EventInspector local harness")
    parser.add_argument("--json", action="store_true", help="Emit JSON results")
    parser.add_argument("--only", nargs="*", default=[], help="Run only named tests")
    args = parser.parse_args()

    selected = TESTS
    if args.only:
        wanted = set(args.only)
        selected = [test for test in TESTS if test.__name__ in wanted]
        missing = wanted - {test.__name__ for test in selected}
        if missing:
            print(f"Unknown test name(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2

    results = run_tests(selected)
    failures = [result for result in results if not result.passed]

    if args.json:
        print(json.dumps([result.__dict__ for result in results], indent=2, ensure_ascii=False))
    else:
        for result in results:
            status = "PASS" if result.passed else "FAIL"
            print(f"{status} {result.name}: {result.message}")

    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
