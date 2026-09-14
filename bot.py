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
    return html.escape(str(x or ''), quote=False)


def parse_cell(cell):
    if isinstance(cell, dict):
        return cell.get('text', ''), cell.get('link', '')
    return str(cell or ''), ''


def table_html(t):
    title = t.get('title', '').strip()
    rows = t.get('rows', [])
    bordered = t.get('bordered', True)
    striped = t.get('striped', False)
    compact = t.get('compact', True)

    if not rows or not rows[0]:
        body = '<i>(Empty table)</i>'
        return f'<b>{esc(title)}</b>\n\n{body}' if title else body

    nr = len(rows)
    nc = len(rows[0])

    parsed_rows = [[parse_cell(cell) for cell in row] for row in rows]

    col_widths = []
    for c in range(nc):
        w = max(1, max(len(parsed_rows[r][c][0]) for r in range(nr)))
        col_widths.append(w)

    pad = 1 if compact else 2
    pad_str = ' ' * pad

    lines = []

    def format_cell(text, link, target_w):
        raw_text = str(text).replace('\r', '').replace('\n', ' ')
        raw_len = len(raw_text)
        esc_val = esc(raw_text)
        if link:
            cell_content = f'<a href="{esc(link)}">{esc_val}</a>'
        else:
            cell_content = esc_val

        # Pad so visually it equals target_w
        esc_len = len(esc_val)
        padded = cell_content + (' ' * (target_w + esc_len - raw_len - len(esc_val)))
        return padded

    if bordered:
        top_line = '+' + '+'.join('-' * (w + 2 * pad) for w in col_widths) + '+'
        head_sep = '+' + '+'.join('=' * (w + 2 * pad) for w in col_widths) + '+'
        row_sep = '+' + '+'.join('-' * (w + 2 * pad) for w in col_widths) + '+' if striped else None
        bot_line = '+' + '+'.join('-' * (w + 2 * pad) for w in col_widths) + '+'

        lines.append(top_line)
        for r, row in enumerate(parsed_rows):
            cell_strs = [format_cell(row[c][0], row[c][1], col_widths[c]) for c in range(nc)]
            row_line = '|' + '|'.join(f'{pad_str}{cs}{pad_str}' for cs in cell_strs) + '|'
            lines.append(row_line)

            if r == 0 and nr > 1:
                lines.append(head_sep)
            elif r > 0 and r < nr - 1 and row_sep:
                lines.append(row_sep)

        lines.append(bot_line)
    else:
        head_sep = ' '.join('=' * (w + 2 * pad) for w in col_widths)
        row_sep = ' '.join('-' * (w + 2 * pad) for w in col_widths) if striped else None

        for r, row in enumerate(parsed_rows):
            cell_strs = [format_cell(row[c][0], row[c][1], col_widths[c]) for c in range(nc)]
            row_line = ' '.join(f'{pad_str}{cs}{pad_str}' for cs in cell_strs)
            lines.append(row_line)

            if r == 0 and nr > 1:
                lines.append(head_sep)
            elif r > 0 and r < nr - 1 and row_sep:
                lines.append(row_sep)

    # Collect links for footer reference if any
    links_list = []
    for r, row in enumerate(parsed_rows):
        for c, (text, link) in enumerate(row):
            if link:
                links_list.append(f'• R{r + 1} C{c + 1} ({esc(text) or "Link"}): <a href="{esc(link)}">{esc(link)}</a>')

    table_block = f'<pre>' + '\n'.join(lines) + '</pre>'
    parts = []
    if title:
        parts.append(f'<b>{esc(title)}</b>')
    parts.append(table_block)
    if links_list:
        parts.append('<b>Links:</b>\n' + '\n'.join(links_list))

    return '\n\n'.join(parts)


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
            {'text': '✏️ Edit Title', 'callback_data': 'edittitle'},
            {'text': '🚀 Publish', 'callback_data': 'pub'}
        ]
    ]}


