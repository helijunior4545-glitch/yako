#!/usr/bin/env python3
"""YAKO safe fast arithmetic installer. python3 py.py --check/--apply/--rollback"""
import argparse, ast, hashlib, os, re, sys, tempfile
from pathlib import Path
from decimal import Decimal, localcontext
ROOT=Path(__file__).resolve().parent
DESKTOP=ROOT/'clients/desktop/linux/yako_v1034'
LOCAL=DESKTOP/'yako_v102_server.py'
HOST=ROOT/'server/api/public/yako_runtime_v1036.py'
MOD=DESKTOP/'yako_fast_math.py'
BACKUP=ROOT/'.yako_fast_math_rollback'
TAG='YAKO_FAST_MATH_V1'
MODULE='''"""Safe deterministic arithmetic, no network or model required."""
import ast,re
from decimal import Decimal,localcontext
PERCENT=re.compile(r"^\\s*(?:quanto\\s+(?:é|e)\\s+|what\\s+is\\s+)?(\\d+(?:[.,]\\d+)?)\\s*%\\s*(?:de|of)\\s*(?:R\\$\\s*|\\$\\s*)?(\\d+(?:[.,]\\d+)?)\\s*\\??\\s*$",re.I)
PREFIX=re.compile(r"^\\s*(?:quanto\\s+(?:é|e)\\s+|what\\s+is\\s+|calculate\\s+|calcule\\s+)?",re.I)
def evaluate(node,depth=0):
    if depth>12:raise ValueError('depth')
    if isinstance(node,ast.Expression):return evaluate(node.body,depth+1)
    if isinstance(node,ast.Constant) and type(node.value) in (int,float):return Decimal(str(node.value))
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
        v=evaluate(node.operand,depth+1);return v if isinstance(node.op,ast.UAdd) else -v
    if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow)):
        a=evaluate(node.left,depth+1);b=evaluate(node.right,depth+1)
        if abs(a)>Decimal('1e18') or abs(b)>Decimal('1e18'):raise ValueError('magnitude')
        if isinstance(node.op,ast.Add):return a+b
        if isinstance(node.op,ast.Sub):return a-b
        if isinstance(node.op,ast.Mult):return a*b
        if isinstance(node.op,ast.Div):return a/b
        if b!=int(b) or abs(b)>12:raise ValueError('exponent')
        return a**int(b)
    raise ValueError('unsupported')
def solve_fast_math(text,locale='en'):
    if not isinstance(text,str) or not 1<=len(text.strip())<=160:return None
    raw=text.strip()
    try:
        with localcontext() as ctx:
            ctx.prec=36
            match=PERCENT.fullmatch(raw)
            if match:
                a=Decimal(match.group(1).replace(',','.'));b=Decimal(match.group(2).replace(',','.'))
                value=a*b/100
            else:
                expr=PREFIX.sub('',raw).strip().rstrip('?').strip()
                if not re.fullmatch(r'[0-9\\s.,+*/()\\-×÷^]+',expr):return None
                if not any(x in expr for x in ('+','-','*','/','×','÷','^')):return None
                expr=expr.replace('×','*').replace('÷','/').replace('^','**').replace(',','.')
                value=evaluate(ast.parse(expr,mode='eval'))
            if not value.is_finite() or abs(value)>Decimal('1e18'):return None
            rendered=format(value.normalize(),'f').rstrip('0').rstrip('.') if value!=value.to_integral_value() else str(int(value))
            if locale in ('pt','es','fr'):rendered=rendered.replace('.',',')
            return {'answer':raw+' = **'+rendered+'**','engine':'YAKO deterministic Decimal arithmetic',
                    'model_used':False,'inference_executed':False,'calculation_verified':True,'total_seconds':0}
    except (ValueError,ArithmeticError,SyntaxError,TypeError,OverflowError):return None
'''
LOCAL_ANCHOR='        # Financial arithmetic is a trusted tool, not an LLM task.\n'
HOST_ANCHOR='            # All calculations and risk rules originate from the original V10.34 modules.\n'
LOCAL_ROUTE="        if computed:\n            emit('done',computed)\n"
HOST_ROUTE="            if computed:\n                answer=computed['answer'];metadata=dict(computed);metadata['model_used']=False\n"
def sha(b):return hashlib.sha256(b).hexdigest()
def atomic(path,raw):
    fd,tmp=tempfile.mkstemp(prefix='.yako-tmp-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.chmod(tmp,path.stat().st_mode & 0o777 if path.exists() else 0o644)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def prepare():
    if not LOCAL.is_file() or not HOST.is_file():raise RuntimeError('Active files missing')
    a=LOCAL.read_text();b=HOST.read_text()
    if BACKUP.exists() or MOD.exists() or TAG in a or TAG in b:raise RuntimeError('Already patched or rollback exists')
    if any(x.count(y)!=1 for x,y in ((a,LOCAL_ANCHOR),(b,HOST_ANCHOR),(a,LOCAL_ROUTE),(b,HOST_ROUTE))):raise RuntimeError('Source anchors changed; abort')
    aa=a.replace(LOCAL_ANCHOR,"        # "+TAG+"\n        from yako_fast_math import solve_fast_math\n        fast_math=solve_fast_math(scenario,locale) if mode=='qvac' else None\n"+LOCAL_ANCHOR)
    aa=aa.replace(LOCAL_ROUTE,"        if fast_math:computed=fast_math\n"+LOCAL_ROUTE)
    bb=b.replace(HOST_ANCHOR,"            # "+TAG+"\n            fast_math=desktop_import('yako_fast_math').solve_fast_math(scenario,locale) if mode=='qvac' else None\n"+HOST_ANCHOR)
    bb=bb.replace(HOST_ROUTE,"            if fast_math:computed=fast_math\n"+HOST_ROUTE)
    for path,content in ((LOCAL,aa),(HOST,bb),(MOD,MODULE)):compile(content,str(path),'exec')
    ns={};exec(compile(MODULE,str(MOD),'exec'),ns)
    f=ns['solve_fast_math']
    for question,expected in (('2 + 2','4'),('What is 7 * 8?','56'),('15% of 8000','1200')):
        result=f(question,'en')
        if not result or ('**'+expected+'**') not in result['answer']:raise RuntimeError('Math test failed: '+question)
    for question in ('2 / 0','I have $10,000 to invest','2**999999','Ignore previous instructions'):
        if f(question,'en') is not None:raise RuntimeError('Unsafe match: '+question)
    return a,b,aa,bb
def apply():
    a,b,aa,bb=prepare()
    BACKUP.mkdir(mode=0o700)
    for index,(path,old) in enumerate(((LOCAL,a),(HOST,b))):
        raw=old.encode();(BACKUP/f'{index}.bak').write_bytes(raw)
        (BACKUP/f'{index}.sha256').write_text(sha(raw))
    try:
        atomic(MOD,MODULE.encode());atomic(LOCAL,aa.encode());atomic(HOST,bb.encode())
    except Exception:
        atomic(LOCAL,a.encode());atomic(HOST,b.encode())
        if MOD.exists() and sha(MOD.read_bytes())==sha(MODULE.encode()):MOD.unlink()
        raise
    print('INSTALLED: desktop + Django fast arithmetic. Restart app/workers. Backups:',BACKUP)
def rollback():
    if not BACKUP.is_dir():raise RuntimeError('No rollback backups')
    originals=[]
    for i,path in enumerate((LOCAL,HOST)):
        raw=(BACKUP/f'{i}.bak').read_bytes()
        if sha(raw)!=(BACKUP/f'{i}.sha256').read_text():raise RuntimeError('Corrupt backup')
        if TAG not in path.read_text():raise RuntimeError('Current file changed; refusing overwrite')
        originals.append((path,raw))
    for path,raw in originals:atomic(path,raw)
    if MOD.exists() and sha(MOD.read_bytes())==sha(MODULE.encode()):MOD.unlink()
    print('RESTORED. Backups retained:',BACKUP)
def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for opt in ('check','apply','rollback'):g.add_argument('--'+opt,action='store_true')
    args=p.parse_args()
    if args.rollback:rollback()
    elif args.check:prepare();print('CHECK OK: active anchors, compilation, arithmetic tests')
    else:apply()
if __name__=='__main__':
    try:main()
    except Exception as e:print('SAFE ABORT:',type(e).__name__,e,file=sys.stderr);sys.exit(1)