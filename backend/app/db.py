import json
from datetime import datetime, timezone

import asyncpg

from .config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=10)
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def insert_raw_clause(clause: str, context: dict | None) -> str:
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO raw_clauses (clause_text, context, received_at)
        VALUES ($1, $2, $3)
        RETURNING id::text
        """,
        clause,
        json.dumps(context or {}),
        datetime.now(timezone.utc),
    )
    return row["id"]


async def insert_consensus_result(raw_clause_id: str, result: dict) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO consensus_results (raw_clause_id, result, created_at)
        VALUES ($1, $2, $3)
        """,
        raw_clause_id,
        json.dumps(result),
        datetime.now(timezone.utc),
    )


async def purge_expired(ttl_seconds: int) -> int:
    """
    Deletes raw clause rows older than the TTL, after rolling their stats
    into audit_rollups. Returns number of rows purged.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO audit_rollups (period_start, period_end, request_count, rollup)
                SELECT
                    date_trunc('day', received_at),
                    date_trunc('day', received_at) + interval '1 day',
                    count(*),
                    jsonb_build_object('purged_at', now())
                FROM raw_clauses
                WHERE received_at < now() - ($1 || ' seconds')::interval
                GROUP BY date_trunc('day', received_at)
                ON CONFLICT (period_start) DO UPDATE
                    SET request_count = audit_rollups.request_count + EXCLUDED.request_count
                """,
                str(ttl_seconds),
            )
            result = await conn.execute(
                """
                DELETE FROM raw_clauses
                WHERE received_at < now() - ($1 || ' seconds')::interval
                """,
                str(ttl_seconds),
            )
    # asyncpg returns e.g. "DELETE 12"
    try:
        return int(result.split()[-1])
    except (ValueError, IndexError):
        return 0
