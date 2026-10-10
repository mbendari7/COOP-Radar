"""
Embedding generation and storage using OpenAI text-embedding-3-small.

generate_embedding — calls OpenAI and returns a list[float] (1536 dims).
store_embedding    — upserts the embedding into posting_embeddings.
enqueue_embed_job  — pushes an embedding job to the RQ ingest queue.
"""

import os
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


async def generate_embedding(text: str) -> list[float]:
    """
    Generate a 1536-dimensional embedding vector for the given text.
    Uses the model configured via EMBED_MODEL env var (default: text-embedding-3-small).
    """
    import openai

    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    model = os.getenv("EMBED_MODEL", "text-embedding-3-small")

    response = await client.embeddings.create(model=model, input=text)
    return response.data[0].embedding


async def store_embedding(
    db: AsyncSession,
    posting_id: UUID,
    embedding: list[float],
) -> None:
    """
    Upsert the embedding for a posting into posting_embeddings.
    If an embedding already exists for this posting, it is replaced.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from app.models.posting_embedding import PostingEmbedding

    model_name = os.getenv("EMBED_MODEL", "text-embedding-3-small")

    stmt = pg_insert(PostingEmbedding).values(
        posting_id=posting_id,
        embedding=embedding,
        model=model_name,
    ).on_conflict_do_update(
        index_elements=["posting_id"],
        set_={"embedding": embedding, "model": model_name},
    )
    await db.execute(stmt)
    await db.commit()


def enqueue_embed_job(posting_id: UUID) -> None:
    """
    Push an embedding generation job to the RQ ingest queue.
    Called after a posting is inserted so embedding happens asynchronously.
    """
    from app.worker import create_queue

    queue = create_queue()
    queue.enqueue("app.ingest.embed._run_embed_job", str(posting_id))


def _run_embed_job(posting_id_str: str) -> None:
    """RQ job entry point (sync wrapper)."""
    import asyncio

    asyncio.run(_run_embed_async(UUID(posting_id_str)))


async def _run_embed_async(posting_id: UUID) -> None:
    from sqlalchemy import select
    from app.db import AsyncSessionLocal
    from app.models.posting import Posting

    async with AsyncSessionLocal() as db:
        posting = (await db.execute(select(Posting).where(Posting.id == posting_id))).scalar_one_or_none()
        if posting is None:
            return
        text = f"{posting.title} {posting.company} {posting.description or ''} {' '.join(posting.skills or [])}"
        embedding = await generate_embedding(text)
        await store_embedding(db, posting_id, embedding)
