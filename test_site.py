import copy
import importlib.util
import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote
from xml.etree import ElementTree

spec=importlib.util.spec_from_file_location('gdog_site',Path(__file__).with_name('site.py'))
site=importlib.util.module_from_spec(spec);spec.loader.exec_module(site)

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.h1=0
    def handle_starttag(self,tag,attrs):
        if tag=='h1':self.h1+=1
        for key,value in attrs:
            if key in ('href','src'):self.links.append(value)

class PublishingTests(unittest.TestCase):
    def test_sharing_metadata_and_breadcrumbs(self):
        with tempfile.TemporaryDirectory() as td:
            root=site.build(td)
            self.assertEqual((root/'social-card.jpg').read_bytes()[:3],b'\xff\xd8\xff')
            a=site.load()[0]
            doc=(root/'notes'/a['id']/'index.html').read_text()
            data=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',doc).group(1))
            self.assertEqual(data[0]['@type'],'TechArticle')
            self.assertEqual(data[1]['itemListElement'][-1]['item'],data[0]['mainEntityOfPage'])
            self.assertIn('summary_large_image',doc)
            self.assertIn('data-share',doc)
            self.assertIn('/wiki',doc)
    def test_sources_and_ids(self):self.assertGreaterEqual(len(site.load()),10)
    def test_reject_duplicate(self):
        articles=site.load();articles.append(copy.deepcopy(articles[0]))
        with self.assertRaises(ValueError):site.validate(articles)
    def test_reject_paths_and_secrets(self):
        for field,value in [('id','../../private'),('body','github_pat_'+('x'*30)+site.load()[0]['body'])]:
            articles=site.load();articles[0][field]=value
            with self.assertRaises(ValueError):site.validate(articles)
    def test_escape_untrusted_markdown(self):
        body,_=site.markdown('<img src=x onerror=alert(1)>\n\n[jump](javascript:alert)\n\n```\n<script>alert(1)</script>\n```')
        self.assertNotIn('<img',body);self.assertNotIn('<script',body);self.assertNotIn('href="javascript:',body)
    def test_code_keeps_characters(self):
        rendered,_=site.markdown('```sh\nif [ "$a" = "x" ]; then echo "<ok>"; fi\n```')
        self.assertIn('&lt;ok&gt;',rendered);self.assertIn('$a',rendered)
    def test_build_navigation_feeds_and_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            root=site.build(td)
            for file in root.rglob('*.html'):
                doc=file.read_text();parser=Links();parser.feed(doc)
                self.assertEqual(parser.h1,1,str(file));self.assertIn('rel="canonical"',doc)
                for link in parser.links:
                    parsed=urlparse(link)
                    if parsed.scheme or parsed.netloc or not parsed.path:continue
                    target=(file.parent/unquote(parsed.path)).resolve()
                    self.assertTrue(target.is_relative_to(root.resolve()),link)
                    self.assertTrue(target.exists(),f'{file}: {link}')
            rss=ElementTree.parse(root/'feed.xml');self.assertEqual(len(rss.findall('.//item')),len(site.load()))
            sitemap=ElementTree.parse(root/'sitemap.xml');self.assertGreater(len(sitemap.getroot()),len(site.load()))
            self.assertEqual(json.loads((root/'manifest.json').read_text())['articles'],len(site.load()))
            self.assertFalse((root/'articles.json').exists())
            self.assertFalse((root/'AGENTS.md').exists())

if __name__=='__main__':unittest.main()
