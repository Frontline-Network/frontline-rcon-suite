import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import discover_backend_readiness as discovery
from scripts.backend_health_override import HEALTHCHECK


@pytest.fixture
def deployment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = tmp_path / 'compose.yaml'
    second = tmp_path / 'overlay.json'
    first.touch()
    second.touch()
    state = {'legacy': {'backend_1'}, 'running': True, 'stopped': set(), 'missing': False,
             'different': False, 'calls': [], 'failed': set(), 'timed_out': set()}

    def run(command):
        if 'config' in command:
            return 'backend_1\nbackend_2\nfrontend_1\n'
        if 'ps' in command:
            return command[-1] + '\n'
        name = command[-1]
        files = [str(first), str(second)]
        if state['missing']:
            files[-1] = str(tmp_path / 'missing.json')
        if state['different'] and name == 'backend_2':
            files.reverse()
        labels = {'com.docker.compose.project': 'project',
                  'com.docker.compose.project.working_dir': str(tmp_path),
                  'com.docker.compose.project.config_files': ','.join(files)}
        return json.dumps([{'State': {'Running': state['running'] and name not in state['stopped']},
                            'Config': {'Labels': labels, 'Healthcheck': {'Test':
                                ['CMD', 'old'] if name in state['legacy'] else HEALTHCHECK['test']}}}])

    monkeypatch.setattr(discovery, 'run', run)
    def subprocess_run(command, check, **kwargs):
        state['calls'].append(command)
        if command[:2] == ['docker', 'exec']:
            assert kwargs['timeout'] == 10
            name = command[2]
            if name in state['failed']:
                raise subprocess.CalledProcessError(1, command)
            if name in state['timed_out']:
                raise subprocess.TimeoutExpired(command, 10)
        else:
            state['legacy'].clear()
        return SimpleNamespace()
    monkeypatch.setattr(discovery.subprocess, 'run', subprocess_run)
    return tmp_path, state


def test_passes_ordered_active_files_to_guarded_reconciler(deployment):
    path, state = deployment
    assert discovery.main() == 0
    command = state['calls'][0]
    assert command[command.index('-f'):command.index('-f') + 4] == ['-f', str(path / 'compose.yaml'), '-f', str(path / 'overlay.json')]
    assert command[-5:] == ['--service', 'backend_1', '--service', 'backend_2', '--apply']
    assert command[command.index('--project-name') + 1] == 'project'


def test_no_recreation_when_probes_already_match(deployment):
    _, state = deployment
    state['legacy'].clear()
    assert discovery.main() == 0
    assert [call[2] for call in state['calls']] == ['backend_1', 'backend_2']
    assert all(call[:2] == ['docker', 'exec'] for call in state['calls'])


@pytest.mark.parametrize('field, message', [('failed', 'failed'), ('timed_out', 'timed out')])
def test_matching_probe_must_also_succeed_now(deployment, field, message):
    _, state = deployment
    state['legacy'].clear()
    state[field].add('backend_2')
    with pytest.raises(ValueError, match=f'backend_2 readiness probe {message}'):
        discovery.main()
    assert all(call[:2] == ['docker', 'exec'] for call in state['calls'])


def test_mixed_configuration_checks_already_correct_backend_after_reconciliation(deployment):
    _, state = deployment
    state['failed'].add('backend_2')
    with pytest.raises(ValueError, match='backend_2 readiness probe failed'):
        discovery.main()
    assert state['calls'][0][-1] == '--apply'
    assert [call[2] for call in state['calls'][1:]] == ['backend_1', 'backend_2']


@pytest.mark.parametrize('field', ['missing', 'different'])
def test_ambiguous_backends_never_reconcile(deployment, field):
    _, state = deployment
    state[field] = True
    state['legacy'].add('backend_2')
    with pytest.raises(ValueError):
        discovery.main()
    assert not state['calls']


def test_stopped_backends_are_not_started(deployment):
    _, state = deployment
    state['running'] = False
    assert discovery.main() == 0
    assert not state['calls']


def test_only_running_backend_is_reconciled(deployment):
    _, state = deployment
    state['stopped'].add('backend_2')
    assert discovery.main() == 0
    command = state['calls'][0]
    assert command[-3:] == ['--service', 'backend_1', '--apply']
    assert 'backend_2' not in command
    assert [call[2] for call in state['calls'][1:]] == ['backend_1']


@pytest.mark.skipif(os.name != 'posix', reason='fake executable requires POSIX')
@pytest.mark.parametrize('probe_ok', [True, False])
def test_discovery_cli_probes_existing_backend_without_recreating(tmp_path, probe_ok):
    (tmp_path / 'compose.yaml').touch()
    fake = tmp_path / 'docker'
    details = json.dumps([{'State': {'Running': True},
                           'Config': {'Healthcheck': {'Test': HEALTHCHECK['test']}}}])
    fake.write_text(f'''#!{sys.executable}
import json, os, sys
args = sys.argv[1:]
if 'config' in args:
    print('backend_1')
elif 'ps' in args:
    print('synthetic-container')
elif args[0] == 'inspect':
    print({details!r})
elif args[0] == 'exec':
    assert args[1:] == ['synthetic-container', 'python', '/code/scripts/backend_healthcheck.py']
    sys.exit(0 if os.environ['PROBE_OK'] == '1' else 1)
else:
    sys.exit(99)
''', encoding='utf-8')
    fake.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ['PATH'],
               PROBE_OK='1' if probe_ok else '0')
    script = Path(discovery.__file__).resolve()
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path, env=env,
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == (0 if probe_ok else 1)
    assert ('listeners are ready' in result.stdout) == probe_ok
    if not probe_ok:
        assert 'backend_1 readiness probe failed' in result.stderr
