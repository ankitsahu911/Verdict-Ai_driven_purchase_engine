import sqlite3
from pathlib import Path
import json

db_path = Path("backend/data/verdict_dev.db")
if db_path.exists():
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("Tables in verdict_dev.db:", tables)
    for t in tables:
        count = cur.execute(f"SELECT count(*) FROM {t[0]}").fetchone()[0]
        cols = [col[1] for col in cur.execute(f"PRAGMA table_info({t[0]})").fetchall()]
        print(f"Table: {t[0]}, Count: {count}, Columns: {cols[:5]}...")
else:
    print("verdict_dev.db does not exist yet")

# Chroma inspection
chroma_path = Path("backend/data/chroma.sqlite3")
if chroma_path.exists():
    ccon = sqlite3.connect(chroma_path)
    ccur = ccon.cursor()
    ctables = ccur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("ChromaDB tables:", [t[0] for t in ctables if not t[0].startswith("sqlite")])
    collections = ccur.execute("SELECT id, name FROM collections").fetchall()
    print("ChromaDB collections:", collections)
    embeddings_count = ccur.execute("SELECT count(*) FROM embeddings").fetchone()[0]
    print("ChromaDB total embeddings stored:", embeddings_count)
