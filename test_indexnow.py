import copy
import unittest
import indexnow

class DiscoveryTests(unittest.TestCase):
    def test_unchanged_content_is_not_resubmitted(self):
        articles=[{'id':'first','title':'A'}]
        self.assertEqual(indexnow.changed_urls(articles,copy.deepcopy(articles)),[])
    def test_new_modified_and_removed_articles(self):
        old=[{'id':'old','title':'A'},{'id':'kept','title':'B'}]
        new=[{'id':'new','title':'C'},{'id':'kept','title':'Updated'}]
        urls=indexnow.changed_urls(new,old)
        for slug in ['old','new','kept']:
            self.assertIn(indexnow.BASE+'/notes/'+slug+'/',urls)
        self.assertNotIn(indexnow.BASE+'/tools/',urls)
    def test_verification_scope(self):
        with self.assertRaises(ValueError):
            indexnow.payload(['https://example.com/'],'a'*32)
        result=indexnow.payload([indexnow.BASE+'/'],'a'*32)
        self.assertTrue(result['keyLocation'].startswith(indexnow.BASE+'/'))
    def test_resource_only_change(self):
        articles=[{'id':'first','title':'A'}]
        self.assertEqual(indexnow.changed_urls(articles,articles,resources_changed=True),
                         [indexnow.BASE+'/resources/'])

if __name__=='__main__':unittest.main()
