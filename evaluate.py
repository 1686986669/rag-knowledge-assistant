"""Retrieval-only evaluation, not an LLM quality or production benchmark."""
import json
from pathlib import Path
from rag import KnowledgeBase
cases=[('服务启动失败怎么办','deployment.md'),('SQL 参数绑定','database.md'),
       ('EXPLAIN 慢查询','database.md'),('API Key 如何保存','security.md'),
       ('发布回滚','deployment.md'),('连接池耗尽','database.md'),
       ('火星种植',None),('海豚食谱',None)]
kb=KnowledgeBase(':memory:'); kb.ingest(Path(__file__).parent/'knowledge')
rows=[]
for question,expected in cases:
    hits=kb.search(question)
    actual=hits[0]['source'] if hits else None
    rows.append(dict(question=question,expected=expected,actual=actual,passed=actual==expected))
report=dict(metric='top1_source_or_abstain',passed=sum(r['passed'] for r in rows),total=len(rows),cases=rows)
print(json.dumps(report,ensure_ascii=False,indent=2))
if report['passed']!=report['total']: raise SystemExit(1)
