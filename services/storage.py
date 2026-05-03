"""
services/storage.py — Persistência em SQLite com separação por usuário.

Cada registro pertence a um user_id do Telegram.
Usuários só acessam seus próprios dados.

SEGURANÇA:
  - Queries 100% parametrizadas (sem SQL injection)
  - user_id vem sempre do Telegram, nunca do input do usuário
  - WHERE user_id = ? em toda operação de leitura/escrita/deleção
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent.parent / "data"))
DB_PATH = DATA_DIR / "dados_financeiros.db"


class StorageService:
    """Gerencia registros financeiros no SQLite, isolados por usuário."""

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._inicializar_banco()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _inicializar_banco(self) -> None:
        """Cria as tabelas necessárias se não existirem."""
        with self._conn() as conn:
            # Tabela de usuários registrados
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    user_id    INTEGER PRIMARY KEY,
                    username   TEXT,
                    nome       TEXT,
                    aprovado   INTEGER NOT NULL DEFAULT 0,
                    criado_em  TEXT    NOT NULL
                )
            """)
            # Tabela de lançamentos financeiros
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lancamentos (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id   INTEGER NOT NULL,
                    tipo      TEXT    NOT NULL CHECK(tipo IN ('gasto','receita')),
                    valor     REAL    NOT NULL CHECK(valor > 0),
                    categoria TEXT    NOT NULL,
                    data      TEXT    NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user ON lancamentos(user_id)")
        logger.info("Banco SQLite iniciado em: %s", DB_PATH)

    # ── Gestão de usuários ─────────────────────────────────────

    def registrar_usuario(self, user_id: int, username: str, nome: str) -> bool:
        """
        Registra um novo usuário. Retorna True se foi inserido agora,
        False se já existia.
        """
        with self._conn() as conn:
            existe = conn.execute(
                "SELECT user_id FROM usuarios WHERE user_id = ?", (user_id,)
            ).fetchone()
            if existe:
                return False
            conn.execute(
                "INSERT INTO usuarios (user_id, username, nome, aprovado, criado_em) "
                "VALUES (?, ?, ?, 0, ?)",
                (user_id, username or "", nome or "", datetime.now().isoformat()),
            )
        logger.info("Novo usuário registrado — user_id=%s username=%s", user_id, username)
        return True

    def usuario_aprovado(self, user_id: int) -> bool:
        """Verifica se o usuário está aprovado para usar o bot."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT aprovado FROM usuarios WHERE user_id = ?", (user_id,)
            ).fetchone()
        return bool(row and row["aprovado"] == 1)

    def usuario_existe(self, user_id: int) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT user_id FROM usuarios WHERE user_id = ?", (user_id,)
            ).fetchone()
        return row is not None

    def aprovar_usuario(self, user_id: int) -> bool:
        """Aprova um usuário. Retorna True se encontrado e aprovado."""
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE usuarios SET aprovado = 1 WHERE user_id = ?", (user_id,)
            )
        return cur.rowcount > 0

    def reprovar_usuario(self, user_id: int) -> bool:
        """Remove a aprovação de um usuário."""
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE usuarios SET aprovado = 0 WHERE user_id = ?", (user_id,)
            )
        return cur.rowcount > 0

    def listar_usuarios_pendentes(self) -> list[dict]:
        """Retorna usuários que ainda não foram aprovados."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT user_id, username, nome, criado_em FROM usuarios WHERE aprovado = 0"
            ).fetchall()
        return [dict(r) for r in rows]

    def listar_usuarios_aprovados(self) -> list[dict]:
        """Retorna todos os usuários aprovados."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT user_id, username, nome FROM usuarios WHERE aprovado = 1"
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Lançamentos ────────────────────────────────────────────

    def salvar_registro(self, user_id: int, tipo: str, valor: float, categoria: str) -> None:
        if tipo not in ("gasto", "receita"):
            raise ValueError(f"Tipo inválido: {tipo!r}")
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO lancamentos (user_id, tipo, valor, categoria, data) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, tipo, round(valor, 2), categoria, datetime.now().isoformat()),
            )

    def carregar_dados(self, user_id: int) -> pd.DataFrame:
        """Retorna todos os lançamentos do usuário como DataFrame."""
        with self._conn() as conn:
            df = pd.read_sql_query(
                "SELECT * FROM lancamentos WHERE user_id = ? ORDER BY id",
                conn, params=(user_id,),
            )
        if not df.empty:
            df["data"] = pd.to_datetime(df["data"], errors="coerce")
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
        return df.reset_index(drop=True)

    def deletar_registro(self, user_id: int, registro_id: int) -> dict | None:
        """
        Deleta um lançamento pelo ID, garantindo que pertence ao user_id.
        SEGURANÇA: WHERE user_id = ? impede deletar dados de outro usuário.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM lancamentos WHERE id = ? AND user_id = ?",
                (registro_id, user_id),
            ).fetchone()
            if row is None:
                return None
            removido = dict(row)
            conn.execute(
                "DELETE FROM lancamentos WHERE id = ? AND user_id = ?",
                (registro_id, user_id),
            )
        return removido

    def editar_registro(self, user_id: int, registro_id: int, campo: str, novo_valor) -> dict | None:
        """
        Edita um campo de um lançamento, garantindo que pertence ao user_id.
        SEGURANÇA: campo validado via whitelist antes de entrar na query.
        """
        CAMPOS_EDITAVEIS = {"valor", "categoria", "tipo"}
        if campo not in CAMPOS_EDITAVEIS:
            raise ValueError(f"Campo inválido: {campo!r}")
        with self._conn() as conn:
            existe = conn.execute(
                "SELECT id FROM lancamentos WHERE id = ? AND user_id = ?",
                (registro_id, user_id),
            ).fetchone()
            if existe is None:
                return None
            # campo é da whitelist — seguro interpolar o nome
            conn.execute(
                f"UPDATE lancamentos SET {campo} = ? WHERE id = ? AND user_id = ?",
                (novo_valor, registro_id, user_id),
            )
            row = conn.execute(
                "SELECT * FROM lancamentos WHERE id = ?", (registro_id,)
            ).fetchone()
        return dict(row)
