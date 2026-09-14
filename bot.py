import os
import html
import requests
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise RuntimeError('BOT_TOKEN environment variable is missing.')

API = f'https://api.telegram.org/bot{TOKEN}'
state = {}


def api(method, payload=None):
    r = requests.post(f'{API}/{method}', json=payload or {}, timeout=60)
    d = r.json()
    if not d.get('ok'):
        raise RuntimeError(d)
    return d['result']


def esc(x):
    return html.escape(str(x), quote=False)


def table_html(t):
    attrs = []
    if t['bordered']:
        attrs.append('bordered')
    if t['striped']:
        attrs.append('striped')
    if t['compact']:
        attrs.append('compact')
    a = (' ' + ' '.join(attrs)) if attrs else ''
    s = (f"<h3>{esc(t['title'])}</h3>" if t['title'] else '') + f'<table{a}>'
    for r, row in enumerate(t['rows']):
        tag = 'th' if r == 0 else 'td'
        s += '<tr>' + ''.join(
            f'<{tag}>{esc(v) or "&nbsp;"}</{tag}>' for v in row
        ) + '</tr>'
    return s + '</table>'


def kb(t):
    return {'inline_keyboard': [
        [
            {'text': '✏️ Edit Cell', 'callback_data': 'edit'},
            {'text': '➕ Add Row', 'callback_data': 'ar'}
        ],
        [
            {'text': '➕ Add Column', 'callback_data': 'ac'},
            {'text': '🗑 Delete Row', 'callback_data': 'dr'}
        ],
        [
            {'text': '🗑 Delete Column', 'callback_data': 'dc'},
            {'text': '⚙️ Settings', 'callback_data': 'set'}
        ],
        [
            {'text': '👀 Preview', 'callback_data': 'preview'},
            {'text': '🚀 Publish', 'callback_data': 'pub'}
        ]
    ]}


def msg(chat, text, markup=None):
    p = {'chat_id': chat, 'text': text}
    if markup:
        p['reply_markup'] = {'inline_keyboard': markup}
    return api('sendMessage', p)


def editor(chat, uid):
    s = state[uid]
    p = {
        'chat_id': chat,
        'rich_message': {'html': table_html(s['t']), 'is_rtl': False},
        'reply_markup': kb(s['t'])
    }
    mid = s.get('mid')
    if mid:
        try:
            api('editMessageText', dict(p, message_id=mid))
            return
        except Exception:
            pass
    m = api('sendRichMessage', p)
    s['mid'] = m['message_id']


def init(chat, uid, r=2, c=2):
    r = max(1, min(50, r))
    c = max(1, min(20, c))
    rows = [['' for _ in range(c)] for _ in range(r)]
    for j in range(c):
        rows[0][j] = f'Column {j + 1}'
    state[uid] = {
        't': {
            'rows': rows,
            'title': '',
            'bordered': True,
            'striped': False,
            'compact': True
        },
        'mid': None,
        'await': None
    }
    editor(chat, uid)


def cell_k(prefix, rows, cols):
    out = []
    for r in range(rows):
        row = []
        for c in range(cols):
            row.append({
                'text': f'R{r + 1} C{c + 1}',
                'callback_data': f'{prefix}:{r}:{c}'
            })
            if len(row) == 3:
                out.append(row)
                row = []
        if row:
            out.append(row)
    out.append([{'text': '↩️ Back', 'callback_data': 'back'}])
    return out


def pick(prefix, n, label):
    out = []
    for i in range(n):
        if i % 3 == 0:
            out.append([])
        out[-1].append({
            'text': f'{label} {i + 1}',
            'callback_data': f'{prefix}:{i}'
        })
    out.append([{'text': '↩️ Back', 'callback_data': 'back'}])
    return out


def edit_text(chat, mid, text, keyboard):
    api('editMessageText', {
        'chat_id': chat,
        'message_id': mid,
        'text': text,
        'reply_markup': {'inline_keyboard': keyboard}
    })


