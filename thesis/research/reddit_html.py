"""Small public-page Reddit collector. No hidden APIs or access fallback.

Only rendered post/comment elements are read. Missing markup is a coverage
failure, never an empty-success sample. Live transport retains the shared Reddit
denial/pacing controls. HTML fixtures exercise parsing, not live availability.
"""
import hashlib
import re
from datetime import datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urlsplit

from thesis.providers.settings import settings
from thesis.config import DATA, ROOT
from . import social
from .catalogue import company_alias

METHOD = 'reddit-public-html-1'
MAX_POSTS = 20
MAX_THREADS = 3
MAX_COMMENTS = 12
ITEM_TAGS = {'shreddit-post', 'shreddit-comment'}
VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


class Node:
    def __init__(self, tag, attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def own_nodes(self):
        for child in self.children:
            if not isinstance(child, Node) or child.tag in ITEM_TAGS | {'script', 'style', 'template'}:
                continue
            yield child
            yield from child.own_nodes()

    def text(self):
        parts = []
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag not in ITEM_TAGS | {'script', 'style', 'template'}:
                parts.append(child.text())
        return ' '.join(' '.join(parts).split())


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root')
        self.stack = [self.root]
        self.items = []
        self.count = 0

    def handle_starttag(self, tag, attrs):
        self.count += 1
        if self.count > 30_000 or len(self.stack) > 120:
            raise ValueError('Reddit HTML exceeded its structural reading limit.')
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag in ITEM_TAGS and not any(n.tag in {'script', 'template'} for n in self.stack):
            self.items.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, value):
        self.stack[-1].children.append(value)


def page(content):
    if not isinstance(content, bytes) or len(content) > 2_000_000:
        raise ValueError('Reddit HTML exceeded its byte limit or was not a page.')
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError('Reddit HTML did not contain readable UTF-8.') from None
    result = Page()
    result.feed(text)
    result.close()
    # A CAPTCHA/login shell or changed layout must not erase usable coverage.
    if not result.items:
        raise ValueError('Reddit HTML contained no readable post or comment elements. Access, an empty search, or changed page markup may be responsible; coverage is unverified.')
    return result


def permalink(value, *, comment=False):
    if not isinstance(value, str):
        raise ValueError('Reddit HTML has no source link.')
    if value.startswith('/') and not value.startswith('//'):
        value = 'https://www.reddit.com' + value
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or parsed.netloc != 'www.reddit.com' or parsed.query or parsed.fragment:
        raise ValueError('Reddit HTML has an unsupported source link.')
    pattern = r'/r/([A-Za-z0-9_]+)/comments/([a-z0-9]+)/([A-Za-z0-9_-]+)/'
    if comment:
        pattern += r'([a-z0-9]+)/'
    match = re.fullmatch(pattern, parsed.path.rstrip('/') + '/')
    if not match:
        raise ValueError('Reddit HTML has an unsupported thread link.')
    return value.rstrip('/') + '/', match


def date(node):
    value = node.attrs.get('created-timestamp')
    if not value:
        value = next((n.attrs.get('datetime') if n.tag == 'time' else n.attrs.get('ts')
                      for n in node.own_nodes() if (n.tag == 'time' and n.attrs.get('datetime')) or
                      (n.tag == 'faceplate-timeago' and n.attrs.get('ts'))), None)
    if not value:
        raise ValueError('Reddit HTML has no original publication date.')
    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('Reddit HTML has no aware publication date.')
    return value


def body(node):
    # Explicit own-body slots, never the complete card or a nested reply tree.
    own = list(node.own_nodes())
    slots = {'text-body'} if node.tag == 'shreddit-post' else {'comment', 'text-body'}
    match = next((n for n in own if n.attrs.get('slot') in slots), None)
    if match is None:
        match = next((n for n in own if (n.attrs.get('id') or '').endswith('-rtjson-content')), None)
    return match.text() if match else ''


def record(node, now, days, enabled, *, is_comment=False):
    key = node.attrs.get('thingid') or node.attrs.get('id')
    prefix = 't1_' if is_comment else 't3_'
    if not isinstance(key, str) or not re.fullmatch(prefix + '[a-z0-9]+', key):
        raise ValueError('Reddit HTML has no original item identity.')
    url, match = permalink(node.attrs.get('permalink'), comment=is_comment)
    feed = match[1].lower()
    if feed not in enabled or (is_comment and match[4] != key[3:]) or (not is_comment and match[2] != key[3:]):
        raise ValueError('Reddit HTML source and item identities disagree.')
    published = date(node)
    if now.tzinfo is None or not now - timedelta(days=days) <= published <= now:
        raise ValueError('Reddit HTML item is outside the requested window.')
    text = body(node)
    title = 'Reddit comment' if is_comment else node.attrs.get('post-title') or next((n.text() for n in node.own_nodes() if n.attrs.get('slot') == 'title' or n.tag == 'h1'), '')
    title = ' '.join(title.split())
    if not title or len(title) > 600 or len(text) > 12000 or (is_comment and not text):
        raise ValueError('Reddit HTML item has no usable bounded text.')
    if text in {'[removed]', '[deleted]'} or node.attrs.get('author') == 'AutoModerator' or ('is-truncated' in node.attrs and node.attrs['is-truncated'] not in {'false', '0'}):
        raise ValueError('Reddit HTML item is removed, automated, or truncated.')
    author = node.attrs.get('author')
    return dict(post_key=key, feed=feed, title=title, body=text, url=url, published_at=published,
                author_hash=hashlib.sha256(('reddit:' + author).encode()).hexdigest() if author and author != '[deleted]' else None,
                content_hash=hashlib.sha256((title + '\n' + text).encode()).hexdigest())


