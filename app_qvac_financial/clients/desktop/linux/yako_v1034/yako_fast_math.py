"""Safe deterministic arithmetic, no network or model required."""
import ast,re
from decimal import Decimal,localcontext
PERCENT=re.compile(r"^\s*(?:quanto\s+(?:é|e)\s+|what\s+is\s+)?(\d+(?:[.,]\d+)?)\s*%\s*(?:de|of)\s*(?:R\$\s*|\$\s*)?(\d+(?:[.,]\d+)?)\s*\??\s*$",re.I)
PREFIX=re.compile(r"^\s*(?:quanto\s+(?:é|e)\s+|what\s+is\s+|calculate\s+|calcule\s+)?",re.I)
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
                if not re.fullmatch(r'[0-9\s.,+*/()\-×÷^]+',expr):return None
                if not any(x in expr for x in ('+','-','*','/','×','÷','^')):return None
                expr=expr.replace('×','*').replace('÷','/').replace('^','**').replace(',','.')
                value=evaluate(ast.parse(expr,mode='eval'))
            if not value.is_finite() or abs(value)>Decimal('1e18'):return None
            rendered=format(value.normalize(),'f').rstrip('0').rstrip('.') if value!=value.to_integral_value() else str(int(value))
            if locale in ('pt','es','fr'):rendered=rendered.replace('.',',')
            return {'answer':raw+' = **'+rendered+'**','engine':'YAKO deterministic Decimal arithmetic',
                    'model_used':False,'inference_executed':False,'calculation_verified':True,'total_seconds':0}
    except (ValueError,ArithmeticError,SyntaxError,TypeError,OverflowError):return None
