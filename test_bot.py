import os
import pytest
from unittest.mock import patch, MagicMock

os.environ['BOT_TOKEN'] = '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'

import bot


def test_table_html_basic_and_links():
    t = {
        'rows': [
            [{'text': 'Col 1', 'link': ''}, {'text': 'Col 2', 'link': ''}],
            [{'text': 'Val 1', 'link': 'https://example.com'}, {'text': 'Val 2', 'link': ''}]
        ],
        'title': 'Test Table',
        'bordered': True,
        'striped': False,
        'compact': True
    }
    res = bot.table_html(t)
    assert '<b>Test Table</b>' in res
    assert '<pre>' in res
    assert 'href="https://example.com"' in res
    assert 'Val 1' in res
    assert 'Val 2' in res


def test_table_html_escaping():
    t = {
        'rows': [[{'text': '<Tag>', 'link': 'https://example.com?a=1&b=2'}]],
        'title': '<b>Header</b>',
        'bordered': True,
        'striped': False,
        'compact': True
    }
    res = bot.table_html(t)
    assert '<b>&lt;b&gt;Header&lt;/b&gt;</b>' in res
    assert '&lt;Tag&gt;' in res
    assert 'href="https://example.com?a=1&amp;b=2"' in res


@patch('bot.api')
def test_commands_cell_link_flow(mock_api):
    mock_api.side_effect = lambda method, payload=None: (
        {'message_id': 100} if method == 'sendMessage' else {}
    )

    bot.state.clear()
    msg = {'chat': {'id': 123}, 'from': {'id': 456}, 'text': '/start'}
    bot.message(msg)

    assert 456 in bot.state
    assert len(bot.state[456]['t']['rows']) == 2

    # Step 1: Select cell 0,0
    cb_cell = {
        'id': 'q1',
        'chat': {'id': 123},
        'from': {'id': 456},
        'message': {'chat': {'id': 123}, 'message_id': 100},
        'data': 'cell:0:0'
    }
    bot.cb(cb_cell)
    assert bot.state[456]['await']['type'] == 'cell_text'

    # Step 2: Send cell text
    msg_text = {'chat': {'id': 123}, 'from': {'id': 456}, 'text': 'Quiz 1'}
    bot.message(msg_text)
    assert bot.state[456]['await']['type'] == 'cell_link'
    assert bot.state[456]['await']['text'] == 'Quiz 1'

    # Step 3: Send cell URL
    msg_link = {'chat': {'id': 123}, 'from': {'id': 456}, 'text': 'https://t.me/quiz/1'}
    bot.message(msg_link)

    assert bot.state[456]['await'] is None
    cell = bot.state[456]['t']['rows'][0][0]
    assert cell['text'] == 'Quiz 1'
    assert cell['link'] == 'https://t.me/quiz/1'
