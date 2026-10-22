"""Private operator CLI; no lead administration is exposed on the public website."""
import argparse
import csv
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app import create_app
from models import Lead

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    export = sub.add_parser('export', help='Write enquiries to a new private CSV file.')
    export.add_argument('path')
    purge = sub.add_parser('purge', help='Delete enquiries older than a chosen number of days.')
    purge.add_argument('--days', type=int, default=180)
    purge.add_argument('--apply', action='store_true', help='Without this flag only show the count.')
    args = parser.parse_args()
    app = create_app()
    with Session(app.extensions['web_engine']) as session:
        if args.command == 'export':
            # Never overwrite existing exports; file readable only by the owner.
            fd = os.open(args.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', newline='', encoding='utf-8') as stream:
                writer = csv.writer(stream)
                columns = list(Lead.__table__.columns.keys())
                writer.writerow(columns)
                for lead in session.scalars(select(Lead).order_by(Lead.created_at)):
                    values = [str(getattr(lead, col)) for col in columns]
                    # Neutralise spreadsheet formula execution in untrusted text.
                    writer.writerow(["'"+v if v.lstrip().startswith(('=', '+', '-', '@')) else v for v in values])
            print('Private export created.')
        else:
            if args.days < 1:
                parser.error('--days must be at least 1')
            cutoff = datetime.now(timezone.utc)-timedelta(days=args.days)
            ids = list(session.scalars(select(Lead.id).where(Lead.created_at < cutoff)))
            if args.apply:
                session.execute(delete(Lead).where(Lead.created_at < cutoff))
                session.commit()
            print(f'{len(ids)} enquiries '+('deleted.' if args.apply else 'eligible. Re-run with --apply to delete.'))

if __name__ == '__main__':
    main()
