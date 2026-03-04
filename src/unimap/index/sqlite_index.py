"""SQLite full-text search index for OCR results."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from unimap.config import GEOJSON_DIR, SQLITE_DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS maps (
    slug TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    map_id TEXT NOT NULL,
    title TEXT NOT NULL,
    canvas_id TEXT,
    iiif_manifest TEXT,
    total_detections INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS text_index USING fts5(
    text,
    map_slug UNINDEXED,
    confidence UNINDEXED,
    bbox_x UNINDEXED,
    bbox_y UNINDEXED,
    bbox_w UNINDEXED,
    bbox_h UNINDEXED,
    tokenize='unicode61'
);
"""


def init_db(db_path: Path = SQLITE_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def index_geojson(conn: sqlite3.Connection, geojson_path: Path) -> int:
    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)

    props = data.get("properties", {})
    slug = geojson_path.stem

    conn.execute(
        """INSERT OR REPLACE INTO maps
           (slug, source, map_id, title, canvas_id, iiif_manifest, total_detections)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            slug,
            props.get("map_source", ""),
            props.get("map_id", ""),
            props.get("map_title", ""),
            props.get("canvas_id", ""),
            props.get("iiif_manifest", ""),
            props.get("total_detections", 0),
        ),
    )

    count = 0
    for feature in data.get("features", []):
        fp = feature.get("properties", {})
        text = fp.get("text", "")
        confidence = fp.get("confidence", 0)

        coords = feature.get("geometry", {}).get("coordinates", [[]])[0]
        if len(coords) >= 4:
            xs = [c[0] for c in coords]
            ys = [c[1] for c in coords]
            bbox_x = int(min(xs))
            bbox_y = int(min(ys))
            bbox_w = int(max(xs) - min(xs))
            bbox_h = int(max(ys) - min(ys))
        else:
            bbox_x = bbox_y = bbox_w = bbox_h = 0

        conn.execute(
            """INSERT INTO text_index
               (text, map_slug, confidence, bbox_x, bbox_y, bbox_w, bbox_h)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (text, slug, confidence, bbox_x, bbox_y, bbox_w, bbox_h),
        )
        count += 1

    conn.commit()
    return count


def index_all_geojson(
    db_path: Path = SQLITE_DB, geojson_dir: Path = GEOJSON_DIR
) -> int:
    conn = init_db(db_path)
    total = 0
    for gj_path in sorted(geojson_dir.glob("*.geojson")):
        n = index_geojson(conn, gj_path)
        total += n
    conn.close()
    return total


def search(query: str, db_path: Path = SQLITE_DB, limit: int = 50) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            ti.text, ti.map_slug, ti.confidence,
            ti.bbox_x, ti.bbox_y, ti.bbox_w, ti.bbox_h,
            m.title, m.source, m.map_id, m.iiif_manifest, m.canvas_id
        FROM text_index ti
        JOIN maps m ON m.slug = ti.map_slug
        WHERE text_index MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()

    results = [dict(row) for row in rows]
    conn.close()
    return results
