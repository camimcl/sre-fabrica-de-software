"""Isolated QA lab. Run with the locked backend Python environment.

Secrets and raw logs stay in ignored .qa-local/. No production volumes are used.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / '.qa-local'


def credentials():
    LOCAL.mkdir(exist_ok=True)
    path = LOCAL / 'credentials.json'
    if not path.exists():
        with path.open('x', encoding='utf-8') as stream:
            json.dump({
                'QA_DATABASE_PASSWORD': secrets.token_hex(24),
                'QA_TOKEN_SECRET': secrets.token_hex(32),
                'qa_password': secrets.token_urlsafe(24),
                'qa_email': 'qa.s09@example.org',
            }, stream)
    return json.loads(path.read_text(encoding='utf-8'))


def compose(*args, **kwargs):
    env = os.environ.copy()
    env.update({k: v for k, v in credentials().items() if k.startswith('QA_')})
    kwargs.setdefault('timeout', 240 if 'up' in args else 100)
    return subprocess.run(['docker', 'compose', '-p', 'loadforge-s09-qa',
                           '-f', str(Path(__file__).with_name('compose.yml')), *args],
                          env=env, **kwargs)


def database_url(name):
    from sqlalchemy import URL
    return URL.create('postgresql+psycopg', username='loadforge',
                      password=credentials()['QA_DATABASE_PASSWORD'], host='127.0.0.1',
                      port=55439, database=name).render_as_string(hide_password=False)


def bootstrap():
    # Initial local administrator only. All test operations use the public API.
    sys.path.insert(0, str(ROOT / 'backend'))
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.core.security import hash_password
    from app.db.types import UserRole
    from app.modules.auth.models import User
    from app.db import models  # noqa: F401
    engine = create_engine(database_url('loadforge_s09_demo'))
    values = credentials()
    with Session(engine) as db:
        if not db.scalar(select(User).where(User.email == values['qa_email'])):
            db.add(User(full_name='QA Sprint 09', email=values['qa_email'],
                        password_hash=hash_password(values['qa_password']), role=UserRole.QA))
            db.commit()
    engine.dispose()
    print('QA administrator available; credentials remain in .qa-local/credentials.json.')


def suite(label):
    if not label.replace('-', '').isalnum():
        raise ValueError('Use an alphanumeric result label')
    database = 'loadforge_s09_test'
    probe = compose('exec', '-T', 'db', 'psql', '-U', 'loadforge', '-d', 'postgres',
                    '-Atc', "SELECT datname FROM pg_database WHERE datname='loadforge_s09_test'",
                    capture_output=True, text=True, check=True)
    if database not in probe.stdout:
        compose('exec', '-T', 'db', 'createdb', '-U', 'loadforge', database, check=True)
    env = os.environ.copy()
    env.update(DATABASE_URL=database_url(database), LOADFORGE_TEST_DATABASE_URL=database_url(database),
               LOADFORGE_TEST_ARTIFACT_ROOT=str(LOCAL / 'test-models'), PYTHONIOENCODING='utf-8')
    # Keep large scientific/test temporary files beside the disposable lab,
    # rather than filling the OS volume on installations on another drive.
    temp = LOCAL / 'tmp'
    temp.mkdir(exist_ok=True)
    env.update(TMP=str(temp), TEMP=str(temp), TMPDIR=str(temp))
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'],
                   cwd=ROOT / 'backend', env=env, check=True)
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                             '--junitxml=' + str(LOCAL / f'{label}.xml')],
                            cwd=ROOT / 'backend', env=env, capture_output=True, text=True, encoding='utf-8')
    log = result.stdout + result.stderr
    for value in credentials().values():
        log = log.replace(value, '<REDACTED>')
    (LOCAL / f'{label}.txt').write_text(log, encoding='utf-8')
    (LOCAL / f'{label}-run.json').write_text(json.dumps({
        'captured_at': datetime.now(timezone.utc).isoformat(), 'exit_code': result.returncode,
        'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    }, indent=2), encoding='utf-8')
    print(log[-7000:])
    return result.returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['up', 'stop', 'status', 'bootstrap', 'suite'])
    parser.add_argument('--label', default='pytest-final')
    args = parser.parse_args()
    if args.command == 'up':
        raise SystemExit(compose('up', '--build', '-d', '--wait').returncode)
    if args.command == 'stop':
        raise SystemExit(compose('stop').returncode)
    if args.command == 'status':
        raise SystemExit(compose('ps').returncode)
    if args.command == 'bootstrap':
        bootstrap()
    if args.command == 'suite':
        raise SystemExit(suite(args.label))
