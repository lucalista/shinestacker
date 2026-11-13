import os
import json
import tempfile
import numpy as np
from .exceptions import InvalidProjectError

FORBIDDEN_LEGACY_TAGS = ('py/object', 'py/reduce', 'py/id', 'py/type', 'py/state', 'py/newargs')
LIST_LEGACY_TAGS = ('py/tuple', 'py/set')


def to_json_safe(obj):
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (set, frozenset, tuple)):
        return list(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def write_json_atomic(file_path, data):
    directory = os.path.dirname(os.path.abspath(file_path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix='.tmp-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, default=to_json_safe)
        os.replace(tmp_path, file_path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def normalize_legacy(obj, file_path=''):
    if isinstance(obj, dict):
        for tag in FORBIDDEN_LEGACY_TAGS:
            if tag in obj:
                raise InvalidProjectError(file_path)
        for tag in LIST_LEGACY_TAGS:
            if tag in obj:
                return [normalize_legacy(item, file_path) for item in obj[tag]]
        return {k: normalize_legacy(v, file_path) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_legacy(item, file_path) for item in obj]
    return obj


def migrate_data(data, version, current_version, file_path=''):
    if not isinstance(version, int) or version < 1 or version > current_version:
        raise InvalidProjectError(file_path)
    if version < 2:
        data = normalize_legacy(data, file_path)
    return data
