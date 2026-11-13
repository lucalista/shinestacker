import os
import glob
import json
import pytest
import numpy as np
from shinestacker.core.exceptions import InvalidProjectError
from shinestacker.core.serialization import (
    to_json_safe, write_json_atomic, normalize_legacy, migrate_data)
from shinestacker.gui.project_model import Project

CURRENT = 2
EXAMPLES = os.path.join(os.path.dirname(__file__), '..', 'examples', '*.fsp')


def test_to_json_safe_numpy_and_containers():
    data = {'a': np.int32(3), 'b': np.float64(1.5), 'c': np.bool_(True),
            'd': np.array([1, 2]), 'e': (1, 2), 'f': {7}}
    out = json.loads(json.dumps(data, default=to_json_safe))
    assert out == {'a': 3, 'b': 1.5, 'c': True, 'd': [1, 2], 'e': [1, 2], 'f': [7]}


def test_to_json_safe_rejects_unknown_objects():
    with pytest.raises(TypeError):
        json.dumps({'a': object()}, default=to_json_safe)


def test_write_json_atomic(tmp_path):
    path = tmp_path / 'p.fsp'
    write_json_atomic(str(path), {'version': CURRENT, 'x': (1, 2)})
    assert json.loads(path.read_text()) == {'version': CURRENT, 'x': [1, 2]}
    assert [f.name for f in tmp_path.iterdir()] == ['p.fsp']


def test_write_json_atomic_failure_keeps_old_file(tmp_path):
    path = tmp_path / 'p.fsp'
    path.write_text('{"old": 1}')
    with pytest.raises(TypeError):
        write_json_atomic(str(path), {'bad': object()})
    assert json.loads(path.read_text()) == {'old': 1}
    assert [f.name for f in tmp_path.iterdir()] == ['p.fsp']


def test_normalize_legacy_tuple_and_set():
    data = {'p': {'py/tuple': [1, {'py/tuple': [2, 3]}]}, 's': {'py/set': [4]}, 'k': [5]}
    assert normalize_legacy(data) == {'p': [1, [2, 3]], 's': [4], 'k': [5]}


@pytest.mark.parametrize('tag', ['py/object', 'py/reduce', 'py/id', 'py/type'])
def test_normalize_legacy_rejects_object_tags(tag):
    with pytest.raises(InvalidProjectError):
        normalize_legacy([{'params': {tag: 'os.system'}}], 'f.fsp')


def test_migrate_version_1_normalizes():
    data = [{'params': {'v': {'py/tuple': [0, 0]}}}]
    assert migrate_data(data, 1, CURRENT) == [{'params': {'v': [0, 0]}}]


def test_migrate_current_version_untouched():
    data = [{'params': {'v': {'py/tuple': [0, 0]}}}]
    assert migrate_data(data, CURRENT, CURRENT) == data


@pytest.mark.parametrize('version', [None, 0, 'x', CURRENT + 1])
def test_migrate_invalid_version(version):
    with pytest.raises(InvalidProjectError):
        migrate_data([], version, CURRENT)


@pytest.mark.parametrize('path', sorted(glob.glob(EXAMPLES)))
def test_example_projects_roundtrip(path, tmp_path):
    with open(path, encoding='utf-8') as f:
        obj = json.load(f)
    data = migrate_data(obj['project'], obj['version'], CURRENT, path)
    project = Project.from_dict(data, obj['version'])
    out = tmp_path / 'out.fsp'
    write_json_atomic(str(out), {'project': project.to_dict(), 'version': CURRENT})
    text = out.read_text()
    assert '"py/' not in text
    saved = json.loads(text)
    assert saved['version'] == CURRENT
    reloaded = Project.from_dict(migrate_data(saved['project'], CURRENT, CURRENT), CURRENT)
    assert reloaded.to_dict() == project.to_dict()
