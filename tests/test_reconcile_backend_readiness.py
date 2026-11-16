import json
import subprocess

import pytest

from scripts import reconcile_backend_readiness as reconcile
from scripts.backend_health_override import HEALTHCHECK


@pytest.fixture
def deployment(tmp_path, monkeypatch):
    (tmp_path / 'compose.yaml').write_text('services: {}')
    baseline = {'services': {
        'backend_1': {'image': 'backend:1', 'healthcheck': {'test': ['CMD', 'old']}},
        'backend_33': {'image': 'backend:33', 'healthcheck': {'test': ['CMD', 'old']}},
        'frontend_1': {'image': 'frontend:1'},
    }}
    state = {'calls': [], 'hash_ok': True, 'running': True, 'image_ok': True,
             'fail_up': False, 'target_drift': False, 'already_correct': set(), 'after_up': False,
             'post_up_health': 'healthy',
             'base_services': ['backend_1', 'backend_33', 'frontend_1']}

    def fake_run(command, *, capture=True):
        state['calls'].append(command)
        if command[:2] == ['docker', 'compose']:
            if 'config' in command and '--services' in command:
                return '\n'.join(state['base_services']) + '\n'
            if 'config' in command and '--format' in command:
                result = json.loads(json.dumps(baseline))
                files = [command[index + 1] for index, value in enumerate(command[:-1]) if value == '-f']
                if len(files) > 1:
                    override = json.loads(open(files[-1], encoding='utf-8').read())
                    for name, entry in override['services'].items():
                        result['services'][name].update(entry)
                    if state['target_drift']:
                        result['services']['frontend_1']['image'] = 'changed'
                return json.dumps(result)
            if 'config' in command and '--hash' in command:
                return f'{command[-1]} ' + 'a' * 64 + '\n'
            if 'ps' in command:
                return f'container-{command[-1]}\n'
            if 'up' in command:
                if state['fail_up']:
                    state['fail_up'] = False
                    raise subprocess.CalledProcessError(1, command)
                state['after_up'] = command.count('-f') > 1
                return ''
        if command[:2] == ['docker', 'inspect']:
            name = command[-1].removeprefix('container-')
            test = HEALTHCHECK['test'] if name in state['already_correct'] or state['after_up'] else ['CMD', 'old']
            return json.dumps([{'State': {'Running': state['running'], 'Health': {'Status': state['post_up_health']}},
                                'Image': f'sha256:{name}',
                                'Config': {'Healthcheck': {'Test': test}, 'Labels': {
                                    'com.docker.compose.config-hash': ('a' if state['hash_ok'] else 'b') * 64}}}])
        if command[:3] == ['docker', 'image', 'inspect']:
            name = 'backend_' + command[-1].split(':')[-1]
            return f'sha256:{name if state["image_ok"] else "other"}\n'
        if command[:2] == ['docker', 'run']:
            return ''
        raise AssertionError(f'Unexpected command: {command}')

    monkeypatch.setattr(reconcile, 'run', fake_run)
    return tmp_path, state


def args(path, *extra):
    return ['--project-dir', str(path), '-f', 'compose.yaml', *extra]


def test_preflight_never_recreates_and_only_uses_existing_backends(deployment):
    path, state = deployment
    assert reconcile.main(args(path)) == 0
    assert not any('up' in call for call in state['calls'])
    assert not (path / '.deploy-state').exists()
    assert len([call for call in state['calls'] if call[:2] == ['docker', 'run']]) == 2


def test_backend_declared_only_by_shared_override_is_never_started(deployment):
    path, state = deployment
    state['base_services'] = ['backend_1', 'frontend_1']
    assert reconcile.main(args(path, '--apply')) == 0
    ups = [call for call in state['calls'] if 'up' in call]
    assert len(ups) == 1 and ups[0][-1:] == ['backend_1']
    override = json.loads((path / '.deploy-state/backend-readiness-override.json').read_text())
    assert set(override['services']) == {'backend_1'}


def test_apply_recreates_only_outdated_services_and_persists_override(deployment):
    path, state = deployment
    state['already_correct'].add('backend_1')
    assert reconcile.main(args(path, '--apply')) == 0
    ups = [call for call in state['calls'] if 'up' in call]
    assert len(ups) == 1 and ups[0][-1:] == ['backend_33']
    assert '--no-deps' in ups[0] and '--no-build' in ups[0] and '--wait' in ups[0]
    override = json.loads((path / '.deploy-state/backend-readiness-override.json').read_text())
    assert set(override['services']) == {'backend_1', 'backend_33'}


@pytest.mark.parametrize('field', ['hash_ok', 'running', 'image_ok'])
def test_preflight_rejects_drift_or_stopped_containers_before_changes(deployment, field):
    path, state = deployment
    state[field] = False
    with pytest.raises(ValueError):
        reconcile.main(args(path, '--apply'))
    assert not any('up' in call for call in state['calls'])


def test_override_cannot_change_other_compose_settings(deployment):
    path, state = deployment
    state['target_drift'] = True
    with pytest.raises(ValueError, match='other Compose settings'):
        reconcile.main(args(path, '--apply'))
    assert not any('up' in call for call in state['calls'])


def test_failed_reconciliation_attempts_restore_of_same_services(deployment):
    path, state = deployment
    state['fail_up'] = True
    with pytest.raises(subprocess.CalledProcessError):
        reconcile.main(args(path, '--apply'))
    ups = [call for call in state['calls'] if 'up' in call]
    assert len(ups) == 2 and ups[0][-2:] == ups[1][-2:] == ['backend_1', 'backend_33']
    assert len([value for value in ups[0] if value == '-f']) == 2
    assert len([value for value in ups[1] if value == '-f']) == 1


def test_compose_success_with_starting_health_is_rolled_back(deployment):
    path, state = deployment
    state['post_up_health'] = 'starting'
    with pytest.raises(ValueError, match='did not become healthy'):
        reconcile.main(args(path, '--apply', '--wait-timeout', '5'))
    ups = [call for call in state['calls'] if 'up' in call]
    assert len(ups) == 2 and ups[0][-2:] == ups[1][-2:] == ['backend_1', 'backend_33']
