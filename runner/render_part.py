# Runs on a GitHub Actions machine: renders part K of N of the job in job/ to an mp4.
# usage: python runner/render_part.py <k> <n> <out.mp4>
import json, math, os, pathlib, subprocess, sys, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
job = json.load(open(ROOT / 'job' / 'job.json', encoding='utf-8'))
data = json.load(open(ROOT / 'job' / 'data.json', encoding='utf-8'))
k, n, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
fps = data['fps']
t0, t1 = float(job['t0']), float(job['t1'])

# same frame list as engine_v2/render.py: f = round(t0*fps) while f/fps < t1
f = int(round(t0 * fps)); frames = []
while f / fps < t1: frames.append(f); f += 1
a, b = len(frames) * k // n, len(frames) * (k + 1) // n
mine = frames[a:b]
print(f'part {k}/{n}: {len(mine)} frames ({a}..{b})', flush=True)

W, H = (1280, 720) if str(job.get('res')) == '720' else (1920, 1080)
ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'image2pipe', '-c:v', 'mjpeg', '-r', str(fps), '-i', '-',
                       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
st = time.time()
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={'width': W, 'height': H})
    pg.goto((ROOT / 'job' / 'page.html').as_uri()); pg.evaluate('d => { DATA = d; }', data)
    for i, fr in enumerate(mine):
        pg.evaluate(f'render({fr / fps})'); ff.stdin.write(pg.screenshot(type='jpeg', quality=92))
        if i % 200 == 0: print(f'  {i}/{len(mine)}  {time.time() - st:.0f}s', flush=True)
    br.close()
ff.stdin.close(); ff.wait()
if ff.returncode: sys.exit(ff.returncode)
print(f'done {out} in {time.time() - st:.0f}s', flush=True)
