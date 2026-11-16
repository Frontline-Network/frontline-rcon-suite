import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.backend_health_override import backend_images, build_override


def test_only_real_configured_backend_numbers_are_added():
    names = ['backend_1', 'frontend_7', 'backend_7', 'backend_32', 'backend_33',
             'backend_99999999999999999999', 'backend_0', 'backend_01', 'backend_7', 'backend_8;bad']
    result = build_override(names)['services']
    assert set(result) == {'backend_1', 'backend_7', 'backend_32', 'backend_33',
                           'backend_99999999999999999999'}
    for service in result.values():
        health = service['healthcheck']
        assert health['disable'] is False
        assert health['test'] == ['CMD', 'python', '/code/scripts/backend_healthcheck.py']


def test_image_inventory_checks_every_configured_backend_and_rejects_missing_image():
    compose = {'services': {'backend_1': {'image': 'frontline:one'},
                            'backend_7': {'image': 'legacy:seven'},
                            'frontend_7': {'image': 'frontend:seven'}}}
    assert backend_images(compose, ['backend_1', 'backend_7', 'frontend_7']) == [
        'frontline:one', 'legacy:seven']
    with pytest.raises(ValueError, match='backend_8'):
        backend_images(compose, ['backend_1', 'backend_8'])


def test_cli_emits_compose_document_without_extra_services(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'backend_health_override.py'
    output = tmp_path / 'health.json'
    subprocess.run([sys.executable, str(script), str(output), 'backend_9', 'redis'], check=True)
    assert list(json.loads(output.read_text())['services']) == ['backend_9']
