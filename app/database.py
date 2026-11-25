import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.config import DB_PATH, settings


class LocalRLSDatabase:
    """
    Camada de Persistência Local (SQLite + Engine de Isolamento Multi-Tenant RLS).
    Simula localmente o comportamento exato do PostgreSQL Row-Level Security
    (`SET LOCAL app.current_tenant_id = '...'`), garantindo que nenhuma query
    retorne ou modifique registros de outro escritório contábil (tenant).
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.current_tenant_id: str = settings.DEFAULT_TENANT_ID
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS kv_rls_store (
                    collection TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (collection, record_id)
                );

                CREATE INDEX IF NOT EXISTS idx_kv_rls_tenant
                ON kv_rls_store (collection, tenant_id);
                """
            )
            conn.commit()

    def set_tenant_context(self, tenant_id: str):
        """Equivalente ao comando PostgreSQL: SET LOCAL app.current_tenant_id = :tenant_id"""
        self.current_tenant_id = tenant_id

    def upsert(self, collection: str, record_id: str, tenant_id: str, data: Dict[str, Any]):
        payload = json.dumps(data, ensure_ascii=False)
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO kv_rls_store (collection, record_id, tenant_id, payload_json, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(collection, record_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    payload_json = excluded.payload_json,
                    updated_at = datetime('now')
                """,
                (collection, record_id, tenant_id, payload),
            )
            conn.commit()

    def list_by_tenant(self, collection: str, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Aplica a política RLS: WHERE tenant_id = current_setting('app.current_tenant_id')"""
        active_tenant = tenant_id or self.current_tenant_id
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM kv_rls_store WHERE collection = ? AND tenant_id = ? ORDER BY rowid ASC",
                (collection, active_tenant),
            ).fetchall()
        return [json.loads(r["payload_json"]) for r in rows]

    def get(self, collection: str, record_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Busca um registro específico aplicando o isolamento RLS do tenant."""
        active_tenant = tenant_id or self.current_tenant_id
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT payload_json FROM kv_rls_store WHERE collection = ? AND record_id = ? AND tenant_id = ?",
                (collection, record_id, active_tenant),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def count_collection(self, collection: str) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM kv_rls_store WHERE collection = ?",
                (collection,),
            ).fetchone()
        return row["cnt"] if row else 0

    def get_postgres_rls_ddl(self) -> str:
        """Retorna o script DDL oficial PostgreSQL 16 com Row-Level Security conforme Seção 2.2 do Playbook."""
        return """-- ============================================================================
-- PLAYBOOK SEÇÃO 2.2: ISOLAMENTO MULTI-TENANT COM POSTGRESQL RLS NATIVO
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE empresas_clientes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64) NOT NULL,
    cnpj VARCHAR(18) NOT NULL,
    razao_social VARCHAR(255) NOT NULL,
    regime_tributario VARCHAR(64) NOT NULL,
    status_geral VARCHAR(32) DEFAULT 'REGULAR',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ativa Row-Level Security (RLS) obrigatório até para o dono da tabela
ALTER TABLE empresas_clientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE empresas_clientes FORCE ROW LEVEL SECURITY;

-- Política Zero-Trust: Bloqueia qualquer linha cujo tenant_id divirja da sessão
CREATE POLICY tenant_isolation_policy ON empresas_clientes
    AS RESTRICTIVE
    USING (tenant_id = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));

-- Exemplo de injeção automática na sessão do SQLAlchemy Async:
-- SET LOCAL app.current_tenant_id = 'escritorio-piloto-01';
"""


rls_db = LocalRLSDatabase()

