from __future__ import annotations

import csv
import json
import subprocess
import urllib.request
from pathlib import Path

OUT = Path("metro-out")
SRC = OUT / "source"
WAV = OUT / "wav"
MIDI = OUT / "basic-pitch"
SRC.mkdir(parents=True, exist_ok=True)
WAV.mkdir(parents=True, exist_ok=True)
MIDI.mkdir(parents=True, exist_ok=True)

TRACKS = {
    "kotake_overflow_p1": {
        "trackId": 738324258,
        "title": "小竹向原A線【1番線】(オーバーフロー)",
        "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview71/v4/44/61/c6/4461c6e9-e2e3-65ae-db00-48ef83e260de/mzaf_9026899164563679297.plus.aac.p.m4a",
    },
    "kotake_mukyu_p4": {
        "trackId": 738324259,
        "title": "小竹向原B線【4番線】(無休)",
        "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview71/v4/6f/4c/4a/6f4c4aab-0b39-0d35-ce79-01093a0a628a/mzaf_1201647162927221737.plus.aac.p.m4a",
    },
    "kotake_eki_stretch_p2": {
        "trackId": 738324262,
        "title": "小竹向原C線【2番線】(駅ストレッチ)",
        "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview71/v4/e0/ba/bc/e0babc33-20fe-8b07-7540-ec8de814d459/mzaf_8048375228634601170.plus.aac.p.m4a",
    },
    "kotake_carrot_p3": {
        "trackId": 738324266,
        "title": "小竹向原D線【3番線】(キャロット)",
        "url": "https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview71/v4/09/15/fd/0915fd64-8406-857c-7fc1-43db6668ac84/mzaf_5051502831314148715.plus.aac.p.m4a",
    },
}

manifest = {}
for key, info in TRACKS.items():
    src = SRC / f"{key}.m4a"
    wav = WAV / f"{key}.wav"
    req = urllib.request.Request(info["url"], headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as response, src.open("wb") as f:
        f.write(response.read())
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
        "-ac", "1", "-ar", "22050", str(wav)
    ], check=True)
    manifest[key] = {**info, "source": str(src), "wav": str(wav), "sourceBytes": src.stat().st_size}

from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH

predict_and_save(
    [str(WAV / f"{key}.wav") for key in TRACKS],
    str(MIDI),
    save_midi=True,
    sonify_midi=True,
    save_model_outputs=False,
    save_notes=True,
    model_or_model_path=ICASSP_2022_MODEL_PATH,
    onset_threshold=0.45,
    frame_threshold=0.25,
    minimum_note_length=80.0,
    minimum_frequency=110.0,
    maximum_frequency=4186.0,
    multiple_pitch_bends=False,
    melodia_trick=True,
)

(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"tracks": len(TRACKS), "midiFiles": len(list(MIDI.glob("*.mid"))), "csvFiles": len(list(MIDI.glob("*.csv")))}, ensure_ascii=False, indent=2))
