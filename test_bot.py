import os
import pytest
from unittest.mock import patch, MagicMock

os.environ['BOT_TOKEN'] = '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'

import bot


def test_table_text_basic():
    t = {
        'rows': [['Col 1', 'Col 2'], ['Val 1', 'Val 2']],
        'title': 'Test Table',
        'bordered': True,
        'striped': False,
        'compact': True
    }
    res = bot.table_text(t)
    assert '<b>Test Table</b>' in res
    assert '<pre><code>' in res
    assert '+-------+-------+' in res
    assert '| Col 1 | Col 2 |' in res
    assert '+=======+=======+' in res


def test_table_text_options():
    t_unbordered = {
        'rows': [['Col 1', 'Col 2'], ['Val 1', 'Val 2'], ['Val 3', 'Val 4']],
        'title': '',
        'bordered': False,
        'striped': True,
        'compact': False
    }
    res = bot.table_text(t_unbordered)
    assert '+' not in res
    assert 'Col 1' in res
    assert '-' in res


def test_table_text_escaping():
    t = {
        'rows': [['<Tag>', 'A & B']],
        'title': '<b>Header</b>',
        'bordered': True,
        'striped': False,
        'compact': True
    }
    res = bot.table_text(t)
    assert '<b>&lt;b&gt;Header&lt;/b&gt;</b>' in res
    assert '&lt;Tag&gt;' in res
    assert 'A &amp; B' in res


@patch('bot.api')
def test_commands_and_state(mock_api):
    mock_api.side_effect = lambda method, payload=None: (
        {'message_id': 100} if method == 'sendMessage' else {}
    )

    bot.state.clear()
    msg = {'chat': {'id': 123}, 'from': {'id': 456}, 'text': '/start'}
    bot.message(msg)

    assert 456 in bot.state
    assert len(bot.state[456]['t']['rows']) == 2
    assert len(bot.state[456]['t']['rows'][0]) == 2

    # Test callback for edit
    cb_q = {
        'id': 'q1',
        'chat': {'id': 123},
        'from': {'id': 456},
        'message': {'chat': {'id': 123}, 'message_id': 100},
        'data': 'edit'
    }
    bot.cb(cb_q)

    # Test selecting cell 0,0
    cb_cell = {
        'id': 'q2',
        'chat': {'id': 123},
        'from': {'id': 456},
        'message': {'chat': {'id': 123}, 'message_id': 100},
        'data': 'cell:0:0'
    }
    bot.cb(cb_cell)
    assert bot.state[456]['await'] == {'type': 'cell', 'r': 0, 'c': 0}

    # Test typing new value
    msg_val = {'chat': {'id': 123}, 'from': {'id': 456}, 'text': 'Header 1'}
    bot.message(msg_val)
    assert bot.state[456]['t']['rows'][0][0] == 'Header 1'
    assert bot.state[456]['await'] is None
