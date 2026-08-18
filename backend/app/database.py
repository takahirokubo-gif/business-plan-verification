from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DB_PATH

engine = create_engine(
    f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 既存テーブルへ後から追加した列。create_all はテーブルを作るだけで
# 既存テーブルにALTERをかけないため、ここで補う。
# 列を追加したら必ずこの表にも追記すること（追記漏れがあると、
# 手元のDBファイルが残っている環境だけ no such column で起動後に全滅する）
_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "extracted_items": {
        "source_type": "VARCHAR NOT NULL DEFAULT 'extracted'",
        "source_unit": "VARCHAR",
    },
    "scenarios": {
        "impact_calc_json": "TEXT",
    },
}


def ensure_schema(engine):
    """既存DBファイルに不足している列を補う簡易マイグレーション（冪等）。

    新規テーブル（inquiries・analysis_runs等）は create_all が作るため対象外。
    """
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    for table, columns in _ADDED_COLUMNS.items():
        if table not in tables:
            continue  # create_all が最新定義で作るので補正不要
        existing = {c["name"] for c in insp.get_columns(table)}
        missing = {name: ddl for name, ddl in columns.items() if name not in existing}
        if not missing:
            continue
        with engine.begin() as conn:
            for name, ddl in missing.items():
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
