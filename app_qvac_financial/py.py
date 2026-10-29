#!/usr/bin/env python3
# AI YAKO — Extração integral de arquivos de código para auditoria
# Somente leitura do projeto. Saída TXT em ~/Downloads.
# Uso: python3 /home/farcry/Downloads/ai_yako_auditoria_integral.txt
# (Python executa scripts .txt explicitamente.)

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import os
import re
import sys

ROOT = Path('/home/farcry/Documents/ai-yako/app_qvac_financial')
OUTDIR = Path('/home/farcry/Downloads')
STAMP = datetime.now().strftime('%Y%m%d-%H%M%S')
OUTPUT = OUTDIR / f'AI_YAKO_AUDITORIA_CODIGO_COMPLETO_{STAMP}.txt'

# Inclui código, configuração e documentação legíveis. Arquivos binários são inventariados.
EXCLUDE_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.mypy_cache', '.pytest_cache', '.next', 'dist', 'build', 'coverage', '.tox', '.idea', '.vscode'}
EXCLUDE_SUFFIXES = {'.pyc', '.pyo', '.so', '.dll', '.exe', '.class', '.jar', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.ico', '.mp3', '.mp4', '.mov', '.avi', '.webm', '.wav', '.pdf', '.zip', '.gz', '.tar', '.7z', '.woff', '.woff2', '.ttf', '.otf', '.sqlite', '.sqlite3', '.db', '.bin', '.onnx', '.gguf', '.pt', '.pth', '.safetensors', '.lockb'}
SECRET_NAMES = {'.env', '.env.local', '.env.production', '.env.development', 'id_rsa', 'id_ed25519', 'credentials.json', 'service-account.json'}
SECRET_SUFFIXES = {'.pem', '.key', '.p12', '.pfx', '.jks', '.keystore'}
MAX_FILE_BYTES = 5 * 1024 * 1024  # proteção contra arquivos gigantes

# Substitui valores em atribuições comuns de segredos, preservando estrutura do código.
SENSITIVE_KEY = re.compile(r'(?i)(?:secret|password|passwd|api[_-]?key|access[_-]?token|refresh[_-]?token|private[_-]?key|client[_-]?secret|database[_-]?url|dsn|authorization|bearer)')
ASSIGNMENT = re.compile(r'(?im)^(\s*(?:[\"\']?[\w.-]+[\"\']?)\s*(?::|=)\s*)([\"\'])([^\r\n]*?)\2(\s*(?:[,#].*)?)$')
ENV_ASSIGN = re.compile(r'(?im)^(\s*[A-Z][A-Z0-9_]*\s*=\s*)([^\r\n#]+)')
BEARER = re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}')
PRIVATE_BLOCK = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----', re.S)


def redact(text):
    text = PRIVATE_BLOCK.sub('[REDACTED PRIVATE KEY]', text)
    text = BEARER.sub('Bearer [REDACTED]', text)
    def repl(m):
        if SENSITIVE_KEY.search(m.group(1)) and m.group(3).strip():
            return m.group(1) + m.group(2) + '[REDACTED]' + m.group(2) + m.group(4)
        return m.group(0)
    text = ASSIGNMENT.sub(repl, text)
    def env_repl(m):
        if SENSITIVE_KEY.search(m.group(1)):
            return m.group(1) + '[REDACTED]'
        return m.group(0)
    return ENV_ASSIGN.sub(env_repl, text)


def main():
    if not ROOT.is_dir():
        sys.exit(f'ERRO: diretório não encontrado: {ROOT}')
    OUTDIR.mkdir(parents=True, exist_ok=True)
    included = []
    skipped = []
    for base, dirs, files in os.walk(ROOT, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS and not (Path(base) / d).is_symlink())
        for name in sorted(files):
            p = Path(base) / name
            rel = p.relative_to(ROOT)
            if p.is_symlink():
                skipped.append((str(rel), 'symlink'))
                continue
            if name in SECRET_NAMES or p.suffix.lower() in SECRET_SUFFIXES or name.startswith('.env'):
                skipped.append((str(rel), 'potential-secret-file'))
                continue
            if p.suffix.lower() in EXCLUDE_SUFFIXES:
                skipped.append((str(rel), 'binary-or-asset'))
                continue
            try:
                size = p.stat().st_size
                if size > MAX_FILE_BYTES:
                    skipped.append((str(rel), f'over-size-limit:{size}'))
                    continue
                raw = p.read_bytes()
                if b'\x00' in raw:
                    skipped.append((str(rel), 'binary-content'))
                    continue
                content = raw.decode('utf-8')
                included.append((str(rel), len(raw), hashlib.sha256(raw).hexdigest(), redact(content)))
            except (OSError, UnicodeError) as exc:
                skipped.append((str(rel), f'unreadable:{type(exc).__name__}'))
    with OUTPUT.open('w', encoding='utf-8') as f:
        f.write('AI YAKO — AUDITORIA INTEGRAL DE CÓDIGO (SOMENTE LEITURA)\n')
        f.write(f'Gerado em: {datetime.now(timezone.utc).isoformat()}\n')
        f.write(f'Raiz: {ROOT}\n')
        f.write('AVISO: REDAÇÃO AUTOMÁTICA DE SEGREDOS É PARCIAL. REVISAR ANTES DE COMPARTILHAR.\n')
        f.write(f'Arquivos textuais incluídos: {len(included)}\n')
        f.write(f'Arquivos ignorados/inventariados: {len(skipped)}\n\n')
        f.write('========== INVENTÁRIO COMPLETO DOS ARQUIVOS TEXTUAIS ==========\n')
        for rel, size, digest, _ in included:
            f.write(f'{rel} | bytes={size} | sha256={digest}\n')
        f.write('\n========== ARQUIVOS NÃO INCLUÍDOS ==========\n')
        for rel, reason in skipped:
            f.write(f'{rel} | motivo={reason}\n')
        for rel, size, digest, content in included:
            f.write('\n\n' + '=' * 90 + '\n')
            f.write(f'ARQUIVO: {rel}\nBYTES: {size}\nSHA256 ORIGINAL: {digest}\n')
            f.write('=' * 90 + '\n')
            for n, line in enumerate(content.splitlines(keepends=True), 1):
                f.write(f'{n:06d} | {line}')
                if not line.endswith(('\n', '\r')):
                    f.write('\n')
    print('AUDITORIA CONCLUÍDA')
    print('Arquivos de texto:', len(included))
    print('Arquivos inventariados sem conteúdo:', len(skipped))
    print('Saída:', OUTPUT)
    print('Tamanho (MB):', round(OUTPUT.stat().st_size / 1024**2, 2))
    print('ATENÇÃO: revise o TXT para segredos antes de compartilhar.')

if __name__ == '__main__':
    main()