def msg(chat, text, markup=None):
    p = {
        'chat_id': chat,
        'text': text,
        'parse_mode': 'HTML'
    }
    if markup:
        if isinstance(markup, dict) and 'inline_keyboard' in markup:
            p['reply_markup'] = markup
        elif isinstance(markup, list):
            p['reply_markup'] = {'inline_keyboard': markup}
        else:
            p['reply_markup'] = markup
    return api('sendMessage', p)


def editor(chat, uid):
    s = state[uid]
    p = {
        'chat_id': chat,
        'text': table_html(s['t']),
        'parse_mode': 'HTML',
        'reply_markup': kb(s['t'])
    }
    mid = s.get('mid')
    if mid:
        try:
            api('editMessageText', dict(p, message_id=mid))
            return
        except Exception:
            pass
    m = api('sendMessage', p)
    s['mid'] = m['message_id']


def init(chat, uid, r=2, c=2):
    r = max(1, min(50, r))
    c = max(1, min(20, c))
    rows = [[{'text': '', 'link': ''} for _ in range(c)] for _ in range(r)]
    for j in range(c):
        rows[0][j] = {'text': f'Column {j + 1}', 'link': ''}
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
    p = {
        'chat_id': chat,
        'message_id': mid,
        'text': text,
        'parse_mode': 'HTML'
    }
    if keyboard:
        if isinstance(keyboard, dict) and 'inline_keyboard' in keyboard:
            p['reply_markup'] = keyboard
        elif isinstance(keyboard, list):
            p['reply_markup'] = {'inline_keyboard': keyboard}
        else:
            p['reply_markup'] = keyboard
    return api('editMessageText', p)


def settings_kb(t):
    return [
        [
            {'text': f"Border: {'ON' if t['bordered'] else 'OFF'}", 'callback_data': 'tb'},
            {'text': f"Striped: {'ON' if t['striped'] else 'OFF'}", 'callback_data': 'ts'}
        ],
        [
            {'text': f"Compact: {'ON' if t['compact'] else 'OFF'}", 'callback_data': 'tc'}
        ],
        [{'text': '↩️ Back', 'callback_data': 'back'}]
    ]


