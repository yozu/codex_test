from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("out")
AUDIO = OUT / "previews"
OUT.mkdir(exist_ok=True)
AUDIO.mkdir(exist_ok=True)

SEARCH_TERMS = [
    "西武鉄道 駅メロディ オリジナル",
    "西武鉄道 駅メロディ",
    "副都心線 発車メロディ Vol.1",
    "おれは怪物くんだ 発車メロディ",
    "きれいな川 発車メロディ",
    "たのしい場所 発車メロディ",
    "銀河鉄道999 発車メロディ",
    "DESIRE 情熱 清瀬 発車メロディ",
    "セカンド・ラブ 清瀬 発車メロディ",
    "となりのトトロ 所沢 発車メロディ",
    "吠えろライオンズ 発車メロディ",
    "若き獅子たち 発車メロディ",
    "地平を駈ける獅子を見た 発車メロディ",
    "茶摘み 入間市 発車メロディ",
    "旅立ちの日に 西武秩父 発車メロディ",
    "オーバーフロー 発車メロディ",
    "駅ストレッチ 発車メロディ",
    "キャロット 発車メロディ",
    "無休 発車メロディ",
]

TARGET_WORDS = [
    "西武メロディ", "おれは怪物くんだ", "きれいな川", "たのしい場所",
    "銀河鉄道999", "DESIRE", "セカンド・ラブ", "となりのトトロ",
    "吠えろ", "若き獅子", "地平を駈ける", "茶摘み", "旅立ちの日に",
    "オーバーフロー", "駅ストレッチ", "キャロット", "無休",
]


def normalize(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").lower().replace(" ", "")


def safe_name(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[^0-9A-Za-zぁ-んァ-ヶ一-龠._-]+", "_", s)
    return s.strip("_")[:100] or "track"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def download(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as response, path.open("wb") as f:
        f.write(response.read())


all_results: dict[int, dict] = {}
search_log: list[dict] = []
for term in SEARCH_TERMS:
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": term, "country": "JP", "media": "music", "entity": "song", "limit": 200}
    )
    try:
        data = fetch_json(url)
        search_log.append({"term": term, "url": url, "count": data.get("resultCount", 0)})
        for item in data.get("results", []):
            tid = item.get("trackId")
            if tid:
                all_results[int(tid)] = item
    except Exception as exc:
        search_log.append({"term": term, "url": url, "error": repr(exc)})
    time.sleep(0.25)

selected: list[dict] = []
for item in all_results.values():
    hay = normalize(" ".join(str(item.get(k, "")) for k in ["trackName", "collectionName", "artistName"]))
    if not any(normalize(word) in hay for word in TARGET_WORDS):
        continue
    row = {
        key: item.get(key)
        for key in [
            "trackId", "trackName", "collectionId", "collectionName", "artistName",
            "previewUrl", "trackTimeMillis", "releaseDate", "primaryGenreName",
        ]
    }
    selected.append(row)

selected.sort(key=lambda x: (str(x.get("collectionName")), int(x.get("trackId") or 0)))

for row in selected:
    preview = row.get("previewUrl")
    if not preview:
        row["download"] = "no_preview"
        continue
    suffix = Path(urllib.parse.urlparse(preview).path).suffix or ".m4a"
    name = f"{row['trackId']}_{safe_name(str(row.get('trackName')))}{suffix}"
    path = AUDIO / name
    try:
        download(preview, path)
        row["download"] = str(path)
        row["bytes"] = path.stat().st_size
    except Exception as exc:
        row["download"] = "error"
        row["downloadError"] = repr(exc)

(OUT / "search-log.json").write_text(json.dumps(search_log, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "tracks.json").write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "summary.txt").write_text(
    f"searches={len(SEARCH_TERMS)}\nunique_results={len(all_results)}\nselected={len(selected)}\n"
    + "\n".join(f"{r.get('trackId')}\t{r.get('trackName')}\t{r.get('collectionName')}\t{r.get('download')}" for r in selected),
    encoding="utf-8",
)
print((OUT / "summary.txt").read_text(encoding="utf-8"))
