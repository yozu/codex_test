from __future__ import annotations

import json
import subprocess
from pathlib import Path

OUT = Path("reference-out")
AUDIO = OUT / "audio"
META = OUT / "metadata"
AUDIO.mkdir(parents=True, exist_ok=True)
META.mkdir(parents=True, exist_ok=True)

EXACT = {
    "ore_wa_kaibutsu_kun": "https://www.youtube.com/watch?v=vzwO-5h92Nk",
    "ginga_tetsudo_999": "https://www.youtube.com/watch?v=uTqUiqszKAg",
    "desire_jonetsu": "https://www.youtube.com/watch?v=CCfRM-2M62k",
    "second_love": "https://www.youtube.com/watch?v=bbPm2q65NiE",
    "tonari_no_totoro": "https://www.youtube.com/watch?v=b-L7NwOQ4Oo",
    "hoero_lions": "https://www.youtube.com/watch?v=gaFtb-_Vp7Y",
    "chatsumi": "https://www.youtube.com/watch?v=69NbUBwY5zk",
    "tabidachi_no_hi_ni": "https://www.youtube.com/watch?v=jucLp9wr5kM",
    "wakaki_shishitachi": "https://www.youtube.com/watch?v=vodkKtVrf4A",
    "chihei_wo_kakeru_shishi_wo_mita": "https://www.youtube.com/watch?v=DhQol58eG1w",
}

SEARCH = {
    "seibu_melody_1": "西武メロディ1 新宿線 上り 発車メロディ メロディのみ",
    "seibu_melody_2": "西武メロディ2 新宿線 下り 発車メロディ メロディのみ",
    "seibu_melody_3": "西武メロディ3 池袋線 上り 発車メロディ メロディのみ",
    "seibu_melody_4": "西武メロディ4 池袋線 下り 発車メロディ メロディのみ",
    "seibu_melody_6": "西武メロディ6 特急 発車メロディ 飯能 メロディのみ",
    "kireina_kawa": "練馬高野台 きれいな川 発車メロディ",
    "tanoshii_basho": "練馬高野台 たのしい場所 発車メロディ",
    "seibu_kyujo_electronic_bell": "西武球場前 7番線 8番線 電子ベル 発車",
    "sayama_7000_boarding_promotion": "西武7000系 狭山線 乗降促進音 下山口 2026",
    "higashi_hanno_departure_signal": "東飯能 西武線 発車 ベル ブザー ワンマン",
    "koma_departure_signal": "高麗駅 西武 発車 ベル ブザー ワンマン",
    "musashi_yokote_departure_signal": "武蔵横手駅 西武 発車 ベル ブザー ワンマン",
    "higashi_agano_departure_signal": "東吾野駅 西武 発車 ベル ブザー ワンマン",
    "agano_departure_signal": "吾野駅 西武 発車 ベル ブザー ワンマン",
    "nishi_agano_departure_signal": "西吾野駅 西武 発車 ベル ブザー ワンマン",
    "shomaru_departure_signal": "正丸駅 西武 発車 ベル ブザー ワンマン",
    "ashigakubo_departure_signal": "芦ヶ久保駅 西武 発車 ベル ブザー ワンマン",
    "yokoze_departure_signal": "横瀬駅 西武 発車 ベル ブザー ワンマン",
}


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, text=True, capture_output=True, check=check)


def dump_metadata(key: str, source: str) -> list[dict]:
    proc = run([
        "yt-dlp", "--dump-single-json", "--no-warnings", "--skip-download", source
    ], check=False)
    if proc.returncode != 0:
        (META / f"{key}.error.txt").write_text(proc.stderr, encoding="utf-8")
        return []
    data = json.loads(proc.stdout)
    entries = data.get("entries") or [data]
    rows = []
    for item in entries:
        if not item:
            continue
        rows.append({
            k: item.get(k)
            for k in ["id", "title", "webpage_url", "duration", "channel", "upload_date", "description"]
        })
    (META / f"{key}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows


def download_audio(key: str, source: str, limit: int | None = None) -> None:
    template = str(AUDIO / f"{key}_%(playlist_index|00)02d_%(id)s.%(ext)s")
    args = [
        "yt-dlp", "--no-warnings", "--no-playlist" if limit is None else "--yes-playlist",
        "-f", "bestaudio[ext=m4a]/bestaudio/best",
        "-o", template,
    ]
    if limit is not None:
        args.extend(["--playlist-end", str(limit)])
    args.append(source)
    proc = run(args, check=False)
    if proc.returncode != 0:
        (META / f"{key}.download-error.txt").write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")


manifest: dict[str, dict] = {"exact": {}, "search": {}}
for key, url in EXACT.items():
    rows = dump_metadata(key, url)
    manifest["exact"][key] = {"source": url, "candidates": rows}
    download_audio(key, url)

for key, query in SEARCH.items():
    source = f"ytsearch3:{query}"
    rows = dump_metadata(key, source)
    manifest["search"][key] = {"query": query, "candidates": rows}
    download_audio(key, source, limit=3)

(OUT / "reference-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({
    "exact": len(EXACT),
    "search": len(SEARCH),
    "audioFiles": len(list(AUDIO.glob("*"))),
}, ensure_ascii=False, indent=2))
