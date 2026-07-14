# 2026_aimaster_wikigen/assistant(app/database.py + app/models.py)와 동일한 SQLAlchemy 매핑을 재사용한다.
# backend-proxy가 소유한 documents/wikimd 테이블에 대한 읽기 전용 매핑이며, 여기서는 create_all을
# 호출하지 않는다(스키마를 만들거나 바꾸지 않음). 실제 조회에 쓰는 컬럼만 선언한다.
from sqlalchemy import Column, String, Text, create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from ..config import config

_engine = (
    create_engine(config.proxy_database_url, pool_pre_ping=True) if config.proxy_database_url else None
)

if _engine is not None and config.proxy_db_search_path:

    @event.listens_for(_engine, "connect")
    def _set_search_path(dbapi_connection, connection_record):
        # Neon 풀링 커넥션은 접속 문자열의 search_path 옵션을 지원하지 않아 접속 직후 SET으로 처리한다.
        with dbapi_connection.cursor() as cursor:
            cursor.execute(f"SET search_path TO {config.proxy_db_search_path}")
        dbapi_connection.commit()

ProxySessionLocal = (
    sessionmaker(autocommit=False, autoflush=False, bind=_engine) if _engine is not None else None
)

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    document_id = Column(String, primary_key=True)
    space_id = Column(String, nullable=False)
    wiki_doc_id = Column(String, nullable=True)
    status = Column(String, nullable=False)
    title = Column(String, nullable=False)


class WikiMd(Base):
    __tablename__ = "wikimd"

    doc_id = Column(String, primary_key=True)
    space_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    doc_type = Column(String, nullable=True)
