"""Saved widget arrangement for the overview and home pages, per account.

Presentation only. The browser's widget registry
(frontend/src/components/workspace/widgets.js) owns titles and default
positions; this module keeps the allow-list of widget ids so a saved layout can
only name real widgets. Reading drops ids that no longer exist, so renaming or
retiring a widget never breaks a saved layout; the browser then adds any new
widget at its default place.
"""
from psycopg.types.json import Jsonb
from .db import transaction, rows

# Keep in step with frontend/src/components/workspace/widgets.js.
WIDGETS = {
    'overview': ('signals', 'news', 'people', 'world', 'view'),
    'home': ('welcome', 'portfolio', 'companies'),
}
COLUMNS = {'lg': 12, 'md': 10, 'sm': 6}
MAX_Y = 1000
MAX_H = 400


def _page(page):
    if page not in WIDGETS:
        raise ValueError('Choose the overview or home page.')
    return WIDGETS[page]


def _whole(value, low, high):
    return type(value) is int and low <= value <= high


def _items(page, breakpoint, items):
    known = _page(page)
    columns = COLUMNS[breakpoint]
    if not isinstance(items, list) or len(items) > len(known):
        raise ValueError('That layout does not match this page.')
    seen = set()
    clean = []
    for item in items:
        if not isinstance(item, dict) or item.get('i') not in known or item['i'] in seen:
            raise ValueError('That layout names a widget this page does not have.')
        x, y, w, h = (item.get(k) for k in ('x', 'y', 'w', 'h'))
        if not (_whole(w, 1, columns) and _whole(x, 0, columns - 1) and x + w <= columns
                and _whole(y, 0, MAX_Y) and _whole(h, 1, MAX_H)):
            raise ValueError('A widget is placed outside the page.')
        seen.add(item['i'])
        clean.append({'i': item['i'], 'x': x, 'y': y, 'w': w, 'h': h})
    return clean


def _hidden(page, hidden):
    known = _page(page)
    if (not isinstance(hidden, list) or len(set(map(str, hidden))) != len(hidden)
            or any(i not in known for i in hidden)):
        raise ValueError('Choose widgets this page has to hide.')
    return list(hidden)


def validate(page, body):
    """The body saved for a page: {lg, md, sm, hidden}, each checked."""
    _page(page)
    if not isinstance(body, dict) or set(body) - {*COLUMNS, 'hidden'}:
        raise ValueError('That layout does not match this page.')
    layouts = {bp: _items(page, bp, body[bp]) for bp in COLUMNS if body.get(bp) is not None}
    if not layouts:
        raise ValueError('Save at least one screen width.')
    return layouts, _hidden(page, body.get('hidden') or [])


def reconcile(page, saved):
    """Drop retired widget ids and impossible positions from a stored layout."""
    known = _page(page)
    result = {bp: None for bp in COLUMNS}
    hidden = []
    for row in saved:
        bp = row['breakpoint']
        if bp not in COLUMNS:
            continue
        kept = []
        for item in row['layout'] if isinstance(row['layout'], list) else []:
            try:
                clean, = _items(page, bp, [item])
            except ValueError:
                continue
            # A widget listed twice keeps its first position.
            if all(k['i'] != clean['i'] for k in kept):
                kept.append(clean)
        result[bp] = kept
        hidden = hidden or [i for i in (row['hidden'] or []) if i in known]
    result['hidden'] = list(dict.fromkeys(hidden))
    result['saved'] = any(result[bp] is not None for bp in COLUMNS)
    return result


def read(owner, page):
    _page(page)
    with transaction(owner, consistent=True) as conn:
        saved = rows(conn, 'SELECT breakpoint,layout,hidden FROM workspace_layouts '
                     'WHERE owner_id=%s AND page=%s ORDER BY breakpoint', (owner, page))
    return reconcile(page, saved)


def save(owner, page, body):
    layouts, hidden = validate(page, body)
    with transaction(owner) as conn:
        for bp, items in layouts.items():
            conn.execute(
                '''INSERT INTO workspace_layouts(owner_id,page,breakpoint,layout,hidden)
                   VALUES(%s,%s,%s,%s,%s)
                   ON CONFLICT(owner_id,page,breakpoint) DO UPDATE
                   SET layout=EXCLUDED.layout,hidden=EXCLUDED.hidden,updated_at=now()''',
                (owner, page, bp, Jsonb(items), Jsonb(hidden)))
        # Hiding applies at every width, including ones not saved yet.
        conn.execute('UPDATE workspace_layouts SET hidden=%s WHERE owner_id=%s AND page=%s',
                     (Jsonb(hidden), owner, page))
    return read(owner, page)


def reset(owner, page):
    _page(page)
    with transaction(owner) as conn:
        conn.execute('DELETE FROM workspace_layouts WHERE owner_id=%s AND page=%s', (owner, page))
    return read(owner, page)
