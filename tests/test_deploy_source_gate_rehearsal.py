"""Exercise the real deploy script against a fake Docker and isolated Git repo."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(os.environ.get("DEPLOY_SOURCE_ROOT", Path(__file__).resolve().parents[1]))

FAKE_DOCKER = r'''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys, tarfile
args = sys.argv[1:]
with open(os.environ['FAKE_DOCKER_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\n')
if args[:1] == ['compose']:
    if 'config' in args:
        if '--services' in args:
            print('redis\npostgres\nmaintenance\nbackend_1\nfrontend_1\nsupervisor_1\nbackend_3\nfrontend_3\nsupervisor_3')
        elif '--environment' in args:
            print('MOBILE_INTEGRATION_ENABLED=false')
        elif '--format' in args:
            names = ['redis', 'postgres', 'maintenance', 'backend_1', 'frontend_1', 'supervisor_1', 'backend_3', 'frontend_3', 'supervisor_3']
            services = {name: {'image': 'fake/backend' if name.startswith('backend_') else 'fake/other'} for name in names}
            for kind in ('frontend', 'supervisor'):
                for number in (1, 3):
                    services[f'{kind}_{number}']['depends_on'] = {f'backend_{number}': {}}
            print(json.dumps({'services': services}))
        sys.exit(0)
    if 'ps' in args:
        if '--status' in args:
            print('redis\npostgres\nmaintenance\nbackend_3\nfrontend_3\nsupervisor_3')
        elif 'postgres' in args:
            print('synthetic-postgres')
        sys.exit(0)
    if 'build' in args:
        image = pathlib.Path(os.environ['FAKE_IMAGE_ROOT'])
        image.mkdir()
        archive = subprocess.check_output(['git', 'archive', '--format=tar', 'HEAD', 'rcon', 'rconweb', 'alembic', 'scripts', 'docs/releases', 'alembic.ini', 'entrypoint.sh', 'manage.py', 'LICENSE', 'requirements.lock', 'requirements-vcs.txt'])
        import io
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as tar:
            tar.extractall(image)
        if os.environ['FAKE_IMAGE_STALE'] == '1':
            (image / 'rcon/models.py').write_text('stale image\n')
        sys.exit(0)
    if 'up' in args:
        # All commands are fake: reaching this point proves the gate passed.
        pathlib.Path(os.environ['FAKE_UP_ENV']).write_text(os.environ.get('FRONTLINE_MAINTENANCE_IMAGE', 'MISSING'))
        sys.exit(0 if os.environ.get('FAKE_UP_SUCCESS') == '1' else 71)
    sys.exit(0)
if args[:2] == ['image', 'inspect']:
    sys.exit(0)
if args[:1] == ['exec']:
    print('synthetic-database-dump')
    sys.exit(0)
if args[:1] == ['run']:
    if '-c' in args:
        sys.exit(0)
    mounts = [args[index + 1] for index, arg in enumerate(args[:-1]) if arg == '-v']
    archive = next(value.split(':')[0] for value in mounts if 'frontline-target-source.tar' in value)
    verifier = next(value.split(':')[0] for value in mounts if 'frontline-verify-source.py' in value)
    sys.exit(subprocess.run([sys.executable, verifier, archive, '--root', os.environ['FAKE_IMAGE_ROOT']]).returncode)
sys.exit(0)
'''


@unittest.skipUnless(os.name == 'posix' and shutil.which('bash') and shutil.which('git'), 'requires POSIX, bash and git')
class DeploySourceGateRehearsal(unittest.TestCase):
    def run_case(self, stale, success=False):
        with tempfile.TemporaryDirectory(prefix='rcon-deploy-gate-') as directory:
            base = Path(directory)
            repo = base / 'repo'
            repo.mkdir()
            def git(*args):
                return subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-b', 'master')
            git('config', 'user.name', 'Synthetic Test')
            git('config', 'user.email', 'synthetic@invalid')
            for name in ('scripts/deploy_frontline.sh', 'scripts/select_deployment_services.py',
                         'scripts/verify_backend_source.py', 'scripts/backend_health_override.py'):
                target = repo / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(SOURCE / name, target)
            files = {
                '.gitignore': '.env\n.deploy-backups/\n.deploy-state/\n',
                'compose.yaml': 'services: {}\n', 'compose.mobile-admin.yaml': 'services: {}\n',
                'compose.combined-workers.yaml': 'services: {}\n',
                'rcon/models.py': 'old source\n', 'rconweb/manage.py': 'pass\n',
                'alembic/env.py': 'pass\n', 'docs/releases/example.md': 'release\n',
                'alembic.ini': '', 'entrypoint.sh': '', 'manage.py': '', 'LICENSE': '',
                'requirements.lock': '', 'requirements-vcs.txt': '',
            }
            for name, content in files.items():
                target = repo / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            git('add', '.')
            git('commit', '-m', 'base')
            baseline = git('rev-parse', 'HEAD')
            bare = base / 'remote.git'
            subprocess.run(['git', 'init', '--bare', str(bare)], check=True, capture_output=True)
            git('remote', 'add', 'frontline', str(bare))
            git('push', 'frontline', 'master')
            (repo / 'rcon/models.py').write_text('new source\n')
            git('add', 'rcon/models.py')
            git('commit', '-m', 'target')
            git('push', 'frontline', 'master')
            git('reset', '--hard', baseline)
            (repo / '.env').write_text('FRONTLINE_BACKGROUND_WORKER_MODE=combined\nFRONTLINE_MAINTENANCE_IMAGE=synthetic/pilot\n')
            fake_bin = base / 'bin'
            fake_bin.mkdir()
            docker = fake_bin / 'docker'
            docker.write_text(FAKE_DOCKER)
            docker.chmod(0o755)
            log = base / 'docker.log'
            env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ['PATH'],
                       FAKE_DOCKER_LOG=str(log), FAKE_IMAGE_ROOT=str(base / 'image'),
                       FAKE_IMAGE_STALE='1' if stale else '0', FAKE_UP_SUCCESS='1' if success else '0',
                       FAKE_UP_ENV=str(base / 'up-env'))
            result = subprocess.run(['bash', 'scripts/deploy_frontline.sh', '--deploy'],
                                    cwd=repo, env=env, capture_output=True, text=True, timeout=45)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            pin = (repo / '.env').read_text()
            up_env = (base / 'up-env').read_text() if (base / 'up-env').exists() else None
            return result, calls, git('rev-parse', 'HEAD'), baseline, pin, up_env

    def test_stale_image_aborts_before_service_changes_and_restores_checkout(self):
        result, calls, current, baseline, _, _ = self.run_case(stale=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Different file: rcon/models.py', result.stdout)
        self.assertIn('Deployment stopped before changing running services.', result.stderr)
        self.assertFalse(any(call[:1] == ['compose'] and ('up' in call or 'rm' in call) for call in calls))
        self.assertEqual(current, baseline)

    def test_matching_image_reaches_service_start_with_only_running_servers(self):
        result, calls, current, baseline, pin, up_env = self.run_case(stale=False)
        self.assertIn('Backend image runtime source matches the target Git archive.', result.stdout)
        starts = [call for call in calls if call[:1] == ['compose'] and 'up' in call]
        self.assertEqual(len(starts), 1)
        self.assertIn('backend_3', starts[0])
        self.assertNotIn('backend_1', starts[0])
        self.assertNotEqual(current, baseline)
        self.assertIn('FRONTLINE_MAINTENANCE_IMAGE=synthetic/pilot', pin)
        self.assertEqual(up_env, '')

    def test_successful_update_removes_only_pilot_pin(self):
        result, _, _, _, pin, up_env = self.run_case(stale=False, success=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('FRONTLINE_MAINTENANCE_IMAGE=', pin)
        self.assertIn('FRONTLINE_BACKGROUND_WORKER_MODE=combined', pin)
        self.assertEqual(up_env, '')


if __name__ == '__main__':
    unittest.main()
