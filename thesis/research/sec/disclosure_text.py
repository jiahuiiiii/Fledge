"""Read untrusted filing HTML without executing it or inventing table values."""
import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

METHOD = 'sec-original-disclosures-1'
MAX_TEXT = 2_000_000
BLOCKS = {'p','div','tr','li','h1','h2','h3','h4','h5','h6','br','hr','section'}
SKIP = {'script','style','noscript','ix:hidden','ix:header','xbrli:context','xbrli:unit','link:schemaref'}


class FilingHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.links=[]
        self.stack=[]
        self.ignored=0
        self.anchor=None

    def boundary(self):
        if self.parts and self.parts[-1]!='\n':self.parts.append('\n')

    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        hidden=tag in SKIP or 'hidden' in attrs or bool(re.search(r'display\s*:\s*none|visibility\s*:\s*hidden',attrs.get('style',''),re.I))
        if tag not in {'br','hr','meta','link','img','input','wbr','source','area','base','embed','param','col'}:
            self.stack.append((tag,hidden))
            if hidden:self.ignored+=1
        if self.ignored:return
        if tag in BLOCKS:self.boundary()
        elif tag in {'td','th'}:self.parts.append(' | ')
        if tag=='a':self.anchor=(attrs.get('href',''),[])

    def handle_endtag(self,tag):
        if not self.ignored:
            if tag in BLOCKS:self.boundary()
            if tag=='a' and self.anchor:
                self.links.append((self.anchor[0],''.join(self.anchor[1]).strip()))
                self.anchor=None
        # HTML can omit closing td/tr tags. Pop through the matching start,
        # rather than treating an unrelated closing tag as the end of hidden data.
        match=next((i for i in range(len(self.stack)-1,-1,-1) if self.stack[i][0]==tag),None)
        if match is not None:
            self.ignored-=sum(hidden for _,hidden in self.stack[match:])
            del self.stack[match:]

    def handle_data(self,text):
        if not self.ignored:
            self.parts.append(text)
            if self.anchor:self.anchor[1].append(text)


def parse(raw, *, form, cik):
    if len(raw)>20*1024*1024:raise ValueError('Filing exceeds the supported size.')
    html=raw.decode('utf-8-sig',errors='strict')
    if not re.search(r'<(?:html|body|div|p|table)\b',html,re.I):
        raise ValueError('The filing did not contain readable HTML.')
    identifiers=re.findall(r'<(?:\w+:)?identifier\b[^>]*scheme=["\'][^"\']*sec\.gov/CIK[^"\']*["\'][^>]*>\s*0*(\d+)\s*</',html,re.I)
    if identifiers and {int(value) for value in identifiers}!={int(cik)}:
        raise ValueError('The original filing belongs to another issuer.')
    reader=FilingHTML();reader.feed(html);reader.close()
    lines=[re.sub(r'\s+',' ',part).strip(' |') for part in ''.join(reader.parts).splitlines()]
    lines=[line for line in lines if line]
    body='\n'.join(lines)
    if len(body)<200 or len(body)>MAX_TEXT:
        raise ValueError('The filing text is missing or exceeds the supported size.')
    if re.search(r'undeclared automated tool|request rate threshold exceeded|your request originates from an',body,re.I):
        raise ValueError('SEC returned an access page rather than a filing.')
    passages=[];position=0
    for i,line in enumerate(lines):
        passages.append(dict(id=f'p{i+1}',quote=line,start=position,end=position+len(line)))
        position+=len(line)+1
    # Repeated table-of-contents headings are retained as text, but the longer
    # substantive interval wins. No unsupported section is invented.
    headings=[]
    for i,line in enumerate(lines):
        match=re.match(r'^item\s+(\d+[a-z]?)\s*[.\-:–—]?\s*(.*)$',line,re.I)
        if match and len(line)<200 and not re.search(r'\bitem\s+\d',match[2],re.I):
            headings.append((i,match[1].upper()))
    sections={}
    titles={'1':'Business','1A':'Risk factors','7':'Management discussion','8':'Financial statements and notes'} if form.startswith('10-K') else {'1':'Financial statements','1A':'Risk factors','2':'Management discussion'} if form.startswith('10-Q') else {}
    for j,(start,item) in enumerate(headings):
        end=headings[j+1][0] if j+1<len(headings) else len(lines)
        length=sum(len(line) for line in lines[start:end])
        if item in titles and length>=500 and length>sections.get(item,{}).get('characters',0):
            sections[item]=dict(title=titles[item],first_passage=f'p{start+1}',last_passage=f'p{end}',characters=length)
    return dict(method=METHOD,body=body,passages=passages,sections=list(sections.values()),
                text_hash=hashlib.sha256(body.encode()).hexdigest(),links=reader.links,
                limitations=['Text is extracted from the retained original HTML; table cells are separated with |.',
                             'Section detection is best effort. Unrecognized sections remain in the full text.',
                             'Publication time is the filing acceptance time, not a separately verified earnings-announcement time.'])


def archive_url(cik, accession, filename):
    if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',accession) or not re.fullmatch(r'[A-Za-z0-9_.-]+\.html?',filename,re.I):
        raise ValueError('Unsupported SEC filing identity or document name.')
    if filename.startswith('.') or '..' in filename:raise ValueError('Unsupported filing path.')
    return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/{filename}'


def exhibits(data, url):
    """Only explicit Exhibit 99 links within this exact issuer/accession."""
    root=url.rsplit('/',1)[0]+'/'
    links=[]
    for href,label in data['links']:
        if not re.search(r'ex(?:hibit)?[\s._-]*99|(?:^|[_.-])ex99',label+' '+href,re.I):continue
        candidate=urljoin(url,href);parsed=urlsplit(candidate)
        if parsed.scheme!='https' or parsed.netloc!='www.sec.gov' or parsed.query or parsed.fragment or parsed.username or parsed.password:continue
        if not candidate.startswith(root) or '/' in candidate[len(root):]:continue
        filename=candidate[len(root):]
        if re.fullmatch(r'[A-Za-z0-9_.-]+\.html?',filename,re.I) and '..' not in filename and candidate not in links:
            links.append(candidate)
    return links[:2]
