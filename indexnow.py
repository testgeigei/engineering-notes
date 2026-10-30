"""Notify IndexNow after deployment. The verification identifier is public."""
import argparse
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from topics import topic_slug

ROOT = Path(__file__).resolve().parent
BASE = 'https://testgeigei.github.io/engineering-notes'
ENDPOINT = 'https://api.indexnow.org/indexnow'

def previous_file(revision, name):
    if not re.fullmatch(r'[0-9a-f]{40}', revision or '') or set(revision) == {'0'}:
        return None
    result = subprocess.run(['git', 'show', f'{revision}:{name}'], cwd=ROOT,
                            capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None

def changed_urls(current, previous=None, site_changed=False, resources_changed=False):
    current_map = {a['id']: a for a in current}
    old_map = {a['id']: a for a in (previous or [])}
    changed = set(current_map) | set(old_map) if previous is None or site_changed else {
        key for key in set(current_map) | set(old_map) if current_map.get(key) != old_map.get(key)
    }
    urls = {f'{BASE}/notes/{key}/' for key in changed}
    if changed or site_changed or previous is None:
        urls.update([BASE+'/', BASE+'/notes/', BASE+'/archive/', BASE+'/topics/'])
        affected = current + (previous or []) if site_changed or previous is None else [a for a in current + (previous or []) if a['id'] in changed]
        urls.update(BASE+'/topics/'+topic_slug(a['category'])+'/' for a in affected if a.get('category'))
    if site_changed or previous is None:
        urls.update(BASE+'/'+path+'/' for path in ['tools', 'resources', 'about', 'subscribe'])
    elif resources_changed:
        urls.add(BASE+'/resources/')
    return sorted(urls)

def payload(urls, key):
    if not re.fullmatch(r'[a-zA-Z0-9-]{8,128}', key):
        raise ValueError('Invalid public verification identifier')
    if any(not url.startswith(BASE+'/') for url in urls):
        raise ValueError('URL outside the publication path')
    if len(urls) > 10000:
        raise ValueError('Too many URLs for one request')
    return {'host': urlparse(BASE).netloc, 'key': key,
            'keyLocation': f'{BASE}/{key}.txt', 'urlList': urls}

def main(dry_run=False):
    revision = os.environ.get('PREVIOUS_SHA', '')
    current = json.loads((ROOT/'articles.json').read_text())
    raw = previous_file(revision, 'articles.json')
    previous = json.loads(raw) if raw else None
    # Introduction of this integration requires the initial site submission.
    first_run = previous_file(revision, 'indexnow.py') is None
    site_changed = first_run or any(previous_file(revision, name) != (ROOT/name).read_bytes()
                                   for name in ['site.py', 'site.css', 'site.js', 'social-card.jpg', 'topics.py'])
    resources_changed = previous_file(revision, 'resources.json') != (ROOT/'resources.json').read_bytes()
    urls = changed_urls(current, previous, site_changed, resources_changed)
    if not urls:
        print('No published content changed; no IndexNow request sent.')
        return
    data = payload(urls, (ROOT/'indexnow-key.txt').read_text().strip())
    if dry_run:
        print(json.dumps({'count': len(urls), 'urls': urls}, indent=2))
        return
    request = urllib.request.Request(ENDPOINT, data=json.dumps(data).encode(),
                                    headers={'Content-Type': 'application/json; charset=utf-8',
                                             'User-Agent': 'GDOG-IndexNow/1.0'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'IndexNow HTTP {error.code}; deployment is separate from notification.') from None
    if status not in (200, 202):
        raise RuntimeError(f'Unexpected IndexNow HTTP {status}')
    state = 'accepted' if status == 200 else 'accepted; key validation pending'
    message = f'IndexNow: HTTP {status}, {len(urls)} URLs {state}. Submission does not confirm indexing.'
    print(message)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write(message+'\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    main(parser.parse_args().dry_run)
