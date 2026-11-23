# Render an episode on GitHub Actions (free) instead of the slow laptop.
# usage:
#   py cloud_go.py <episode_folder>                  -> full video, muxed with mix_full.wav into Final Videos\
#   py cloud_go.py <episode_folder> --t0 0 --t1 30   -> test clip (episode\cloud_test.mp4)
#   options: --parts N (default 20), --res 720|1080 (default 1080)
# The episode folder needs cloud_cfg.json: {"shots": "shots_x", "extra": "...js,...js", "theme": {...}, "title": "...", "final_name": "....mp4"}
# Only page.html (drawing engine) + data.json (shots, lip-sync envelope) are uploaded. No voice/audio leaves the laptop.
import argparse, datetime, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.abspath(os.path.join(HERE, '..'))
ENGINE = os.path.join(CH, 'engine_v2')

def tool(name, *fallbacks):
    p = shutil.which(name)
    if p: return p
    for f in fallbacks:
        if os.path.exists(f): return f
    sys.exit(f'{name} not found - install it first')

def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def run(*cmd, **kw): return subprocess.run(cmd, check=True, **kw)
def out(*cmd): return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()

ap = argparse.ArgumentParser()
ap.add_argument('episode'); ap.add_argument('--t0', type=float); ap.add_argument('--t1', type=float)
ap.add_argument('--parts', type=int, default=20); ap.add_argument('--res', default='1080')
ap.add_argument('--prep-only', action='store_true')
a = ap.parse_args()
EP = os.path.abspath(a.episode if os.path.isabs(a.episode) or os.path.exists(a.episode) else os.path.join(CH, 'Episodes', a.episode))
cfg = json.load(open(os.path.join(EP, 'cloud_cfg.json'), encoding='utf-8'))

# 1. build page.html + data.json exactly like engine_v2/render.py does (without touching the engine folder)
os.environ.update(VB=os.path.join(EP, 'vb'), SHOTS=cfg['shots'], EXTRA=cfg['extra'], THEME=json.dumps(cfg['theme']), TITLE=cfg['title'], RES=a.res)
sys.path[:0] = [EP, ENGINE]
import render  # engine_v2/render.py
d = render.data()
eng = open(os.path.join(ENGINE, 'ifv.js'), encoding='utf-8').read()
if os.path.exists(os.path.join(ENGINE, 'ifv_ext.js')): eng += '\n' + open(os.path.join(ENGINE, 'ifv_ext.js'), encoding='utf-8').read()
for x in [e for e in cfg['extra'].split(',') if e]: eng += '\n' + open(os.path.join(ENGINE, x), encoding='utf-8').read()
RW, RH = (1280, 720) if a.res == '720' else (1920, 1080)
html = render.HTML.replace('ENGINE', eng).replace('RESW', str(RW)).replace('RESH', str(RH))
t0 = a.t0 if a.t0 is not None else 0.0
t1 = a.t1 if a.t1 is not None else d['total']
full = a.t0 is None and a.t1 is None
parts = max(1, min(a.parts, int((t1 - t0) * render.FPS // 24) or 1))  # at least ~1 s of frames per part
JOB = os.path.join(HERE, 'job'); os.makedirs(JOB, exist_ok=True)
open(os.path.join(JOB, 'page.html'), 'w', encoding='utf-8').write(html)
json.dump(d, open(os.path.join(JOB, 'data.json'), 'w', encoding='utf-8'), separators=(',', ':'))
stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
json.dump({'episode': os.path.basename(EP), 't0': t0, 't1': t1, 'parts': parts, 'res': a.res, 'stamp': stamp},
          open(os.path.join(JOB, 'job.json'), 'w', encoding='utf-8'), indent=1)
log(f'job ready: {os.path.basename(EP)} {t0:.2f}-{t1:.2f}s, {parts} parts, {a.res}p')
if a.prep_only: sys.exit(0)

# 2. push -> GitHub starts the render
GIT = tool('git', r'C:\Program Files\Git\cmd\git.exe')
GH = tool('gh', r'C:\Program Files\GitHub CLI\gh.exe')
run(GIT, '-C', HERE, 'add', '-A')
run(GIT, '-C', HERE, 'commit', '-q', '-m', f'render {os.path.basename(EP)} {t0:.0f}-{t1:.0f} {stamp}')
sha = out(GIT, '-C', HERE, 'rev-parse', 'HEAD')
run(GIT, '-C', HERE, 'push', '-q')
log('pushed, waiting for GitHub to start...')
rid = None
for _ in range(60):
    runs = json.loads(out(GH, 'run', 'list', '-R', out(GIT, '-C', HERE, 'remote', 'get-url', 'origin'), '--workflow', 'render.yml', '-L', '10', '--json', 'databaseId,headSha'))
    m = [r for r in runs if r['headSha'] == sha]
    if m: rid = str(m[0]['databaseId']); break
    time.sleep(5)
if not rid: sys.exit('GitHub did not start the render - check the Actions tab of the repo')
url = out(GIT, '-C', HERE, 'remote', 'get-url', 'origin').removesuffix('.git') + f'/actions/runs/{rid}'
log('rendering on GitHub:', url)
st = time.time()
w = subprocess.run([GH, 'run', 'watch', rid, '-R', url.split('/actions')[0], '--exit-status', '--interval', '30'], cwd=HERE, stdout=subprocess.DEVNULL)
if w.returncode: sys.exit(f'render FAILED - open {url} to see why')
log(f'render done in {(time.time() - st) / 60:.1f} min, downloading...')

# 3. download + add the audio
dl = os.path.join(EP, 'parts', 'cloud_' + stamp); os.makedirs(dl, exist_ok=True)
run(GH, 'run', 'download', rid, '-R', url.split('/actions')[0], '-n', 'video_only', '-D', dl)
vid = os.path.join(dl, 'video_only.mp4')
mix = os.path.join(EP, 'mix_full.wav')
if full:
    dst = os.path.join(CH, 'Final Videos'); os.makedirs(dst, exist_ok=True); dst = os.path.join(dst, cfg['final_name'])
    run('ffmpeg', '-v', 'error', '-y', '-i', vid, '-i', mix, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
        '-af', 'volume=-0.6dB,alimiter=limit=0.75:level=disabled', '-c:a', 'aac', '-b:a', '192k', '-shortest', dst)
else:
    dst = os.path.join(EP, 'cloud_test.mp4')
    if os.path.exists(mix):
        run('ffmpeg', '-v', 'error', '-y', '-i', vid, '-ss', str(t0), '-t', str(t1 - t0), '-i', mix, '-map', '0:v', '-map', '1:a',
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', dst)
    else: shutil.copy(vid, dst)
log('FINAL', dst)
