"""Docker reproduction on Windows or Linux, using an isolated Linux work volume."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
sys.dont_write_bytecode = True
from host_storage import check_storage

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'work/container-session.json'
IMAGE = 'cie-vdot-env:20261103'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def delivery_rels():
    manifest = ROOT / 'MANIFEST.sha256'
    if manifest.is_file():
        files = [line.split('  ', 1)[1] for line in manifest.read_text(encoding='utf8').splitlines()]
        return files + ['MANIFEST.sha256']
    from verify_bundle import bundle_files
    return [p.relative_to(ROOT).as_posix() for p in bundle_files()]


def source_fingerprint():
    manifest = ROOT / 'MANIFEST.sha256'
    if manifest.is_file():
        return digest(manifest)
    h = hashlib.sha256()
    for rel in delivery_rels():
        h.update(rel.encode('utf-8'))
        h.update(digest(ROOT / rel).encode('ascii'))
        h.update(b'\n')
    return h.hexdigest()


def image_info(image):
    p = subprocess.run(['docker', 'image', 'inspect', image], capture_output=True, text=True, check=True)
    info = json.loads(p.stdout)[0]
    if (info['Os'], info['Architecture']) != ('linux', 'amd64'):
        raise ValueError('Expected a linux/amd64 image.')
    return info


def run(argv, folder, name):
    record = dict(argv=list(map(str, argv)), cwd=str(ROOT),
                  started_at=datetime.datetime.now().astimezone().isoformat())
    log = folder / (name + '.log')
    with log.open('w', encoding='utf8') as out:
        p = subprocess.Popen(record['argv'], cwd=ROOT, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding='utf8', errors='replace')
        lines = queue.Queue()
        def reader():
            try:
                for line in p.stdout: lines.put(line)
            finally: lines.put(None)
        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        try:
            ended = False
            checked = time.monotonic()
            while not ended:
                try:
                    line = lines.get(timeout=1)
                    if line is None: ended = True
                    else:
                        out.write(line); out.flush()
                        print(line, end='', flush=True)
                except queue.Empty: pass
                if time.monotonic() - checked >= 5:
                    check_storage(ROOT)
                    checked = time.monotonic()
            code = p.wait()
        except (KeyboardInterrupt, OSError) as error:
            if '--name' in record['argv']:
                container = record['argv'][record['argv'].index('--name') + 1]
                try:
                    subprocess.run(['docker', 'stop', '--timeout', '3', container], stdout=subprocess.DEVNULL, timeout=15)
                except (OSError, subprocess.TimeoutExpired) as stop_error:
                    record['stop_error'] = str(stop_error)
            p.terminate()
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill(); p.wait()
            code = 130 if isinstance(error, KeyboardInterrupt) else 75
            record['stopped_reason'] = str(error) or 'Interrupted by user'
            out.write('\n' + record['stopped_reason'] + '\n')
            print(record['stopped_reason'], flush=True)
    record.update(exit_code=code, finished_at=datetime.datetime.now().astimezone().isoformat())
    (folder / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
    (folder / (name + '.exit')).write_text(str(code) + '\n')
    if code:
        print('CONTAINER_EXIT_CODE=' + str(code))
        raise SystemExit(code)


def base_command(state):
    return ['docker', 'run', '--rm', '--platform', 'linux/amd64',
            '--mount', 'type=volume,source=' + state['volume'] + ',target=/validation',
            '--mount', 'type=volume,source=' + state['cache_volume'] + ',target=/cache',
            '-e', 'HOME=/cache/home', '-e', 'VDOT_JOBS=' + os.environ.get('VDOT_JOBS', '2'),
            '-e', 'VDOT_APP_JOBS=' + os.environ.get('VDOT_APP_JOBS', '2'),
            '-w', state['container_root']]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage', choices=['image', 'init', 'check', 'build', 'smoke', 'functional',
                                      'performance', 'collect', 'status', 'log', 'exec'])
    ap.add_argument('command', nargs=argparse.REMAINDER, help='Command following exec')
    args = ap.parse_args()
    subprocess.run(['docker', 'info'], check=True, stdout=subprocess.DEVNULL)
    if args.stage in ['status', 'log']:
        if not STATE.is_file(): raise ValueError('No session. Run init first.')
        state = json.loads(STATE.read_text(encoding='utf8'))
        if args.stage == 'status':
            print(json.dumps(state, indent=2)); return 0
        latest = state.get('last_log_dir')
        if not latest: raise ValueError('No stage logs yet.')
        host_log = Path(latest) / 'stage.log'
        if not host_log.exists(): raise ValueError('Stage log not created yet.')
        text = host_log.read_text(encoding='utf8')
        build_dirs = [line.split('=', 1)[1] for line in text.splitlines() if line.startswith('BUILD_LOG=')]
        if build_dirs:
            target = build_dirs[-1]
            if not target.startswith(state['container_root'] + '/work/build/build-logs/'):
                raise ValueError('Unexpected build log location.')
            return subprocess.call(base_command(state) + [state['image'], 'tail', '-n', '45', target + '/build.log'])
        print('\n'.join(text.splitlines()[-45:])); return 0
    logs = ROOT / 'work/container-logs'
    logs.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=args.stage + '-', dir=logs))
    print('CONTAINER_LOG=' + str(folder), flush=True)
    image = os.environ.get('VDOT_CONTAINER_IMAGE', IMAGE)
    if args.stage not in ['collect']:
        storage = check_storage(ROOT, starting=True, heavy=args.stage in ['image', 'build', 'exec'])
        (folder / 'host-storage.json').write_text(json.dumps(storage, indent=2) + '\n')
        for item in storage:
            print('HOST_DISK %s: %.2f GiB free (%s)' % (item['name'], item['free_bytes'] / 2**30, item['path']), flush=True)
    if args.stage == 'image':
        run(['docker', 'build', '--platform', 'linux/amd64', '-t', image,
             '-f', 'environment/Dockerfile', 'environment'], folder, 'image-build')
        (folder / 'image.json').write_text(json.dumps(image_info(image), indent=2) + '\n')
    elif args.stage == 'init':
        if STATE.exists(): raise ValueError('Session already exists; use check/build, or use a new repository copy.')
        info = image_info(image)
        run([sys.executable, 'tools/verify_bundle.py'], folder, 'bundle-check')
        token = uuid.uuid4().hex[:12]
        state = dict(image=image, image_id=info['Id'], volume='cie-vdot-' + token,
                     cache_volume='cie-vdot-' + token + '-cache',
                     container_root='/validation/' + ROOT.name,
                     source_manifest_sha256=source_fingerprint(), ready=False)
        STATE.write_text(json.dumps(state, indent=2) + '\n', encoding='utf8')
        for key in ['volume', 'cache_volume']: run(['docker', 'volume', 'create', state[key]], folder, key)
        archive = folder / 'repository.zip'
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=1) as z:
            files = delivery_rels()
            for rel in files:
                source = (ROOT / rel).resolve()
                if not source.is_relative_to(ROOT): raise ValueError('Unsafe manifest path: ' + rel)
                z.write(source, ROOT.name + '/' + rel)
        # Extract on Linux; avoids slow per-file reads through a Windows bind mount.
        cmd = ['docker', 'run', '--rm', '--mount', 'type=volume,source=' + state['volume'] + ',target=/validation',
               '--mount', 'type=bind,source=' + str(folder) + ',target=/input,readonly', image,
               'python3', '-m', 'zipfile', '-e', '/input/repository.zip', '/validation']
        run(cmd, folder, 'extract')
        run(base_command(state) + [image, 'python3', 'tools/verify_bundle.py'], folder, 'copied-bundle-check')
        state.update(ready=True, last_log_dir=str(folder))
        STATE.write_text(json.dumps(state, indent=2) + '\n', encoding='utf8')
        print('CONTAINER_INIT_OK')
    else:
        if not STATE.exists(): raise ValueError('Run init first.')
        state = json.loads(STATE.read_text(encoding='utf8'))
        if not state.get('ready'): raise ValueError('Initialization incomplete; preserve logs and inspect before retrying.')
        if args.stage not in ['collect']:
            if source_fingerprint() != state['source_manifest_sha256']:
                raise ValueError('Repository manifest changed since init. Keep this session for logs; use a fresh repository copy for new source.')
            if image_info(state['image'])['Id'] != state['image_id']:
                raise ValueError('Image tag changed since init; original session is preserved.')
        cmd = base_command(state)
        if args.stage == 'collect':
            result = ROOT / 'work/container-results' / folder.name
            result.mkdir(parents=True)
            guest = "from pathlib import Path;import tarfile;p=Path('.');names=[n for n in ['runs','work/environment-checks','work/build/build-logs'] if (p/n).exists()];t=tarfile.open('/export/results.tar.gz','w:gz');[t.add(n) for n in names];t.close();print('RESULTS_EXPORTED')"
            run(cmd + ['--mount', 'type=bind,source=' + str(result) + ',target=/export', state['image'],
                       'python3', '-c', guest], folder, 'collect')
            print('RESULTS_ARCHIVE=' + str(result / 'results.tar.gz'))
        else:
            name = 'cie-vdot-run-' + uuid.uuid4().hex[:12]
            state.update(last_log_dir=str(folder), last_container=name, last_stage=args.stage)
            STATE.write_text(json.dumps(state, indent=2) + '\n', encoding='utf8')
            if args.stage == 'exec':
                if not args.command: raise ValueError('Specify a command after exec.')
                guest = args.command
            else:
                guest = ['bash', 'tools/reproduce.sh', args.stage]
            run(cmd + ['--name', name, state['image']] + guest, folder, 'stage')
    print('CONTAINER_EXIT_CODE=0')
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print('CONTAINER_ERROR: ' + str(error), file=sys.stderr)
        raise SystemExit(2)

