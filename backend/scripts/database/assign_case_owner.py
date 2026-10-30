"""Explicit local-operator assignment of one legacy ownerless case. Never automatic."""
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend/src'))
load_dotenv(ROOT / '.env')
from persistence.database import get_engine


def assign(engine, case_id, email):
    with engine.begin() as connection:
        user_id = connection.execute(text('SELECT user_id FROM app_users WHERE email=:email AND is_active=TRUE AND password_hash IS NOT NULL'), {'email': email.strip().casefold()}).scalar()
        if not user_id:
            raise ValueError('No active registered account matches that email.')
        row = connection.execute(text('SELECT owner_user_id FROM analysis_cases WHERE case_id=:case FOR UPDATE'), {'case': case_id}).first()
        if not row:
            raise ValueError('Case not found.')
        if row[0] is not None:
            raise ValueError('Case already has an owner. Nothing was changed.')
        connection.execute(text('UPDATE analysis_cases SET owner_user_id=:owner WHERE case_id=:case AND owner_user_id IS NULL'), {'owner': user_id, 'case': case_id})


def list_unowned(engine):
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(text('SELECT case_id,title FROM analysis_cases WHERE owner_user_id IS NULL ORDER BY created_at,case_id')).mappings()]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--case-id')
    operation.add_argument('--list-unowned', action='store_true')
    parser.add_argument('--owner-email')
    args = parser.parse_args()
    if args.list_unowned:
        for row in list_unowned(get_engine()):
            print(row['case_id'], row['title'], sep='\t')
    else:
        if not args.owner_email:
            parser.error('--owner-email is required with --case-id')
        assign(get_engine(), args.case_id, args.owner_email)
        print('Selected ownerless case assigned. No other cases were changed.')
