from typing import Any, Dict

import psycopg2

from ..config import config

connection = psycopg2.connect(config.database_url)
connection.autocommit = True


def ensure_schema() -> None:
    with connection.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wiki_documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                category TEXT,
                version TEXT,
                created_date DATE,
                updated_date DATE,
                approval_status TEXT NOT NULL,
                tags TEXT[],
                source_file TEXT,
                related_menus TEXT[],
                summary TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )


def upsert_document_metadata(doc: Dict[str, Any]) -> None:
    with connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO wiki_documents
              (id, title, doc_type, category, version, created_date, updated_date,
               approval_status, tags, source_file, related_menus, summary, updated_at)
            VALUES
              (%(id)s, %(title)s, %(doc_type)s, %(category)s, %(version)s, %(created_date)s,
               %(updated_date)s, %(approval_status)s, %(tags)s, %(source_file)s, %(related_menus)s,
               %(summary)s, now())
            ON CONFLICT (id) DO UPDATE SET
              title = EXCLUDED.title,
              doc_type = EXCLUDED.doc_type,
              category = EXCLUDED.category,
              version = EXCLUDED.version,
              created_date = EXCLUDED.created_date,
              updated_date = EXCLUDED.updated_date,
              approval_status = EXCLUDED.approval_status,
              tags = EXCLUDED.tags,
              source_file = EXCLUDED.source_file,
              related_menus = EXCLUDED.related_menus,
              summary = EXCLUDED.summary,
              updated_at = now();
            """,
            doc,
        )
