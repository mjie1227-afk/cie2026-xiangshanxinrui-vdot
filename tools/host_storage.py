"""Check the host drive backing Docker, not the virtual free space inside a container."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

GIB = 1024 ** 3


def docker_storage_path():
    override = os.environ.get('VDOT_DOCKER_STORAGE_PATH')
    if override: return Path(override).expanduser().resolve()
    if sys.platform == 'win32':
        settings_path = Path(os.environ['APPDATA']) / 'Docker/settings-store.json'
        settings = json.loads(settings_path.read_text(encoding='utf8')) if settings_path.exists() else {}
        location = settings.get('CustomWslDistroDir')
        return Path(location) if location else Path(os.environ['LOCALAPPDATA']) / 'Docker/wsl'
    result = subprocess.check_output(['docker', 'info', '--format', '{{.DockerRootDir}}'], text=True).strip()
    if not result: raise ValueError('Cannot determine Docker storage path.')
    return Path(result)


def check_storage(project, *, starting=False, heavy=False):
    storage = docker_storage_path()
    if not storage.exists():
        raise ValueError('Docker storage path is not locally accessible: ' + str(storage)
                         + '; set VDOT_DOCKER_STORAGE_PATH to the actual local storage directory.')
    checks = [('docker-storage', storage, 50 if starting and heavy else 10),
              ('project-files', Path(project), 3)]
    if sys.platform == 'win32':
        checks.append(('windows-system-drive', Path(os.environ.get('SystemDrive', 'C:') + '/'),
                       12 if starting else 10))
    result = []
    for name, path, minimum in checks:
        free = shutil.disk_usage(path).free
        result.append(dict(name=name, path=str(path), free_bytes=free, minimum_bytes=minimum * GIB))
        if free < minimum * GIB:
            raise OSError('LOW_HOST_DISK_SPACE: %s at %s has %.2f GiB free; need %.0f GiB. '
                          'Build stopped; no data was deleted.' % (name, path, free / GIB, minimum))
    return result


if __name__ == '__main__':
    try:
        print(json.dumps(check_storage(Path(__file__).resolve().parents[1], starting=True, heavy=True), indent=2))
        print('HOST_STORAGE_OK')
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
