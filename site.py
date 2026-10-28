#!/usr/bin/env python3
"""GDOG: dependency-free static publishing. Only dist/ is public output."""
import argparse
import datetime as dt
import hashlib
import html
import http.server
import json
import re
import shutil
import threading
import time
from pathlib import Path
from urllib.parse import urlparse
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT = Path(__file__).resolve().parent
BASE = 'https://testgeigei.github.io/engineering-notes'
REPO = 'https://github.com/testgeigei/engineering-notes'
NAME = 'GDOG 工程手记'
DESCRIPTION = '把日常开发里的小问题，写成能照着做的笔记。Git、命令行、Web 基础与轻量工具。'

def esc(text):
    return html.escape(str(text), quote=True)

def inline(text):
    slots = []
    def code(m):
        slots.append('<code>' + esc(m[1]) + '</code>')
        return f'\x00{len(slots)-1}\x00'
    text = re.sub(r'`([^`]+)`', code, text)
    text = esc(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', r'<a href="\2" rel="noopener noreferrer">\1</a>', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: slots[int(m[1])], text)

def markdown(text):
    out, toc, para, code, listing = [], [], [], None, False
    def flush():
        if para:
            out.append('<p>' + inline(' '.join(para)) + '</p>')
            para.clear()
    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            if listing:
                out.append('</ul>'); listing = False
            if code is None: code = []
            else:
                out.append('<pre><code>' + esc('\n'.join(code)) + '</code></pre>'); code = None
            continue
        if code is not None:
            code.append(line); continue
        if not line.strip():
            flush()
            if listing: out.append('</ul>'); listing = False
        elif line.startswith(('## ', '### ')):
            flush()
            if listing: out.append('</ul>'); listing = False
            level = 3 if line.startswith('### ') else 2
            title = line[level+1:]; anchor = f'section-{len(toc)+1}'
            toc.append((anchor, title)); out.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>')
        elif line.startswith('- '):
            flush()
            if not listing: out.append('<ul>'); listing = True
            out.append('<li>' + inline(line[2:]) + '</li>')
        else:
            if listing: out.append('</ul>'); listing = False
            para.append(line)
    flush()
    if listing: out.append('</ul>')
    if code is not None: raise ValueError('Unclosed fenced code block')
    return '\n'.join(out), toc

def validate(articles):
    if not isinstance(articles, list) or not articles: raise ValueError('articles must be a nonempty list')
    ids, titles, bodies = set(), set(), set()
    for a in articles:
        for field in ['id','title','summary','category','date','updated','body','sources']:
            if not a.get(field): raise ValueError(f'Missing {field}')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', a['id']): raise ValueError('Unsafe article id')
        if a['id'] in ids or a['title'] in titles: raise ValueError('Duplicate article')
        digest = hashlib.sha256(a['body'].encode()).hexdigest()
        if digest in bodies: raise ValueError('Duplicate body')
        ids.add(a['id']); titles.add(a['title']); bodies.add(digest)
        if len(a['body']) < 300: raise ValueError(f'Thin article: {a["id"]}')
        if len(a['summary']) > 180: raise ValueError('Summary too long')
        published = dt.date.fromisoformat(a['date']); updated = dt.date.fromisoformat(a['updated'])
        if published > dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date() or updated < published:
            raise ValueError('Invalid publication date')
        if not isinstance(a['sources'], list): raise ValueError('Sources must be list')
        for s in a['sources']:
            u = urlparse(s['url'])
            if u.scheme != 'https' or not u.netloc or u.username or u.password: raise ValueError('Unsafe source URL')
        if re.search(r'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_|-----BEGIN .*PRIVATE KEY|/Users/hellcat|Bearer [A-Za-z0-9]{16,}', a['body']):
            raise ValueError('Potential private material')
        markdown(a['body'])
    return articles

def load():
    return validate(json.loads((ROOT/'articles.json').read_text()))

def minutes(a):
    return max(2, round(len(a['body'])/380))

def card(a, prefix=''):
    search = ' '.join([a['title'],a['summary'],a['category'],a['body']]).lower()
    return f'''<a class="card" href="{prefix}notes/{a['id']}/" data-article data-category="{esc(a['category'])}" data-search="{esc(search)}"><span class="tag">{esc(a['category'])}</span><h3>{esc(a['title'])}</h3><p>{esc(a['summary'])}</p><span class="meta"><span>{a['updated']} · {minutes(a)} 分钟</span><span aria-hidden="true">↗</span></span></a>'''

def layout(title, body, path='', description=DESCRIPTION, active='', article=None, absolute=False):
    depth = len([x for x in path.split('/') if x])
    prefix = BASE+'/' if absolute else '../'*depth
    url = BASE + '/' + (path.rstrip('/')+'/' if path else '')
    nav = ''.join(f'<a href="{prefix}{route}" '+('aria-current="page"' if active==name else '')+f'>{name}</a>' for name, route in [('笔记','notes/'),('工具箱','tools/'),('资源','resources/'),('关于','about/')])
    schema = {'@context':'https://schema.org','@type':'WebSite','name':NAME,'url':BASE+'/'}
    if article:
        schema = {'@context':'https://schema.org','@type':'TechArticle','headline':article['title'],'description':article['summary'],'datePublished':article['date'],'dateModified':article['updated'],'author':{'@type':'Organization','name':NAME,'url':BASE+'/about/'},'mainEntityOfPage':url,'inLanguage':'zh-CN'}
    schema_text = json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c')
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · {NAME}</title><meta name="description" content="{esc(description)}"><meta name="theme-color" content="#24342b"><meta name="referrer" content="strict-origin-when-cross-origin"><link rel="canonical" href="{url}"><meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{url}"><meta property="og:site_name" content="{NAME}"><meta property="og:image" content="{BASE}/social-card.svg"><meta name="twitter:card" content="summary"><link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml"><link rel="alternate" type="application/rss+xml" title="{NAME}" href="{prefix}feed.xml"><link rel="stylesheet" href="{prefix}site.css"><script defer src="{prefix}site.js"></script><script type="application/ld+json">{schema_text}</script></head><body><a class="skip" href="#main">跳到正文</a><header class="top"><div class="wrap"><nav class="nav" aria-label="主导航"><a class="brand" href="{prefix or './'}"><span class="brand-mark">g.</span><span>GDOG 工程手记</span></a><div class="nav-links">{nav}<a class="pill" href="{REPO}">GitHub ↗</a></div></nav></div></header><main id="main" class="wrap">{body}</main><footer class="footer"><div class="wrap"><div>GDOG / 少一点重复摸索，多一点可复用的办法。<br>© 2026 · 开源笔记与浏览器工具</div><div class="footer-links"><a href="{prefix}feed.xml">RSS 订阅</a><a href="{REPO}/issues">纠错与建议</a><a href="{prefix}about/">编辑说明</a></div></div></footer></body></html>'''

TOOLS = '''<div class="page-head"><div class="eyebrow">SMALL TOOLS / 大有用处</div><h1>打开就能用的工具箱。</h1><p>处理眼前的小问题，然后继续你的工作。所有输入都在当前浏览器处理，不上传到服务器。</p></div><div class="tool-grid">
<section class="tool"><h2>01 / JSON 整理</h2><p>检查语法、格式化或压缩。大整数可能被 JavaScript 四舍五入，精确标识符请使用字符串。</p><label for="json-input">JSON 内容</label><textarea id="json-input" spellcheck="false">{"project":"GDOG","readable":true,"tags":["notes","tools"]}</textarea><button id="json-format">格式化</button><button id="json-minify" class="secondary">压缩</button><button id="json-copy" class="secondary">复制</button><output id="json-output" aria-live="polite">等待检查。</output></section>
<section class="tool"><h2>02 / 时间戳转换</h2><p>明确选择秒或毫秒，避免把不同单位当成同一个时间。</p><label for="time-input">时间戳或带时区的 ISO 日期</label><input id="time-input" value="1767225600" autocomplete="off"><label for="time-unit">数字输入单位</label><select id="time-unit"><option value="seconds">Unix 秒</option><option value="milliseconds">Unix 毫秒</option></select><button id="time-convert">转换</button><button id="time-now" class="secondary">当前时间</button><output id="time-output" aria-live="polite">结果会同时显示 UTC、本地时间和两种时间戳。</output></section>
<section class="tool"><h2>03 / URL 拆解</h2><p>查看协议、主机、路径和查询参数。保留重复参数，不发起网络请求。</p><label for="url-input">HTTP / HTTPS 地址</label><textarea id="url-input" spellcheck="false">https://example.com/search?q=hello%20world&amp;tag=git&amp;tag=web#results</textarea><button id="url-parse">解析地址</button><output id="url-output" aria-live="polite">等待解析。</output></section>
<section class="tool"><h2>04 / SHA-256 文本指纹</h2><p>计算 UTF-8 文本的摘要。换行和空格都会影响结果；摘要不等于加密。</p><label for="hash-input">原始文本</label><textarea id="hash-input" spellcheck="false">hello world</textarea><button id="hash-run">计算 SHA-256</button><button id="hash-copy" class="secondary">复制结果</button><output id="hash-output" aria-live="polite">需要 HTTPS 安全上下文。</output></section></div><p class="note">隐私设计：无第三方脚本、无输入内容上传、无浏览器本地持久化。请勿把真实密码或访问令牌粘贴到任何不受信任的工具里。</p>'''

def build(out=None, base=None):
    global BASE
    if base: BASE = base.rstrip('/')
    articles = sorted(load(), key=lambda a:(a['updated'],a['date']), reverse=True)
    resources = json.loads((ROOT/'resources.json').read_text())
    dest = Path(out or ROOT/'dist'); dest.mkdir(parents=True,exist_ok=True)
    paths = []
    def write(path, content):
        target=dest/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content,encoding='utf-8');paths.append(path)
    a=articles[0]
    home=f'''<section class="hero"><div><div class="eyebrow"><span class="dot"></span> BUILD SMALL. UNDERSTAND DEEPLY.</div><h1>把问题拆小，<br>把方法<em>留下来。</em></h1><p>{DESCRIPTION}</p><div class="actions"><a class="button" href="notes/">开始阅读 <span aria-hidden="true">　↗</span></a><a class="button secondary" href="tools/">打开工具箱</a></div></div><div class="terminal" aria-label="GDOG 内容方向"><div class="terminal-bar"><span class="lights">● ● ●</span><span>field-notes / README</span></div><pre><span class="green">$ cat philosophy.txt</span>\n\n01  先理解，再复制。\n02  例子要小，步骤要清楚。\n03  留下来源，也留下方法。\n\n<span class="green">→ less noise, more signal.</span></pre></div></section><div class="metrics"><div><strong>{len(articles):02d}</strong><span>篇实用笔记</span></div><div><strong>04</strong><span>个本地小工具</span></div><div><strong>{len(resources):02d}</strong><span>份精选资料</span></div></div><div class="section-head"><h2>从这一篇开始</h2><a href="notes/">全部笔记 ↗</a></div><a class="feature" href="notes/{a['id']}/"><div class="feature-copy"><span class="tag">FEATURED / {esc(a['category'])}</span><h2>{esc(a['title'])}</h2><p>{esc(a['summary'])}</p><span class="meta">{a['updated']} · {minutes(a)} 分钟阅读　↗</span></div><div class="feature-art" aria-hidden="true"><div class="diagram"><span>一个明确的问题</span><b>↓</b><span>一个最小可运行的例子</span><b>↓</b><span>一个可复用的方法 ✓</span></div></div></a><div class="section-head"><h2>最近整理</h2><p>技术细节，慢慢讲清楚。</p></div><div class="grid">{''.join(card(x) for x in articles[1:7])}</div><section class="tool-banner"><div><span class="tag" style="color:#bbd5ad">BROWSER-LOCAL TOOLBOX</span><h2>小工具，用完就走。</h2><p>JSON、时间戳、URL、SHA-256。无需登录，输入留在浏览器。</p></div><a class="button" href="tools/">试试工具箱 ↗</a></section>'''
    write('index.html',layout('把问题拆小，把方法留下来',home))
    cats=sorted({x['category'] for x in articles})
    filters=''.join(f'<button class="filter" type="button" data-filter="{esc(c)}" aria-pressed="{str(c=="全部").lower()}">{esc(c)}</button>' for c in ['全部']+cats)
    notes=f'''<div class="page-head"><div class="eyebrow">THE NOTEBOOK</div><h1>一个问题，一篇笔记。</h1><p>从具体场景出发，解释原因，再给出能用的步骤。</p></div><div class="searchbar"><label class="sr" for="search">搜索笔记</label><input id="search" type="search" placeholder="试试：Git、缓存、时间戳…" autocomplete="off"></div><div class="filters" aria-label="专题筛选">{filters}</div><p id="result-count" role="status">共 {len(articles)} 篇笔记</p><div class="grid">{''.join(card(x,'../') for x in articles)}</div><div id="empty" class="empty" hidden>没有匹配的笔记。换个词，或选择“全部”。</div>'''
    write('notes/index.html',layout('全部笔记',notes,'notes',active='笔记'))
    for a in articles:
        content,toc=markdown(a['body'])
        source_links=''.join(f'<li><a href="{esc(s["url"])}" rel="noopener noreferrer">{esc(s["title"])}</a></li>' for s in a['sources'])
        related=[x for x in articles if x['id']!=a['id'] and x['category']==a['category']][:3]
        if len(related)<3: related += [x for x in articles if x['id']!=a['id'] and x not in related][:3-len(related)]
        body=f'''<div class="breadcrumb"><a href="../../">首页</a> / <a href="../">笔记</a> / {esc(a['category'])}</div><div class="page-head"><div class="eyebrow">{esc(a['category'])}</div><h1>{esc(a['title'])}</h1><p>{esc(a['summary'])}</p></div><div class="article-meta"><span>{NAME}</span><span>发布 {a['date']}</span><span>更新 {a['updated']}</span><span>约 {minutes(a)} 分钟</span></div><div class="article-layout"><article><div class="prose">{content}</div><aside class="sources"><strong>继续查阅</strong><ul>{source_links}</ul></aside><div class="article-actions"><a href="{REPO}/issues/new">报告错误 ↗</a><a href="../../feed.xml">订阅后续笔记 ↗</a><a href="../../tools/">打开工具箱 ↗</a></div></article><aside class="toc" aria-label="文章目录"><strong>ON THIS PAGE</strong>{''.join(f'<a href="#{anchor}">{esc(t)}</a>' for anchor,t in toc)}</aside></div><section class="related"><div class="section-head"><h2>接着读</h2><a href="../">全部笔记 ↗</a></div><div class="grid">{''.join(card(x,'../../') for x in related)}</div></section>'''
        write(f'notes/{a["id"]}/index.html',layout(a['title'],body,f'notes/{a["id"]}',a['summary'],'笔记',a))
    write('tools/index.html',layout('浏览器工具箱',TOOLS,'tools',active='工具箱'))
    resource_body='<div class="page-head"><div class="eyebrow">REFERENCE SHELF</div><h1>把好资料放在手边。</h1><p>优先指向维护者的一手文档。每一条都说明适合解决什么问题。</p></div>'
    for category in sorted({r['category'] for r in resources}):
        resource_body+=f'<div class="section-head"><h2>{esc(category)}</h2></div>'
        for r in resources:
            if r['category']==category: resource_body+=f'<a class="resource" href="{esc(r["url"])}" rel="noopener noreferrer"><strong>{esc(r["title"])} ↗</strong><p>{esc(r["description"])}</p><small>{esc(urlparse(r["url"]).netloc)}</small></a>'
    write('resources/index.html',layout('精选开发资料',resource_body,'resources',active='资源'))
    about='''<div class="page-head"><div class="eyebrow">ABOUT THE NOTEBOOK</div><h1>写给正在动手的人。</h1><p>GDOG 是一本公开维护的工程手记。我们把开发中的小问题整理成短教程、可复用的例子和轻量工具。</p></div><div class="prose about"><h2>内容从哪里来</h2><p>笔记围绕官方文档和可检查的示例编写。AI 辅助资料整理与初稿生成，发布前检查来源、示例与表达。我们不编造使用经历、测试成绩或产品评价。</p><h2>怎么读</h2><p>遇到具体问题，从笔记搜索开始。需要整理 JSON、拆解 URL 或转换时间戳，可以直接使用工具箱。资源目录保留一手文档，方便你继续深入。</p><h2>隐私与维护</h2><p>工具输入只在当前浏览器处理，不上传、不持久化。站点没有第三方分析脚本。托管服务仍可能记录正常访问日志。公开反馈请先移除令牌、密码和个人信息。</p><h2>订阅与贡献</h2><p>你可以订阅 RSS，或者在 GitHub 提交纠错和选题建议。有实质变化时更新文章日期；不会通过反复更换日期制造新文章。</p><h2>许可</h2><p>本站原创程序使用 MIT 许可，原创文章使用 CC BY 4.0。第三方文档和商标归原权利人所有。转载文章请标明来源并保留链接。</p></div>'''
    write('about/index.html',layout('关于与编辑说明',about,'about',active='关于'))
    write('404.html',layout('没有找到这页','<div class="page-head"><div class="eyebrow">404 / PAGE NOT FOUND</div><h1>这一页没有找到。</h1><p>地址可能改变了，试试从笔记目录重新查找。</p><a class="button" href="'+BASE+'/notes/">浏览全部笔记</a></div>', absolute=True))
    write('favicon.svg','<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="#24342b"/><text x="13" y="45" font-size="42" font-family="monospace" fill="#f5f4ee">g.</text></svg>')
    write('social-card.svg','<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"><rect width="1200" height="630" fill="#24342b"/><text x="90" y="160" fill="#b7dc8b" font-family="monospace" font-size="28">GDOG / ENGINEERING NOTES</text><text x="90" y="310" fill="#f5f4ee" font-family="sans-serif" font-size="65">把问题拆小，</text><text x="90" y="405" fill="#f5f4ee" font-family="sans-serif" font-size="65">把方法留下来。</text><text x="90" y="535" fill="#b7c6b8" font-family="sans-serif" font-size="26">Git · Web · 命令行 · 浏览器工具</text></svg>')
    for asset in ['site.css','site.js']:shutil.copyfile(ROOT/asset,dest/asset)
    write('.nojekyll','')
    write('robots.txt',f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    sitemap=Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for path in paths:
        if not path.endswith('index.html'):continue
        item=SubElement(sitemap,'url');SubElement(item,'loc').text=BASE+'/'+path.removesuffix('index.html')
        aid=path.split('/')[1] if path.startswith('notes/') and path.count('/')==2 else None
        if aid:SubElement(item,'lastmod').text=next(a['updated'] for a in articles if a['id']==aid)
    write('sitemap.xml',tostring(sitemap,encoding='unicode',xml_declaration=True))
    rss=Element('rss',version='2.0');channel=SubElement(rss,'channel')
    for key,value in [('title',NAME),('link',BASE+'/'),('description',DESCRIPTION),('language','zh-CN')]:SubElement(channel,key).text=value
    for a in articles[:30]:
        item=SubElement(channel,'item'); url=BASE+'/notes/'+a['id']+'/'
        for key,value in [('title',a['title']),('link',url),('guid',url),('description',a['summary']),('pubDate',dt.datetime.fromisoformat(a['date']).strftime('%a, %d %b %Y 00:00:00 +0800'))]:SubElement(item,key).text=value
    write('feed.xml',tostring(rss,encoding='unicode',xml_declaration=True))
    write('search.json',json.dumps([{k:a[k] for k in ['id','title','summary','category']} for a in articles],ensure_ascii=False))
    write('manifest.json',json.dumps({'articles':len(articles),'resources':len(resources),'source_sha256':hashlib.sha256((ROOT/'articles.json').read_bytes()).hexdigest()},indent=2))
    print(f'Built {len(articles)} articles, 4 tools, {len(resources)} resources → {dest}')
    return dest

def dev(port):
    dest=build(base='http://gdog.loc')
    handler=lambda *a,**kw:http.server.SimpleHTTPRequestHandler(*a,directory=str(dest),**kw)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',port),handler)
    def watch():
        previous=None
        while True:
            signature=tuple((ROOT/name).stat().st_mtime_ns for name in ['articles.json','resources.json','site.py','site.css','site.js'])
            if previous and signature!=previous:
                try:build(base='http://gdog.loc')
                except Exception as e:print(f'Rebuild rejected: {e}')
            previous=signature;time.sleep(1)
    threading.Thread(target=watch,daemon=True).start()
    print(f'Dev listening on 127.0.0.1:{port}; fixed entrance http://gdog.loc',flush=True)
    server.serve_forever()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['build','check','dev']);p.add_argument('--out');p.add_argument('--base');p.add_argument('--port',type=int,default=4186);args=p.parse_args()
    if args.command=='build':build(args.out,args.base)
    elif args.command=='check':print(f'Validated {len(load())} articles')
    else:dev(args.port)
