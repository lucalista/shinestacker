import argparse
import sys
import pytest
from shinestacker.app.args_parser_opts import (
    add_project_arguments, extract_positional_filename, get_bunch_params)
from shinestacker.config.defaults import DEFAULTS


def parse(argv, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['shinestacker'] + argv)
    _, filtered = extract_positional_filename()
    parser = argparse.ArgumentParser()
    add_project_arguments(parser)
    return parser.parse_args(filtered)


def test_no_bunches(monkeypatch):
    assert get_bunch_params(parse(['-p', 'x', '-s'], monkeypatch)) is None


def test_bunches_defaults(monkeypatch):
    params = get_bunch_params(parse(['-p', 'x', '-s', '-b'], monkeypatch))
    defaults = DEFAULTS['focus_stack_bunch_params']
    assert params == {'frames': defaults['frames'], 'overlap': defaults['overlap']}


def test_bunch_values_imply_bunches(monkeypatch):
    params = get_bunch_params(parse(
        ['-p', 'x', '-s', '--bunch-frames', '5', '--bunch-overlap', '1'], monkeypatch))
    assert params == {'frames': 5, 'overlap': 1}


@pytest.mark.parametrize('argv', [
    ['--bunch-frames', '0'], ['--bunch-frames', '21'],
    ['--bunch-overlap', '11'], ['--bunch-frames', '3', '--bunch-overlap', '3']])
def test_invalid_bunch_values(monkeypatch, argv):
    with pytest.raises(SystemExit):
        get_bunch_params(parse(['-p', 'x', '-s'] + argv, monkeypatch))
