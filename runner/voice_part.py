# Runs on a GitHub Actions machine: makes the voice lines of part K of N with Supertonic 3 (free, open model).
# usage: python runner/voice_part.py <k> <n> <outdir>
import json, os, pathlib, re, sys, time
from supertonic import TTS

ROOT = pathlib.Path(__file__).resolve().parent.parent
lines = json.load(open(ROOT / 'voice_job' / 'lines.json', encoding='utf-8'))
k, n, out = int(sys.argv[1]), int(sys.argv[2]), pathlib.Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
mine = lines[len(lines) * k // n: len(lines) * (k + 1) // n]
print(f'part {k}/{n}: {len(mine)} lines', flush=True)
tts = TTS(model_dir=os.path.expanduser('~/supertonic3'), auto_download=True)
styles = {}
st = time.time()
for ln in mine:
    v = ln['voice']; styles.setdefault(v, tts.get_voice_style(v))
    text = re.sub(r'\[[^\]]*\]', ' ', ln['text']); text = re.sub(r'\s+', ' ', text).strip()  # drop Gemini-style [notes]
    wav, dur = tts.synthesize(text, voice_style=styles[v], lang=ln.get('lang', 'en'),
                              speed=float(ln.get('speed', 1.05)), total_steps=int(ln.get('steps', 8)))
    tts.save_audio(wav, str(out / f"{ln['id']}.wav"))
    print(f"  {ln['id']} {v} {float(dur[0]) if hasattr(dur, '__len__') else float(dur):.2f}s", flush=True)
print(f'done in {time.time() - st:.0f}s', flush=True)
