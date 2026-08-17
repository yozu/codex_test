from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

OUT = Path("alt-out")
AUDIO = OUT / "audio"
META = OUT / "metadata"
AUDIO.mkdir(parents=True, exist_ok=True)
META.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "ore_wa_kaibutsu_kun": ["vzwO-5h92Nk"],
    "ginga_tetsudo_999": ["uTqUiqszKAg"],
    "desire_jonetsu": ["CCfRM-2M62k"],
    "second_love": ["bbPm2q65NiE"],
    "tonari_no_totoro": ["b-L7NwOQ4Oo"],
    "hoero_lions": ["gaFtb-_Vp7Y"],
    "chatsumi": ["69NbUBwY5zk"],
    "tabidachi_no_hi_ni": ["jucLp9wr5kM"],
    "wakaki_shishitachi": ["vodkKtVrf4A"],
    "chihei_wo_kakeru_shishi_wo_mita": ["DhQol58eG1w"],
    "seibu_melody_1": ["z4YjhUR1UUU", "KM3-STvmsuY", "zUwTEPOssY8"],
    "seibu_melody_2": ["jtm08FW2QGw", "fE-V3zw8g5M", "cPIR2JcKSrQ", "GNQRBCKMvZQ"],
    "seibu_melody_3": ["XA8X5IYU4VQ", "G0AESuRX8jI", "FFI2gXsvOjY", "ZGzdxe__pMc"],
    "seibu_melody_4": ["GNQRBCKMvZQ", "KaunqEJO67s", "ZGzdxe__pMc", "NFzYeKvcWVY"],
    "seibu_melody_6": ["GNQRBCKMvZQ", "vD1tLKoW64E", "06B4u2sWGgQ"],
    "kireina_kawa": ["ZPGCuWflTDM", "Dpfa1o4bMT8", "0Nk2UsVvfxk", "8S8usnydjFE"],
    "tanoshii_basho": ["ZPGCuWflTDM", "0Nk2UsVvfxk", "02mLmN7aLzM"],
    "seibu_kyujo_electronic_bell": ["Hgifc8uuEWc", "SxSJ4kBOxpE", "L0IS_TN3fKo", "HWWrgKLf1Pc"],
    "higashi_hanno_departure_signal": ["0d7Cwokm5OU", "GaHsYwFZLPQ", "xcUatrsrb0o"],
    "koma_departure_signal": ["rjOuBb0G3rc", "2yYZ_N50Ieg", "sCLNmbhctdw", "P7O99E_RYNY", "UnXbHqoGUb8"],
    "musashi_yokote_departure_signal": ["SYkIXWAtZtA"],
    "higashi_agano_departure_signal": ["MwoFCXrpXBw", "82iC-l1GRV8", "VdfP2KbPuiQ"],
    "agano_departure_signal": ["GaHsYwFZLPQ", "PR6DXBnxGuE", "82iC-l1GRV8", "rjOuBb0G3rc"],
    "nishi_agano_departure_signal": ["xcUatrsrb0o", "MwoFCXrpXBw", "82iC-l1GRV8"],
    "shomaru_departure_signal": ["y_YoRnt4DXQ", "x6MBGT90GLk", "fCYMAYl7fIc"],
    "ashigakubo_departure_signal": ["8Qgx7YSlJs0", "--deLeSroqk", "2NkoN_AfwjI"],
    "yokoze_departure_signal": ["0d7Cwokm5OU", "MbR5Wyaa16E", "GaHsYwFZLPQ", "y_YoRnt4DXQ"],
}

PIPED_INSTANCES = [
    "https://pipedapi.adminforge.de",
    "https://pipedapi.reallyaweso.me",
    "https://pipedapi.private.coffee",
    "https://pipedapi.nosebs.ru",
    "https://api.piped.private.coffee",
    "https://pipedapi.kavin.rocks",
    "https://pipedapi-libre.kavin.rocks",
]

INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://yt.chocolatemoo53.com",
    "https://inv.thepixora.com",
    "https://invidious.private.coffee",
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/136 Safari/537.36"})


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def download(url: str, path: Path) -> tuple[bool, str]:
    try:
        with SESSION.get(url, timeout=90, stream=True, allow_redirects=True) as r:
            if r.status_code != 200:
                return False, f"http_{r.status_code}"
            content_type = r.headers.get("content-type", "")
            total = 0
            with path.open("wb") as f:
                for chunk in r.iter_content(1024 * 512):
                    if not chunk:
                        continue
                    f.write(chunk)
                    total += len(chunk)
                    if total > 100 * 1024 * 1024:
                        break
            if total < 10_000:
                path.unlink(missing_ok=True)
                return False, f"too_small_{total}_{content_type}"
            return True, f"ok_{total}_{content_type}"
    except Exception as exc:
        path.unlink(missing_ok=True)
        return False, repr(exc)


