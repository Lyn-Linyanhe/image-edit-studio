"""Inherited subprocess isolation for local image tests, not core API mocks."""
from __future__ import annotations
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BOOTSTRAP = r'''
import ipaddress, os, pathlib, shlex, socket, sys
sys.dont_write_bytecode = True
GOAL_GUARD_ACTIVE = True

def is_loopback(host):
    try:
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False

def audit(event, args):
    if event.startswith('winreg.'):
        raise PermissionError('goal_gate: registry credential reads forbidden')
    if event in ('socket.connect', 'socket.bind'):
        if os.environ.get('GOAL_ALLOW_LOOPBACK') != '1' or not is_loopback(args[1][0]):
            raise PermissionError('goal_gate: network forbidden')
    if event in ('socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyaddr'):
        if os.environ.get('GOAL_ALLOW_LOOPBACK') != '1' or not is_loopback(args[0]):
            raise PermissionError('goal_gate: external DNS forbidden')
    if event == 'socket.sendto':
        raise PermissionError('goal_gate: datagrams forbidden')
    if event in ('os.system', 'os.exec', 'os.posix_spawn'):
        raise PermissionError('goal_gate: native process bypass forbidden')
    if event in ('os.remove', 'os.rmdir', 'os.mkdir', 'os.rename'):
        paths = args[:2] if event == 'os.rename' else args[:1]
        for value in paths:
            if not pathlib.Path(value).resolve().is_relative_to(pathlib.Path(os.environ['GOAL_TEMP_ROOT']).resolve()):
                raise PermissionError('goal_gate: mutation outside isolated temp forbidden')
    if event == 'subprocess.Popen':
        argv = args[1]
        if isinstance(argv, str):
            argv = [x.strip('"') for x in shlex.split(argv, posix=False)]
        executable = args[0] or argv[0]
        if pathlib.Path(executable).resolve() != pathlib.Path(sys.executable).resolve():
            raise PermissionError('goal_gate: non-Python child forbidden')
        if any(x in argv for x in ('-I', '-S', '-E')) or any(pathlib.Path(str(x)).name.lower() == 'fetch_url.py' for x in argv):
            raise PermissionError('goal_gate: unguarded/fetch child forbidden')
        env = args[3] or os.environ
        for name in ('PYTHONPATH', 'GOAL_TEMP_ROOT', 'GOAL_ALLOW_LOOPBACK', 'PYTHONDONTWRITEBYTECODE'):
            if env.get(name) != os.environ.get(name):
                raise PermissionError('goal_gate: child isolation environment changed')
    if event == 'open':
        value, mode, flags = args
        if isinstance(value, (str, bytes, os.PathLike)):
            p = pathlib.Path(os.fsdecode(value)).resolve()
            name = p.name.lower()
            if (name.startswith('.env') or name.endswith(('.pem', '.key', '.pfx', '.p12')) or
                name in ('auth.json', 'credentials.json', 'secrets.json', 'probe_keys_result.json')):
                raise PermissionError('goal_gate: credential file reads forbidden')
            writing = (isinstance(mode, str) and any(x in mode for x in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            if writing and not p.is_relative_to(pathlib.Path(os.environ['GOAL_TEMP_ROOT']).resolve()):
                if p != pathlib.Path(os.devnull).resolve():
                    raise PermissionError('goal_gate: writes outside isolated temp forbidden')
sys.addaudithook(audit)
'''


def run_isolated(test: Path, root: Path, loopback: bool) -> bool:
    with tempfile.TemporaryDirectory(prefix='zimage-goal-gate-') as temporary:
        temp = Path(temporary)
        (temp / 'sitecustomize.py').write_text(BOOTSTRAP, encoding='utf-8')
        # Read only named OS plumbing variables; never copy credential values.
        env = {n: os.environ[n] for n in ('SystemRoot', 'WINDIR', 'PATH', 'COMSPEC') if n in os.environ}
        env.update({'PYTHONPATH': temporary, 'PYTHONDONTWRITEBYTECODE': '1',
                    'USERPROFILE': temporary, 'HOME': temporary,
                    'PYTHONIOENCODING': 'utf-8', 'TMP': temporary, 'TEMP': temporary,
                    'GOAL_TEMP_ROOT': temporary, 'GOAL_ALLOW_LOOPBACK': '1' if loopback else '0',
                    'RELAY_API_KEY': 'goal-test-dummy-not-a-real-credential',
                    'RELAY_API_KEY_HD': 'goal-test-dummy-not-a-real-credential',
                    'RELAY_BASE_URL': 'https://image-direct.geiliapi.com/v1', 'RELAY_MODEL': 'gpt-image-2',
                    'ZIMAGE_JOBS_DIR': str(temp / 'jobs'), 'ZIMAGE_CACHE_DIR': str(temp / 'cache')})
        proof = "import socket,sitecustomize; print('GUARD_ACTIVE',sitecustomize.GOAL_GUARD_ACTIVE); socket.getaddrinfo('goal-gate.invalid',443)"
        result = subprocess.run([sys.executable, '-B', '-c', proof], env=env, cwd=temp, capture_output=True, timeout=30)
        if result.returncode == 0 or b'GUARD_ACTIVE True' not in result.stdout or b'external DNS forbidden' not in result.stderr:
            print('ISOLATION FAIL: external DNS guard proof failed; tests not run')
            return False
        print(f'ISOLATION PASS: DNS denied before resolution; numeric loopback={loopback}; dummy credentials')
        command = [sys.executable, '-B', str(test)]
        print('TEST COMMAND:', subprocess.list2cmdline(command))
        try:
            result = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=600)
        except subprocess.TimeoutExpired:
            print('TEST FAIL: timeout; output withheld')
            return False
        print(result.stdout.decode('utf-8', 'replace'))
        print(result.stderr.decode('utf-8', 'replace'))
        print(f'TEST EXIT: {result.returncode}')
        return result.returncode == 0
