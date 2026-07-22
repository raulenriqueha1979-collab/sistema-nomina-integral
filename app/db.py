"""Persistencia en SQLite: empresas y fichas de trabajadores."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

DB_PATH = os.environ.get(
    "NOMINA_DB",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "nomina.db"),
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                rif TEXT,
                direccion TEXT,
                creado TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fichas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                nombre TEXT NOT NULL,
                cedula TEXT NOT NULL,
                cargo TEXT,
                creado TEXT NOT NULL,
                datos TEXT NOT NULL
            )
            """
        )
        # Migración: agregar empresa_id si la tabla es antigua.
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(fichas)").fetchall()]
        if "empresa_id" not in cols:
            conn.execute("ALTER TABLE fichas ADD COLUMN empresa_id INTEGER")


# ------------------------------ Empresas ------------------------------
def crear_empresa(nombre: str, rif: str, direccion: str) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO empresas (nombre, rif, direccion, creado) VALUES (?,?,?,?)",
            (nombre, rif, direccion, datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def actualizar_empresa(empresa_id: int, nombre: str, rif: str, direccion: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE empresas SET nombre=?, rif=?, direccion=? WHERE id=?",
            (nombre, rif, direccion, empresa_id),
        )


def listar_empresas() -> List[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute(
            "SELECT id, nombre, rif, direccion, creado FROM empresas ORDER BY nombre"
        ).fetchall()


def obtener_empresa(empresa_id: int) -> Optional[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute(
            "SELECT id, nombre, rif, direccion FROM empresas WHERE id = ?", (empresa_id,)
        ).fetchone()


def eliminar_empresa(empresa_id: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM empresas WHERE id = ?", (empresa_id,))


def guardar_ficha(nombre: str, cedula: str, cargo: str, datos: Dict,
                  empresa_id: Optional[int] = None) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO fichas (empresa_id, nombre, cedula, cargo, creado, datos) "
            "VALUES (?,?,?,?,?,?)",
            (empresa_id, nombre, cedula, cargo,
             datetime.now().isoformat(timespec="seconds"),
             json.dumps(datos, ensure_ascii=False)),
        )
        return cur.lastrowid


def listar_fichas() -> List[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute(
            "SELECT f.id, f.nombre, f.cedula, f.cargo, f.creado, e.nombre AS empresa "
            "FROM fichas f LEFT JOIN empresas e ON e.id = f.empresa_id "
            "ORDER BY f.id DESC"
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
