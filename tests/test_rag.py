import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from rag import KnowledgeBase, chunks, tokens

class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        (self.root/'db.md').write_text('慢查询使用 EXPLAIN 检查索引。SQL 必须参数绑定。',encoding='utf-8')
        (self.root/'release.md').write_text('部署失败检查端口占用。回滚使用上一版本镜像。',encoding='utf-8')
        self.kb=KnowledgeBase(':memory:'); self.kb.ingest(self.root)
    def tearDown(self):
        self.kb.db.close(); self.temp.cleanup()
    def test_chinese_and_english_ranking(self):
        self.assertEqual(self.kb.search('慢查询 EXPLAIN')[0]['source'],'db.md')
    def test_unknown_refuses(self):
        self.assertEqual(self.kb.answer('火星种植')['sources'],[])
    def test_idempotence_and_deletion(self):
        self.kb.ingest(self.root); self.assertEqual(self.kb.db.execute('SELECT COUNT(*) FROM chunks').fetchone()[0],2)
        (self.root/'db.md').unlink(); self.kb.ingest(self.root)
        self.assertEqual(self.kb.search('EXPLAIN'),[])
    def test_invalid_input(self):
        for question in ['', 'a'*2001]:
            with self.assertRaises(ValueError): self.kb.search(question)
        with self.assertRaises(ValueError): list(chunks('abc',2,2))
    def test_chunk_overlap(self):
        self.assertEqual(list(chunks('abcdefgh',5,2)),['abcde','defgh'])
    def test_sql_payload_is_data(self):
        self.kb.search("'; DROP TABLE chunks; --")
        self.assertEqual(self.kb.db.execute('SELECT COUNT(*) FROM chunks').fetchone()[0],2)
    @patch('rag.chat',return_value={'content':'检查索引 [1]'})
    def test_live_adapter_contract(self,mock):
        result=self.kb.answer('慢查询',True)
        self.assertEqual(result['mode'],'live'); self.assertTrue(result['sources'])
        self.assertIn('不可信',mock.call_args.args[0][0]['content'])

if __name__=='__main__': unittest.main()
