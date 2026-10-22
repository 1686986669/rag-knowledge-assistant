"""Business-scenario acceptance checks against the real CLI and SQLite store."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]

def cli(db, *args):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    result = subprocess.run([sys.executable, str(ROOT/'rag.py'), '--db', str(db), *map(str,args)],
                            cwd=ROOT, env=env, text=True, encoding='utf-8',
                            capture_output=True, timeout=15, check=True)
    return json.loads(result.stdout)

def main():
    results=[]
    def check(case_id, title, fn):
        try:
            evidence=fn()
            results.append(dict(id=case_id,title=title,passed=True,evidence=evidence))
        except Exception as exc:
            results.append(dict(id=case_id,title=title,passed=False,error=f'{type(exc).__name__}: {exc}'))

    with tempfile.TemporaryDirectory(prefix='.case-',dir=ROOT) as work:
        work=Path(work); db=work/'support.db'
        def outage():
            imported=cli(db,'ingest',ROOT/'knowledge')
            answer=cli(db,'ask','商城接口返回 503，如何排查上游服务？')
            top=answer['sources'][0]
            assert top['source']=='deployment.md',top
            assert '503' in top['text'] and '[1]' in answer['answer']
            assert answer['mode']=='extractive'
            return dict(imported_chunks=imported['chunks'],question='商城接口返回 503，如何排查上游服务？',
                        top_source=top['source'],chunk=top['chunk'],answer=answer['answer'],mode=answer['mode'])
        check('RAG-01','商城接口 503，定位故障处理文档并返回引用',outage)

        def stale_document():
            folder=work/'runbooks';folder.mkdir()
            file=folder/'release.md'
            file.write_text('发布手册：旧版回滚标签 RELEASE_V1。',encoding='utf-8')
            cli(db,'ingest',folder)
            old=cli(db,'ask','RELEASE_V1')
            assert len(old['sources'])==1
            file.write_text('发布手册：新版回滚标签 RELEASE_V2。',encoding='utf-8')
            cli(db,'ingest',folder)
            after=cli(db,'ask','RELEASE_V1')
            current=cli(db,'ask','RELEASE_V2')
            assert after['sources']==[] and len(current['sources'])==1
            file.unlink();cli(db,'ingest',folder)
            removed=cli(db,'ask','RELEASE_V2')
            assert removed['sources']==[]
            return dict(before_source=old['sources'][0]['source'],old_tag_after_update=after['sources'],
                        new_tag_before_delete=current['sources'][0]['source'],new_tag_after_delete=removed['sources'])
        check('RAG-02','发布手册改版与撤回，清除过期知识',stale_document)

        def unknown():
            cli(db,'ingest',ROOT/'knowledge')
            result=cli(db,'ask','公司婚假天数是多少？')
            assert result['sources']==[]
            assert '没有匹配依据' in result['answer']
            return dict(question='公司婚假天数是多少？',**result)
        check('RAG-03','运维知识库缺少人事制度，返回无依据',unknown)

        def sql_input():
            cli(db,'ask',"'; DROP TABLE chunks; --")
            with closing(sqlite3.connect(db)) as conn:
                count=conn.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]
            result=cli(db,'ask','EXPLAIN 慢查询')
            assert count==3 and result['sources'][0]['source']=='database.md'
            return dict(payload="'; DROP TABLE chunks; --",chunks_after_payload=count,
                        followup_top_source=result['sources'][0]['source'])
        check('RAG-04','查询文本含 SQL 攻击字符，知识库仍可查询',sql_input)

    report=dict(data_origin='synthetic business scenarios; executed against actual CLI and SQLite',
                mode='extractive; no live model request',passed=sum(r['passed'] for r in results),
                total=len(results),cases=results)
    target=Path(__file__).with_name('results.json')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['passed']==report['total'] else 1

if __name__=='__main__':raise SystemExit(main())
