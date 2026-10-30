"""Add credentials/session tables without reimporting or claiming old analyses."""
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend/src'))
load_dotenv(ROOT / '.env')
from persistence.database import get_engine


def migrate(engine):
    with engine.begin() as connection:
        columns = {column['name'] for column in inspect(connection).get_columns('app_users')}
        if 'password_hash' not in columns:
            connection.execute(text('ALTER TABLE app_users ADD COLUMN password_hash VARCHAR(255) NULL'))
        sql = (ROOT / 'database/sql/05_auth.sql').read_text(encoding='utf-8')
        sql = '\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--'))
        for statement in sql.split(';'):
            if statement.strip():
                connection.execute(text(statement))


if __name__ == '__main__':
    migrate(get_engine())
    print('Authentication schema ready. Existing ownership was not changed.')