def cb(q):
    chat = q['message']['chat']['id']
    uid = q['from']['id']
    mid = q['message']['message_id']
    d = q.get('data', '')
    api('answerCallbackQuery', {'callback_query_id': q['id']})

    if uid not in state:
        init(chat, uid)

    s = state[uid]
    t = s['t']
    rows = t['rows']
    nr = len(rows)
    nc = len(rows[0])

    if d == 'back':
        s['await'] = None
        editor(chat, uid)
        return

    if d == 'edit':
        edit_text(chat, mid, '✏️ <b>Select a cell to edit</b>', cell_k('cell', nr, nc))
        return

    if d.startswith('cell:'):
        _, r, c = d.split(':')
        r, c = int(r), int(c)
        s['await'] = {'r': r, 'c': c}
        msg(
            chat,
            f'✏️ Editing R{r + 1} C{c + 1}\n'
            f'Current: <code>{esc(rows[r][c]) or "(empty)"}</code>\n\n'
            'Send the new text. Use /empty for blank.'
        )
        return

    if d == 'ar':
        rows.append([''] * nc)
        editor(chat, uid)
        return

    if d == 'ac':
        for row in rows:
            row.append('')
        editor(chat, uid)
        return

    if d == 'dr':
        if nr > 1:
            edit_text(chat, mid, '🗑 <b>Select a row to delete</b>', pick('xrow', nr, 'Row'))
        else:
            msg(chat, '⚠️ At least 1 row must remain.')
        return

    if d.startswith('xrow:'):
        rows.pop(int(d.split(':')[1]))
        editor(chat, uid)
        return

    if d == 'dc':
        if nc > 1:
            edit_text(chat, mid, '🗑 <b>Select a column to delete</b>', pick('xcol', nc, 'Col'))
        else:
            msg(chat, '⚠️ At least 1 column must remain.')
        return

    if d.startswith('xcol:'):
        c = int(d.split(':')[1])
        for row in rows:
            row.pop(c)
        editor(chat, uid)
        return

    if d == 'set':
        k = [
            [
                {'text': f"Border: {'ON' if t['bordered'] else 'OFF'}", 'callback_data': 'tb'},
                {'text': f"Striped: {'ON' if t['striped'] else 'OFF'}", 'callback_data': 'ts'}
            ],
            [
                {'text': f"Compact: {'ON' if t['compact'] else 'OFF'}", 'callback_data': 'tc'}
            ],
            [{'text': '↩️ Back', 'callback_data': 'back'}]
        ]
        edit_text(chat, mid, '⚙️ <b>Table settings</b>', k)
        return

    if d in ('tb', 'ts', 'tc'):
        t[{'tb': 'bordered', 'ts': 'striped', 'tc': 'compact'}[d]] ^= True
        editor(chat, uid)
        return

    if d in ('preview', 'pub'):
        api('sendRichMessage', {
            'chat_id': chat,
            'rich_message': {'html': table_html(t), 'is_rtl': False}
        })
        return


def message(m):
    chat = m['chat']['id']
    uid = m['from']['id']
    text = m.get('text', '').strip()

    if text.startswith('/start') or text.startswith('/newtable'):
        p = text.split()
        r = int(p[1]) if len(p) > 1 and p[1].isdigit() else 2
        c = int(p[2]) if len(p) > 2 and p[2].isdigit() else 2
        init(chat, uid, r, c)
        msg(chat, '🎉 <b>Rich Table Maker ready!</b>\nUse the buttons under the table.')
        return

    if text == '/help':
        msg(
            chat,
            '/newtable — 2×2\n'
            '/newtable 3 4 — 3×4\n\n'
            'Edit cells, add/delete rows and columns, change border/striped/compact, '
            'preview and publish.'
        )
        return

    if uid not in state:
        msg(chat, 'Send /newtable first.')
        return

    s = state[uid]
    if s.get('await'):
        r, c = s['await']['r'], s['await']['c']
        s['t']['rows'][r][c] = '' if text == '/empty' else text
        s['await'] = None
        msg(chat, '✅ Cell updated.')
        editor(chat, uid)
    else:
        msg(chat, 'Use the buttons under the table.')


class HealthHandler(BaseHTTPRequestHandler):
    """Tiny HTTP server so Render Web Service can detect a listening port."""

    def do_GET(self):
        if self.path in ('/', '/health', '/healthz'):
            body = b'Rich Table Maker is running.\n'
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Keep Render logs clean; health checks can be frequent.
        return


def start_web_server():
    port = int(os.getenv('PORT', '10000'))
    server = ThreadingHTTPServer(('0.0.0.0', port), HealthHandler)
    print(f'HTTP health server listening on 0.0.0.0:{port}', flush=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    print('Starting Rich Table Maker...', flush=True)
    start_web_server()

    # Ensure polling mode is available if this bot token previously had a webhook.
    try:
        api('deleteWebhook', {'drop_pending_updates': False})
        print('Telegram webhook cleared; starting long polling.', flush=True)
    except Exception as e:
        print('Could not clear webhook:', repr(e), flush=True)

    off = None
    while True:
        try:
            p = {'timeout': 50}
            if off is not None:
                p['offset'] = off
            d = requests.get(f'{API}/getUpdates', params=p, timeout=60).json()
            for u in d.get('result', []):
                off = u['update_id'] + 1
                try:
                    if 'callback_query' in u:
                        cb(u['callback_query'])
                    elif 'message' in u and 'text' in u['message']:
                        message(u['message'])
                except Exception as e:
                    print('update error', repr(e), flush=True)
        except Exception as e:
            print('loop error', repr(e), flush=True)


if __name__ == '__main__':
    main()
