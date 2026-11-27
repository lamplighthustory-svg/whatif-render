# Free voices on GitHub Actions with Supertonic 3 (open model, no key, no daily limit).
# usage:
#   py voice_go.py <episode> --demo                      -> one sample line in all 10 voices (F1-F5, M1-M5) to pick from
#   py voice_go.py <episode>                             -> every line of lines.py
#   py voice_go.py <episode> --speakers Dad,Jayden       -> only these characters
#   py voice_go.py <episode> --ids n01,n02               -> only these line ids
#   options: --voices Narrator=M2,Max=M3  (else cloud_cfg.json "free_voices", else M1)  --speed 1.05  --parts 10
# Output: Episodes\<ep>\voices_free\<id>.wav + manifest.csv (id, speaker, voice, seconds)
import argparse, csv, datetime, json, os, shutil, subprocess, sys, time, wave

HERE = os.path.dirname(os.path.abspath(__file__)); CH = os.path.abspath(os.path.join(HERE, '..'))
def tool(name, *fb):
    p = shutil.which(name)
    if p: return p
    for f in fb:
        if os.path.exists(f): return f
    sys.exit(f'{name} not found')
GIT = tool('git', r'C:\Program Files\Git\cmd\git.exe'); GH = tool('gh', r'C:\Program Files\GitHub CLI\gh.exe')
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def run(*c): subprocess.run(c, check=True)
def out(*c): return subprocess.run(c, check=True, capture_output=True, text=True).stdout.strip()

ap = argparse.ArgumentParser()
ap.add_argument('episode'); ap.add_argument('--demo', action='store_true'); ap.add_argument('--ids'); ap.add_argument('--speakers')
ap.add_argument('--voices'); ap.add_argument('--speed', type=float, default=1.05); ap.add_argument('--parts', type=int, default=10)
a = ap.parse_args()
EP = os.path.abspath(a.episode if os.path.exists(a.episode) else os.path.join(CH, 'Episodes', a.episode))
cfgp = os.path.join(EP, 'cloud_cfg.json'); cfg = json.load(open(cfgp, encoding='utf-8')) if os.path.exists(cfgp) else {}
vmap = dict(cfg.get('free_voices', {}))
if a.voices: vmap.update(dict(x.split('=', 1) for x in a.voices.split(',')))
sys.path.insert(0, EP); from lines import L  # (id, speaker, request, emotion, text)

if a.demo:
    txt = next(t for i, sp, r, e, t in L if sp == 'Narrator' and len(t) > 60)
    jobs = [{'id': f'demo_{v}', 'speaker': v, 'voice': v, 'text': txt, 'speed': a.speed} for v in ['F1', 'F2', 'F3', 'F4', 'F5', 'M1', 'M2', 'M3', 'M4', 'M5']]
else:
    ids = set(a.ids.split(',')) if a.ids else None; spk = set(a.speakers.split(',')) if a.speakers else None
    jobs = [{'id': i, 'speaker': sp, 'voice': vmap.get(sp, 'M1'), 'text': t, 'speed': a.speed}
            for i, sp, r, e, t in L if (ids is None or i in ids) and (spk is None or sp in spk)]
if not jobs: sys.exit('no lines selected')
parts = max(1, min(a.parts, len(jobs)))
J = os.path.join(HERE, 'voice_job'); os.makedirs(J, exist_ok=True)
json.dump(jobs, open(os.path.join(J, 'lines.json'), 'w', encoding='utf-8'), indent=0, ensure_ascii=False)
stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
json.dump({'episode': os.path.basename(EP), 'parts': parts, 'lines': len(jobs), 'stamp': stamp}, open(os.path.join(J, 'job.json'), 'w'), indent=1)
log(f'{len(jobs)} lines, {parts} parts, voices: {sorted(set(j["voice"] for j in jobs))}')

run(GIT, '-C', HERE, 'add', '-A'); run(GIT, '-C', HERE, 'commit', '-q', '-m', f'voice {os.path.basename(EP)} {len(jobs)} lines {stamp}')
sha = out(GIT, '-C', HERE, 'rev-parse', 'HEAD'); run(GIT, '-C', HERE, 'push', '-q')
repo = out(GIT, '-C', HERE, 'remote', 'get-url', 'origin').removesuffix('.git')
rid = None
for _ in range(60):
    m = [r for r in json.loads(out(GH, 'run', 'list', '-R', repo, '--workflow', 'voice.yml', '-L', '10', '--json', 'databaseId,headSha')) if r['headSha'] == sha]
    if m: rid = str(m[0]['databaseId']); break
    time.sleep(5)
if not rid: sys.exit('GitHub did not start the voice job')
log('making voices on GitHub:', f'{repo}/actions/runs/{rid}')
if subprocess.run([GH, 'run', 'watch', rid, '-R', repo, '--exit-status', '--interval', '20'], stdout=subprocess.DEVNULL).returncode:
    sys.exit(f'voice job FAILED - open {repo}/actions/runs/{rid}')
dst = os.path.join(EP, 'voices_free'); os.makedirs(dst, exist_ok=True)
run(GH, 'run', 'download', rid, '-R', repo, '-n', 'voices', '-D', dst)
rows = []
for j in jobs:
    p = os.path.join(dst, j['id'] + '.wav')
    if not os.path.exists(p): rows.append([j['id'], j['speaker'], j['voice'], 'MISSING']); continue
    with wave.open(p) as w: rows.append([j['id'], j['speaker'], j['voice'], round(w.getnframes() / w.getframerate(), 2)])
with open(os.path.join(dst, 'manifest.csv'), 'w', newline='', encoding='utf-8') as f:
    csv.writer(f).writerows([['id', 'speaker', 'voice', 'seconds']] + rows)
miss = [r[0] for r in rows if r[3] == 'MISSING']
log(f'DONE {len(rows) - len(miss)}/{len(rows)} lines ->', dst, ('MISSING: ' + ','.join(miss)) if miss else '')
