from __future__ import annotations
import json, subprocess, urllib.request
from pathlib import Path
OUT=Path('direct-transcribe-out'); SRC=OUT/'source'; WAV=OUT/'wav'; MIDI=OUT/'basic-pitch'
for p in (SRC,WAV,MIDI): p.mkdir(parents=True,exist_ok=True)
TRACKS={
'seibu_melody_1_shinjuku_up':'https://img.atwiki.jp/seibuinfo91/attach/22/117/%E4%B8%AD%E4%BA%952%281%29.mp3',
'seibu_melody_2_shinjuku_down':'https://img.atwiki.jp/seibuinfo91/attach/22/80/%E5%B0%8F%E5%B9%B32.mp3',
'seibu_melody_3_ikebukuro_up':'https://img.atwiki.jp/seibuinfo91/attach/22/79/%E6%9D%B1%E6%9D%91%E5%B1%B13.mp3',
'seibu_melody_4_ikebukuro_down':'https://img.atwiki.jp/seibuinfo91/attach/22/162/%E8%A5%BF%E6%89%80%E6%B2%A22.mp3',
'desire_jonetsu':'https://img.atwiki.jp/seibuinfo91/attach/22/164/%E6%B8%85%E7%80%AC1.mp3',
'second_love':'https://img.atwiki.jp/seibuinfo91/attach/22/163/%E6%B8%85%E7%80%AC3.mp3',
'tonari_no_totoro_a':'https://img.atwiki.jp/seibuinfo91/attach/22/84/20251223_%E6%89%80%E6%B2%A2%234%202.mp3',
'tonari_no_totoro_b':'https://img.atwiki.jp/seibuinfo91/attach/22/85/20251223_%E6%89%80%E6%B2%A2%232%202.mp3',
'tonari_no_totoro_c':'https://img.atwiki.jp/seibuinfo91/attach/22/86/20251223_%E6%89%80%E6%B2%A2%235%202.mp3',
'hoero_lions_a':'https://img.atwiki.jp/seibuinfo91/attach/22/90/%E5%90%A0%E3%81%88%E3%82%8D%E3%83%A9%E3%82%A4%E3%82%AA%E3%83%B3%E3%82%BA.mp3',
'hoero_lions_c':'https://img.atwiki.jp/seibuinfo91/attach/22/94/20251223_%E8%A5%BF%E6%89%80%E6%B2%A2%232%281%29.mp3',
'wakaki_shishitachi':'https://img.atwiki.jp/seibuinfo91/attach/22/159/%E4%B8%8B%E5%B1%B1%E5%8F%A31.mp3',
'seibu_4000_one_man_door_chime':'https://hsm.uijin.com/soundsrc/DoorChime_seibu4000.wav',
'seibu_departure_buzzer':'https://hsm.uijin.com/soundsrc/StationSeibu.wav',
'station_type1_bell':'https://hsm.uijin.com/soundsrc/StationType1.wav',
'station_type2_bell':'https://hsm.uijin.com/soundsrc/StationType2.wav'}
manifest={}; headers={'User-Agent':'Mozilla/5.0'}
for key,url in TRACKS.items():
 suffix=Path(url.split('?')[0]).suffix or '.audio'; src=SRC/f'{key}{suffix}'; wav=WAV/f'{key}.wav'
 req=urllib.request.Request(url,headers=headers)
 with urllib.request.urlopen(req,timeout=90) as r, src.open('wb') as f: f.write(r.read())
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(src),'-ac','1','-ar','22050',str(wav)],check=True)
 manifest[key]={'url':url,'source':str(src),'wav':str(wav),'bytes':src.stat().st_size}
from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH
predict_and_save([str(WAV/f'{k}.wav') for k in TRACKS],str(MIDI),save_midi=True,sonify_midi=True,save_model_outputs=False,save_notes=True,model_or_model_path=ICASSP_2022_MODEL_PATH,onset_threshold=.45,frame_threshold=.25,minimum_note_length=70.,minimum_frequency=110.,maximum_frequency=4186.,multiple_pitch_bends=False,melodia_trick=True)
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'tracks':len(TRACKS),'midi':len(list(MIDI.glob('*.mid'))),'csv':len(list(MIDI.glob('*.csv')))},ensure_ascii=False,indent=2))
