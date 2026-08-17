from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

OUT = Path("direct-out")
AUDIO = OUT / "audio"
HTML = OUT / "html"
META = OUT / "metadata"
for p in [AUDIO, HTML, META]:
    p.mkdir(parents=True, exist_ok=True)

DIRECT = {
    "seibu_melody_1_shinjuku_up_nakai": "https://img.atwiki.jp/seibuinfo91/attach/22/117/%E4%B8%AD%E4%BA%952%281%29.mp3",
    "seibu_melody_1_shinjuku_up_araiyakushi": "https://img.atwiki.jp/seibuinfo91/attach/22/116/%E8%96%AC%E5%B8%AB2.mp3",
    "seibu_melody_2_shinjuku_down_kodaira": "https://img.atwiki.jp/seibuinfo91/attach/22/80/%E5%B0%8F%E5%B9%B32.mp3",
    "seibu_melody_3_ikebukuro_up_higashimurayama": "https://img.atwiki.jp/seibuinfo91/attach/22/79/%E6%9D%B1%E6%9D%91%E5%B1%B13.mp3",
    "seibu_melody_4_ikebukuro_down_nishitokorozawa": "https://img.atwiki.jp/seibuinfo91/attach/22/162/%E8%A5%BF%E6%89%80%E6%B2%A22.mp3",
    "kiyose_desire": "https://img.atwiki.jp/seibuinfo91/attach/22/164/%E6%B8%85%E7%80%AC1.mp3",
    "kiyose_second_love": "https://img.atwiki.jp/seibuinfo91/attach/22/163/%E6%B8%85%E7%80%AC3.mp3",
    "tokorozawa_totoro_before_chorus": "https://img.atwiki.jp/seibuinfo91/attach/22/84/20251223_%E6%89%80%E6%B2%A2%234%202.mp3",
    "tokorozawa_totoro_ending": "https://img.atwiki.jp/seibuinfo91/attach/22/86/20251223_%E6%89%80%E6%B2%A2%235%202.mp3",
    "nishitokorozawa_hoero_current": "https://img.atwiki.jp/seibuinfo91/attach/22/94/20251223_%E8%A5%BF%E6%89%80%E6%B2%A2%232%281%29.mp3",
    "nishitokorozawa_hoero_alt": "https://img.atwiki.jp/seibuinfo91/attach/22/90/%E5%90%A0%E3%81%88%E3%82%8D%E3%83%A9%E3%82%A4%E3%82%AA%E3%83%B3%E3%82%BA.mp3",
    "shimoyamaguchi_wakaki": "https://img.atwiki.jp/seibuinfo91/attach/22/159/%E4%B8%8B%E5%B1%B1%E5%8F%A31.mp3",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/136 Safari/537.36"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read()


manifest: dict[str, dict] = {}
for key, url in DIRECT.items():
    suffix = Path(urllib.parse.urlparse(url).path).suffix or ".mp3"
    path = AUDIO / f"{key}{suffix}"
    try:
        body = fetch(url)
        path.write_bytes(body)
        manifest[key] = {"url": url, "path": str(path), "bytes": len(body), "status": "downloaded"}
    except Exception as exc:
        manifest[key] = {"url": url, "status": "failed", "error": repr(exc)}

# Scrape HSM for the actual linked audio names used for the 4000-series one-man door chime
# and the Seibu departure buzzer. The references are for note/frequency analysis only.
hsm_url = "https://hsm.uijin.com/"
try:
    raw = fetch(hsm_url)
    (HTML / "hsm.html").write_bytes(raw)
    text = raw.decode("utf-8", errors="replace")
    links = []
    for href, label in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, flags=re.I | re.S):
        clean = re.sub(r"<[^>]+>", "", label)
        links.append({"href": urllib.parse.urljoin(hsm_url, href), "label": clean.strip()})
    # Also keep all src URLs because some players use <audio src> or <embed src>.
    for src in re.findall(r'(?:src|data-src)=["\']([^"\']+)["\']', text, flags=re.I):
        links.append({"href": urllib.parse.urljoin(hsm_url, src), "label": "src"})
    (META / "hsm-links.json").write_text(json.dumps(links, ensure_ascii=False, indent=2), encoding="utf-8")
    for i, row in enumerate(links):
        href = row["href"]
        if not re.search(r"\.(?:mp3|wav|ogg|m4a)(?:\?|$)", href, re.I):
            continue
        try:
            body = fetch(href)
            name = Path(urllib.parse.urlparse(href).path).name or f"hsm_{i}.bin"
            target = AUDIO / f"hsm_{i:03d}_{name}"
            target.write_bytes(body)
            row["downloadedPath"] = str(target)
            row["bytes"] = len(body)
        except Exception as exc:
            row["downloadError"] = repr(exc)
    (META / "hsm-links-after-download.json").write_text(json.dumps(links, ensure_ascii=False, indent=2), encoding="utf-8")
except Exception as exc:
    (META / "hsm-error.txt").write_text(repr(exc), encoding="utf-8")

(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({
    "directTargets": len(DIRECT),
    "directDownloaded": sum(v.get("status") == "downloaded" for v in manifest.values()),
    "audioFiles": len(list(AUDIO.glob("*"))),
}, ensure_ascii=False, indent=2))
