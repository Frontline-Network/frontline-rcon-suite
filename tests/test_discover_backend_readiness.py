import json
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
             'different': False, 'calls': []}

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
    monkeypatch.setattr(discovery.subprocess, 'run',
                        lambda command, check: state['calls'].append(command) or SimpleNamespace())
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
    assert not state['calls']


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