def choose_piped_audio(payload: dict) -> dict | None:
    streams = payload.get("audioStreams") or []
    streams = [s for s in streams if s.get("url")]
    if not streams:
        return None
    # Prefer a compact m4a/opus stream around 128–192 kbps; all are only for analysis.
    def score(s: dict) -> tuple:
        fmt = str(s.get("format") or s.get("mimeType") or "").lower()
        bitrate = int(s.get("bitrate") or 0)
        preferred = 0 if ("m4a" in fmt or "mp4" in fmt or "opus" in fmt or "webm" in fmt) else 1
        distance = abs((bitrate or 128000) - 160000)
        return preferred, distance, -bitrate
    return sorted(streams, key=score)[0]


def try_piped(video_id: str, log: list[dict]) -> tuple[str | None, dict | None]:
    for base in PIPED_INSTANCES:
        endpoint = f"{base.rstrip('/')}/streams/{video_id}"
        try:
            r = SESSION.get(endpoint, timeout=30)
            log.append({"method": "piped", "endpoint": endpoint, "status": r.status_code, "bytes": len(r.content)})
            if r.status_code != 200:
                continue
            payload = r.json()
            stream = choose_piped_audio(payload)
            if stream:
                meta = {
                    "frontend": "piped",
                    "instance": base,
                    "endpoint": endpoint,
                    "title": payload.get("title"),
                    "duration": payload.get("duration"),
                    "uploader": payload.get("uploader"),
                    "stream": stream,
                }
                return stream.get("url"), meta
        except Exception as exc:
            log.append({"method": "piped", "endpoint": endpoint, "error": repr(exc)})
    return None, None


def choose_invidious_audio(payload: dict) -> dict | None:
    streams = payload.get("adaptiveFormats") or []
    streams = [s for s in streams if s.get("url") and str(s.get("type", "")).startswith("audio/")]
    if not streams:
        return None
    return sorted(streams, key=lambda s: abs(int(s.get("bitrate") or 128000) - 160000))[0]


def try_invidious(video_id: str, log: list[dict]) -> tuple[str | None, dict | None]:
    for base in INVIDIOUS_INSTANCES:
        endpoint = f"{base.rstrip('/')}/api/v1/videos/{video_id}"
        try:
            r = SESSION.get(endpoint, timeout=30)
            log.append({"method": "invidious", "endpoint": endpoint, "status": r.status_code, "bytes": len(r.content)})
            if r.status_code != 200:
                continue
            payload = r.json()
            stream = choose_invidious_audio(payload)
            if stream:
                meta = {
                    "frontend": "invidious",
                    "instance": base,
                    "endpoint": endpoint,
                    "title": payload.get("title"),
                    "duration": payload.get("lengthSeconds"),
                    "uploader": payload.get("author"),
                    "stream": {k: stream.get(k) for k in ["itag", "type", "bitrate", "audioQuality", "audioSampleRate", "audioChannels", "url"]},
                }
                return stream.get("url"), meta
        except Exception as exc:
            log.append({"method": "invidious", "endpoint": endpoint, "error": repr(exc)})
    return None, None


manifest: dict[str, dict] = {}
for key, ids in TARGETS.items():
    key_log: list[dict] = []
    manifest[key] = {"candidateIds": ids, "attempts": key_log, "downloaded": []}
    for index, video_id in enumerate(ids[:4], start=1):
        url, meta = try_piped(video_id, key_log)
        if not url:
            url, meta = try_invidious(video_id, key_log)
        if not url or not meta:
            continue
        ext = ".m4a"
        fmt = str(meta.get("stream", {}).get("format") or meta.get("stream", {}).get("type") or "").lower()
        if "webm" in fmt or "opus" in fmt:
            ext = ".webm"
        path = AUDIO / f"{key}_{index:02d}_{video_id}{ext}"
        ok, detail = download(url, path)
        key_log.append({"method": "stream_download", "videoId": video_id, "ok": ok, "detail": detail, "path": str(path)})
        if ok:
            rec = {"videoId": video_id, "path": str(path), **meta}
            manifest[key]["downloaded"].append(rec)
            # One valid source per target is enough for this stage; alternatives remain in manifest.
            break
    write_json(META / f"{key}.json", manifest[key])
    time.sleep(0.2)

write_json(OUT / "manifest.json", manifest)
summary = {
    "targets": len(TARGETS),
    "targetsDownloaded": sum(bool(v["downloaded"]) for v in manifest.values()),
    "audioFiles": len(list(AUDIO.glob("*"))),
    "failed": [k for k, v in manifest.items() if not v["downloaded"]],
}
write_json(OUT / "summary.json", summary)
print(json.dumps(summary, ensure_ascii=False, indent=2))