def search_posts(content, now, days, enabled):
    result, excluded, seen = [], 0, set()
    for node in (n for n in page(content).items if n.tag == 'shreddit-post'):
        if len(result) >= MAX_POSTS:
            break
        try:
            post = record(node, now, days, enabled)
            if post['post_key'] not in seen:
                result.append(post)
                seen.add(post['post_key'])
        except (ValueError, TypeError):
            excluded += 1
    if not result:
        raise ValueError('Reddit HTML contained no usable dated posts in the selected window. Coverage remains unverified.')
    return result, excluded


def replies(content, post, now, days):
    document = page(content)
    parent_node = next((n for n in document.items if n.tag == 'shreddit-post' and (n.attrs.get('thingid') or n.attrs.get('id')) == post['post_key']), None)
    if parent_node is None:
        raise ValueError('Reddit HTML thread did not contain the discovered post.')
    if body(parent_node) in {'[removed]', '[deleted]'} and permalink(parent_node.attrs.get('permalink'))[0] == post['url']:
        return [], [post['post_key']]
    parent = record(parent_node, now, days, [post['feed']])
    # Title, body and timestamp must all match the discovered version.
    if parent['content_hash'] != post['content_hash'] or parent['published_at'] != post['published_at'] or parent['url'] != post['url']:
        raise ValueError('Reddit HTML thread changed since discovery; refresh its source version.')
    if not any(n.tag == 'shreddit-comment' for n in document.items) and parent_node.attrs.get('comment-count') != '0':
        raise ValueError('Reddit HTML thread contained no readable comments and no verified zero count. Its discussion coverage is unverified.')
    comments, contexts, removed = [], {}, []
    contexts[post['post_key']] = dict(parent_key=post['post_key'], parent_type='story', title=post['title'], body=post['body'], url=post['url'], published_at=post['published_at'])
    pending, seen, scanned = [], set(), 0
    for node in (n for n in document.items if n.tag == 'shreddit-comment'):
        if scanned >= MAX_COMMENTS:
            break
        scanned += 1
        try:
            if body(node) in {'[removed]', '[deleted]'}:
                key = node.attrs.get('thingid') or node.attrs.get('id')
                _, link = permalink(node.attrs.get('permalink'), comment=True)
                if isinstance(key, str) and key == 't1_' + link[4] and link[1].lower() == post['feed'] and link[2] == post['post_key'][3:]:
                    removed.append(key)
                continue
            comment = record(node, now, days, [post['feed']], is_comment=True)
            if permalink(comment['url'], comment=True)[1][2] != post['post_key'][3:] or comment['published_at'] < post['published_at']:
                continue
            parent_key = node.attrs.get('parentid')
            ancestor = node.parent
            while ancestor and ancestor.tag not in ITEM_TAGS:
                ancestor = ancestor.parent
            inherited = (ancestor.attrs.get('thingid') or ancestor.attrs.get('id')) if ancestor else None
            if inherited and parent_key and inherited != parent_key:
                continue
            parent_key = parent_key or inherited
            if not parent_key or not re.fullmatch(r't[13]_[a-z0-9]+', parent_key) or comment['post_key'] in seen or parent_key == comment['post_key']:
                continue
            seen.add(comment['post_key'])
            pending.append((comment, parent_key))
            contexts[comment['post_key']] = dict(parent_key=comment['post_key'], parent_type='comment', title=comment['title'], body=comment['body'], url=comment['url'], published_at=comment['published_at'])
        except (ValueError, TypeError):
            continue
    parents = {comment['post_key']: parent_key for comment, parent_key in pending}
    for comment, parent_key in pending:
        context = contexts.get(parent_key)
        if not context or len(context['body']) > 6000 or context['published_at'] > comment['published_at']:
            continue
        chain, current = {comment['post_key']}, parent_key
        while current != post['post_key']:
            if current in chain or current not in parents:
                break
            chain.add(current)
            current = parents[current]
        if current != post['post_key']:
            continue
        comment.update(parent=context, thread_key=post['post_key'])
        comments.append(comment)
    return comments, removed


def fetch(kind, company, days, post=None, feeds=social.FEEDS):
    from .reddit_research import request
    values = settings()
    if values.get('THESIS_LIVE_DATA_ENABLED') != 'true' or values.get('THESIS_REDDIT_HTML_ENABLED') != 'true':
        raise ValueError('Reddit HTML collection is switched off. Its live access is unverified; enable it only after reviewing the recorded Reddit denial.')
    if DATA.resolve() != (ROOT / '.local').resolve():
        raise ValueError('Reddit HTML live requests are disabled in isolated workspaces.')
    if kind == 'search':
        alias = company_alias(company['name'])
        query = f'"{company["symbol"]}"' + (f' OR "{alias}"' if alias else '')
        return request('https://www.reddit.com/r/' + '+'.join(feeds) + '/search/',
                       dict(q=query, restrict_sr='on', sort='new', t={1:'day', 7:'week', 30:'month'}[days]), html_page=True)
    if kind == 'comments' and post:
        return request(permalink(post['url'])[0], html_page=True)
    raise ValueError('Unsupported Reddit HTML collection step.')
