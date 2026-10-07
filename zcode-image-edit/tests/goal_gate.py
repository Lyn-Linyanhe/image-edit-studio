"""Fail-closed local preparation gate; no six-batch completion claim."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / '.zimage/goal-baseline.json'
FILES = ROOT / '.zimage/goal-baseline-files.json'
DIFF = ROOT / '.zimage/goal-baseline.diff'
GLOBAL = Path.home() / '.zcode/workflows/image-job.dwf.ts'
ROUND = 'style-distill/round_lib/run_round.py'
ALLOWLIST = tuple('''zcode-image-edit/bin/zimage.py
zcode-image-edit/reliability.py
zcode-image-edit/tests/test_reliability.py
zcode-image-edit/README.md
zcode-image-edit/_skill/image-edit/SKILL.md
zcode-image-edit/commands/image-edit.md
zcode-image-edit/commands/paint-mask.md
zcode-image-edit/commands/image-gallery.md
style-distill/_skill/style-distill/SKILL.md
style-distill/_skill/style-distill/LESSONS.md
style-distill/_skill/style-distill/references/negative-library.md
style-distill/_skill/style-distill/references/identity-library.md
style-distill/_skill/style-distill/references/pipeline-notes.md
AGENTS.md
style-distill/round_lib/run_round.py
zcode-image-edit/plan_store.py
zcode-image-edit/preflight.py
zcode-image-edit/payload.py
zcode-image-edit/executor.py
zcode-image-edit/request_lock.py
zcode-image-edit/transport.py
zcode-image-edit/task_contract.py
zcode-image-edit/review.py
zcode-image-edit/lessons.py
zcode-image-edit/tests/goal_gate.py
zcode-image-edit/tests/test_goal_transactions.py
zcode-image-edit/tests/test_goal_preflight.py
zcode-image-edit/tests/test_goal_execution.py
zcode-image-edit/tests/test_goal_concurrency.py
zcode-image-edit/tests/test_goal_review.py
zcode-image-edit/tests/test_goal_roles.py
zcode-image-edit/tests/test_goal_lessons.py
zcode-image-edit/tests/no_network.py
zcode-image-edit/tests/live_mask_once.py
zcode-image-edit/references/agent-roles/image-planner.md
zcode-image-edit/references/agent-roles/image-reviewer.md
zcode-image-edit/references/agent-roles/image-lesson-curator.md
.zcode/agents/image-planner.md
.zcode/agents/image-reviewer.md
.zcode/agents/image-lesson-curator.md
zcode-image-edit/workflows/image-review.dwf.ts
zcode-image-edit/evidence/goal-local-report.md
zcode-image-edit/evidence/goal-checklist.json
zcode-image-edit/evidence/goal-gate-results.json
.zimage/goal-baseline.json
.zimage/goal-baseline.diff
.zimage/goal-baseline-files.json'''.splitlines())
BATCH_TESTS = {1: ('test_reliability.py', 'test_goal_transactions.py'),
               2: ('test_goal_preflight.py',),
               3: ('test_goal_execution.py', 'test_goal_concurrency.py'),
               4: ('test_goal_review.py',),
               5: ('test_goal_roles.py', 'test_goal_lessons.py')}
EXTRA = ('compose/images/gen.py', 'compose/images/mask_edit_app.py',
         'style-distill/round_lib/local_ops.py', 'zcode-image-edit/mask_gen.py')


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True).stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record(path):
    stat = path.lstat()
    name = path.name.lower()
    # Do not read likely credential stores, including existing probe results.
    secret = (name.startswith('.env') or name.endswith(('.pem', '.key', '.pfx', '.p12')) or
              name in ('credentials.json', 'auth.json', 'secrets.json', 'probe_keys_result.json') or
              any(x.lower() in ('credentials', 'secrets') for x in path.parts))
    if secret:
        return {'unread': True, 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
    if path.is_symlink():
        return {'symlink': os.readlink(path)}
    with path.open('rb') as stream:
        return {'sha256': hashlib.file_digest(stream, 'sha256').hexdigest(), 'size': stat.st_size}


def inventory():
    names = set()
    for args in (('ls-files', '-z'), ('ls-files', '--others', '--exclude-standard', '-z')):
        names.update(os.fsdecode(x).replace('\\', '/') for x in git(*args).split(b'\0') if x)
    # Ignored jobs/cache/ledger are not exempt from preservation checks.
    for directory in ('.zimage', '.agent-teams', 'dsh-probe', 'plugins', 'style-distill/round_pool'):
        parent = ROOT / directory
        if parent.exists():
            names.update(p.relative_to(ROOT).as_posix() for p in parent.rglob('*') if p.is_file())
    return {name: record(ROOT / name) if (ROOT / name).is_file() else {'missing': True}
            for name in sorted(names)}


def workflow_audit():
    if not GLOBAL.is_file():
        print('WORKFLOW UNVERIFIED: definition absent')
        return False
    lines = GLOBAL.read_text(encoding='utf-8').splitlines()
    ok = True
    for label, needles in (
        ('bypasses zimage; direct run_round/fetch_url', ('const RUN_ROUND =', 'const FETCH =', 'const genArgs =', 'const genArgs2 =', '[FETCH, "--pending"]')),
        ('fast defaults true and skips semantic review', ('const fast = args.fast !== false', 'verdict = "pass（fast）"', '未做目检核查')),
        ('parallel variants opt-in; variants default=1', ('Promise.all(', '全部并行生成')),
        ('subagent mutates lesson library', ('把本轮实际出现的失败形态追加进负向词库',))):
        matches = [i for i, line in enumerate(lines, 1) if any(n in line for n in needles)]
        for line in matches:
            print(f'WORKFLOW FINDING {GLOBAL}:{line}: {label}')
            ok = False
    print(json.dumps({'legacy_workflow_risk': not ok, 'invoked': False,
                      'discovery_permissions': 'unverified'}))
    # The global definition is outside repair scope; reject new local references.
    for name in ALLOWLIST:
        path = ROOT / name
        if path.suffix in ('.md', '.ts') and path.is_file():
            if 'image-job.dwf.ts' in path.read_text(encoding='utf-8'):
                print(f'WORKFLOW FAIL: scope-local legacy reference: {name}')
                return False
    return True


def initialize():
    if BASE.exists() or DIFF.exists():
        raise RuntimeError('refuse to overwrite baseline')
    data = inventory()
    dirty = git('status', '--porcelain=v1', '-z', '--untracked-files=all')
    for path in ALLOWLIST:
        if path in (ROUND, 'zcode-image-edit/tests/goal_gate.py', 'zcode-image-edit/tests/no_network.py', '.zimage/goal-baseline-files.json'):
            continue
        if os.fsencode(path) + b'\0' in dirty:
            raise RuntimeError(f'pre-existing allowlist conflict: {path}')
    original = (ROOT / ROUND).read_bytes()
    external_diff = git('diff', '--binary', 'HEAD', '--', ROUND)
    if FILES.exists() and FILES.read_bytes().strip() != b'{}':
        raise RuntimeError('refuse to overwrite baseline bytes')
    FILES.write_text(json.dumps({ROUND: {'bytes_b64': base64.b64encode(original).decode(),
                                        'sha256': digest(original)}}, indent=2) + '\n', encoding='utf-8')
    DIFF.write_bytes(external_diff)
    data.pop('.zimage/goal-baseline-files.json', None)
    baseline = {'schema': 'zimage-goal-baseline-v1', 'head': git('rev-parse', 'HEAD').decode().strip(),
                'allowlist': list(ALLOWLIST), 'inventory': data,
                'initial_git_status': os.fsdecode(dirty).split('\0'),
                'external_tracked_paths': [ROUND, 'style-distill/round_lib/pending_urls.json'],
                'external_diff_sha256': digest(external_diff), 'files_sha256': digest(FILES.read_bytes()),
                'global_workflow': record(GLOBAL) if GLOBAL.is_file() else None,
                'scope': 'preparation only; no batch completion claim'}
    BASE.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'BASELINE CREATED: HEAD={baseline["head"]}; {len(data)} file records')
    print('CREDENTIAL CANDIDATES NOT READ:', sum(bool(v.get('unread')) for v in data.values()))


def audit_baseline():
    if not BASE.is_file():
        print('BASELINE FAIL: missing baseline')
        return False
    data = json.loads(BASE.read_text(encoding='utf-8'))
    ok = data['head'] == git('rev-parse', 'HEAD').decode().strip() and tuple(data['allowlist']) == ALLOWLIST
    after = inventory()
    initial_staged = [x for x in data['initial_git_status'] if x and x[0] not in (' ', '?')]
    current_status = os.fsdecode(git('status', '--porcelain=v1', '-z', '--untracked-files=all')).split('\0')
    current_staged = [x for x in current_status if x and x[0] not in (' ', '?')]
    if initial_staged != current_staged or git('diff', '--cached', '--binary'):
        print('BASELINE FAIL: index changed or staged content requires review')
        ok = False
    for name in sorted(set(data['inventory']) | set(after)):
        if name not in ALLOWLIST and data['inventory'].get(name) != after.get(name):
            print(f'BASELINE FAIL outside allowlist: {name}')
            ok = False
    if digest(DIFF.read_bytes()) != data['external_diff_sha256'] or digest(FILES.read_bytes()) != data['files_sha256']:
        print('BASELINE FAIL: external evidence changed')
        ok = False
    saved = json.loads(FILES.read_text(encoding='utf-8'))[ROUND]
    original = base64.b64decode(saved['bytes_b64'], validate=True)
    if digest(original) != saved['sha256']:
        ok = False
    current = (ROOT / ROUND).read_bytes()
    if original != current:
        check = subprocess.run(['git', 'apply', '--reverse', '--check', '--unidiff-zero', str(DIFF)], cwd=ROOT, capture_output=True)
        if check.returncode:
            print('BASELINE FAIL: original external run_round hunks no longer reversible; review required')
            ok = False
        print(f'ROUND original={digest(original)} current={digest(current)}; original external diff preserved separately')
    if (record(GLOBAL) if GLOBAL.is_file() else None) != data['global_workflow']:
        print('BASELINE FAIL: global read-only workflow changed')
        ok = False
    for name, value in data['inventory'].items():
        if value.get('unread'):
            print(json.dumps({'path': name, 'content_integrity': 'unverified_credentials_exclusion',
                              'metadata_equal': after.get(name) == value}))
            if name != 'style-distill/round_pool/probe_keys_result.json':
                print('BASELINE FAIL: unapproved credential exclusion')
                ok = False
    print(f'BASELINE {"PASS" if ok else "FAIL"}: no dirty-worktree exemption')
    return ok


def compile_targets():
    count = 0
    ok = True
    for name in sorted(set(ALLOWLIST) | set(EXTRA)):
        path = ROOT / name
        if path.suffix == '.py' and path.is_file():
            try:
                compile(path.read_bytes(), str(path), 'exec')
                count += 1
            except (SyntaxError, ValueError):
                print('COMPILE FAIL:', name)
                ok = False
    print(f'COMPILE {"PASS" if ok else "FAIL"}: {count} targets; compile builtin; no pycache')
    return ok


def run_tests(batch, loopback):
    from no_network import run_isolated
    ok = True
    for name in BATCH_TESTS[batch]:
        path = ROOT / 'zcode-image-edit/tests' / name
        if not path.is_file():
            print(f'BATCH {batch} NOT_IMPLEMENTED: {name}')
            ok = False
        else:
            ok = run_isolated(path, ROOT, loopback) and ok
    return ok


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--batch', type=int, choices=range(1, 6))
    modes.add_argument('--full', action='store_true')
    modes.add_argument('--init-baseline', action='store_true')
    parser.add_argument('--audit', action='store_true')
    parser.add_argument('--allow-loopback', action='store_true')
    args = parser.parse_args()
    if not (args.batch or args.full or args.audit or args.init_baseline):
        parser.error('one of --batch, --full, --audit, --init-baseline is required')
    if args.init_baseline:
        initialize()
        return 0
    compiled, before = compile_targets(), audit_baseline()
    workflow_ok = workflow_audit() if args.audit or args.full else True
    tests_ok = True
    if args.batch or args.full:
        for batch in range(1, 6) if args.full else (args.batch,):
            tests_ok = run_tests(batch, args.allow_loopback) and tests_ok
    after = audit_baseline()
    ok = compiled and before and after and workflow_ok and tests_ok
    print(f'GOAL_GATE {"PASS" if ok else "FAIL"}; preparation only, not six-batch completion')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
