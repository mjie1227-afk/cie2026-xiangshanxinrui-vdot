"""Export the tested Docker toolchain image and transfer checksums; Windows/Linux."""
import argparse
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('destination', type=Path, help='New output directory outside the source repository')
    ap.add_argument('--image', default='cie-vdot-env:20261103')
    args = ap.parse_args()
    dest = args.destination.expanduser().resolve()
    root = Path(__file__).resolve().parents[1]
    if dest.exists() or dest.is_relative_to(root):
        ap.error('Choose a new directory outside this repository; existing files are preserved.')
    inspect = subprocess.run(['docker', 'image', 'inspect', args.image],
                             capture_output=True, text=True, check=True)
    data = json.loads(inspect.stdout)[0]
    if (data['Os'], data['Architecture']) != ('linux', 'amd64'):
        ap.error('This delivery expects linux/amd64.')
    dest.mkdir(parents=True)
    name = 'cie-vdot-env-20261103-linux-amd64.tar.gz'
    partial = dest / (name + '.partial')
    archive = dest / name
    argv = ['docker', 'image', 'save', args.image]
    record = dict(image=args.image, image_id=data['Id'], os=data['Os'], architecture=data['Architecture'],
                  argv=argv, started_at=datetime.datetime.now().astimezone().isoformat(),
                  scope='Toolchain image only; no source tree, Scala dependency cache, emu or test results.')
    print('EXPORT_DIRECTORY=' + str(dest), flush=True)
    print('IMAGE_ID=' + data['Id'], flush=True)
    with (dest / 'save.log').open('wb') as errors, gzip.open(partial, 'wb', compresslevel=1) as out:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=errors)
        try:
            for chunk in iter(lambda: process.stdout.read(4 * 1024 * 1024), b''):
                out.write(chunk)
        except BaseException:
            process.terminate()
            process.wait()
            raise
        finally:
            process.stdout.close()
        code = process.wait()
    (dest / 'save.exit').write_text(str(code) + '\n')
    if code:
        print('Export failed; partial file and save.log preserved.', file=sys.stderr)
        return code
    partial.rename(archive)
    digest = hashlib.sha256()
    with archive.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    record.update(archive=name, archive_bytes=archive.stat().st_size, sha256=digest.hexdigest(), exit_code=0,
                  finished_at=datetime.datetime.now().astimezone().isoformat())
    (dest / 'environment.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
    (dest / 'SHA256SUMS.txt').write_text(digest.hexdigest() + '  ' + name + '\n', encoding='utf8')
    print('ENVIRONMENT_EXPORT_OK ' + str(archive))
    print('SHA256=' + digest.hexdigest())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
