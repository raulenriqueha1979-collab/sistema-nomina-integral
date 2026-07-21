"""Persistencia opcional de fichas de trabajadores en SQLite."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

DB_PATH = os.environ.get(
    "CONTROL_FISCAL_DB",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "control_fiscal.db"),
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fichas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                cedula TEXT NOT NULL,
                cargo TEXT,
                creado TEXT NOT NULL,
                datos TEXT NOT NULL
            )
            """
        )


def guardar_ficha(nombre: str, cedula: str, cargo: str, datos: Dict) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO fichas (nombre, cedula, cargo, creado, datos) VALUES (?,?,?,?,?)",
            (nombre, cedula, cargo, datetime.now().isoformat(timespec="seconds"),
             json.dumps(datos, ensure_ascii=False)),
        )
        return cur.lastrowid


def listar_fichas() -> List[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute(
            "SELECT id, nombre, cedula, cargo, creado FROM fichas ORDER BY id DESC"
        ).fetchall()


def obtener_ficha(ficha_id: int) -> Optional[Dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT datos FROM fichas WHERE id = ?", (ficha_id,)
        ).fetchone()
    if row is None:
        return None
    return json.loads(row["datos"])


def eliminar_ficha(ficha_id: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM fichas WHERE id = ?", (ficha_id,))