def cb(q):
    chat = q['message']['chat']['id']
    uid = q['from']['id']
    mid = q['message']['message_id']
    d = q.get('data', '')
    try:
        api('answerCallbackQuery', {'callback_query_id': q['id']})
    except Exception:
        pass

    if uid not in state:
        init(chat, uid)

    s = state[uid]
    t = s['t']
    rows = t['rows']
    nr = len(rows)
    nc = len(rows[0]) if rows else 0

    if d == 'back':
        s['await'] = None
        editor(chat, uid)
        return

    if d == 'edit':
        edit_text(chat, mid, '✏️ <b>Select a cell to edit</b>', cell_k('cell', nr, nc))
        return

    if d.startswith('cell:'):
        parts = d.split(':')
        r, c = int(parts[1]), int(parts[2])
        if 0 <= r < nr and 0 <= c < nc:
            text, link = parse_cell(rows[r][c])
            s['await'] = {'type': 'cell_text', 'r': r, 'c': c}
            msg(
                chat,
                f'✏️ Editing R{r + 1} C{c + 1}\n'
                f'Current Text: <code>{esc(text) or "(empty)"}</code>\n'
                f'Current Link: <code>{esc(link) or "(none)"}</code>\n\n'
                'Step 1/2: Send the new cell text. Use /empty for blank.'
            )
        else:
            msg(chat, '⚠️ Invalid cell selection.')
        return

    if d == 'edittitle':
        s['await'] = {'type': 'title'}
        msg(
            chat,
            f'✏️ Current Title: <code>{esc(t["title"]) or "(none)"}</code>\n\n'
            'Send the new title text. Use /empty to remove the title.'
        )
        return

    if d == 'ar':
        rows.append([{'text': '', 'link': ''} for _ in range(nc)])
        editor(chat, uid)
        return

    if d == 'ac':
        if nc < 20:
            for row in rows:
                row.append({'text': '', 'link': ''})
            editor(chat, uid)
        else:
            msg(chat, '⚠️ Maximum limit of 20 columns reached.')
        return

    if d == 'dr':
        if nr > 1:
            edit_text(chat, mid, '🗑 <b>Select a row to delete</b>', pick('xrow', nr, 'Row'))
        else:
            msg(chat, '⚠️ At least 1 row must remain.')
        return

    if d.startswith('xrow:'):
        idx = int(d.split(':')[1])
        if 0 <= idx < len(rows) and len(rows) > 1:
            rows.pop(idx)
        editor(chat, uid)
        return

    if d == 'dc':
        if nc > 1:
            edit_text(chat, mid, '🗑 <b>Select a column to delete</b>', pick('xcol', nc, 'Col'))
        else:
            msg(chat, '⚠️ At least 1 column must remain.')
        return

    if d.startswith('xcol:'):
        idx = int(d.split(':')[1])
        if nc > 1 and 0 <= idx < nc:
            for row in rows:
                if idx < len(row):
                    row.pop(idx)
        editor(chat, uid)
        return

    if d == 'set':
        edit_text(chat, mid, '⚙️ <b>Table settings</b>', settings_kb(t))
        return

    if d in ('tb', 'ts', 'tc'):
        key = {'tb': 'bordered', 'ts': 'striped', 'tc': 'compact'}[d]
        t[key] = not t[key]
        edit_text(chat, mid, '⚙️ <b>Table settings</b>', settings_kb(t))
        return

    if d in ('preview', 'pub'):
        p = {
            'chat_id': chat,
            'text': table_html(t),
            'parse_mode': 'HTML'
        }
        api('sendMessage', p)
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
            'Edit cells (text & hyperlink), add/delete rows and columns, '
            'change border/striped/compact, preview and publish.'
        )
        return

    if uid not in state:
        msg(chat, 'Send /newtable first.')
        return

    s = state[uid]
    if s.get('await'):
        await_info = s['await']
        await_type = await_info.get('type')

        if await_type == 'title':
            s['t']['title'] = '' if text == '/empty' else text
            s['await'] = None
            msg(chat, '✅ Title updated.')
            editor(chat, uid)
        elif await_type == 'cell_text':
            r, c = await_info['r'], await_info['c']
            if 0 <= r < len(s['t']['rows']) and 0 <= c < len(s['t']['rows'][0]):
                cell_text = '' if text == '/empty' else text
                s['await'] = {'type': 'cell_link', 'r': r, 'c': c, 'text': cell_text}
                _, current_link = parse_cell(s['t']['rows'][r][c])
                msg(
                    chat,
                    f'🔗 Step 2/2: Send the URL link for R{r + 1} C{c + 1} (e.g., https://t.me/...)\n'
                    f'Current Link: <code>{esc(current_link) or "(none)"}</code>\n\n'
                    'Use /skip to keep/leave no link, or /empty to clear.'
                )
            else:
                s['await'] = None
                msg(chat, '⚠️ Selected cell is no longer valid.')
                editor(chat, uid)
        elif await_type == 'cell_link':
            r, c = await_info['r'], await_info['c']
            cell_text = await_info['text']
            if 0 <= r < len(s['t']['rows']) and 0 <= c < len(s['t']['rows'][0]):
                _, old_link = parse_cell(s['t']['rows'][r][c])
                if text == '/skip':
                    link = old_link
                elif text == '/empty':
                    link = ''
                else:
                    link = text
                s['t']['rows'][r][c] = {'text': cell_text, 'link': link}
                s['await'] = None
                msg(chat, '✅ Cell updated.')
                editor(chat, uid)
            else:
                s['await'] = None
                msg(chat, '⚠️ Selected cell is no longer valid.')
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
