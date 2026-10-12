"""
Embedding generation and storage (OpenAI text-embedding-3-small, 1536 dims).

generate_embedding  — calls OpenAI and returns a list[float].
store_embedding     — upserts the vector into posting_embeddings (no commit).
embed_posting       — builds the text for one posting, embeds it, and stores it.
enqueue_embed_job   — embeds a posting in the background (best effort).
backfill            — embeds every posting that has no vector yet.

Postings need embeddings for semantic search, "similar postings", and resume
matching. After seeding or bulk-importing postings, run:

    python -m app.ingest.embed            # embeds postings that are missing a vector
"""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

logger = logging.getLogger(__name__)


async def generate_embedding(text: str) -> list[float]:
    """Generate a 1536-dimensional embedding vector for the given text."""
    import openai

    settings = get_settings()
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key or None)
    response = await client.embeddings.create(model=settings.embed_model, input=text)
    return list(response.data[0].embedding)


async def store_embedding(
    db: AsyncSession,
    posting_id: UUID,
    embedding: list[float],
) -> None:
    """
    Upsert the embedding for a posting into posting_embeddings.
    The caller owns the transaction (commit happens there).
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.models.posting_embedding import PostingEmbedding

    model_name = get_settings().embed_model
    stmt = (
        pg_insert(PostingEmbedding)
        .values(posting_id=posting_id, embedding=embedding, model=model_name)
        .on_conflict_do_update(
            index_elements=["posting_id"],
            set_={"embedding": embedding, "model": model_name},
        )
    )
    await db.execute(stmt)


def embedding_text(title: str, company: str, description: str | None, skills: list[str]) -> str:
    """The text we embed for a posting — kept in one place so all callers agree."""
    return f"{title} at {company}\nSkills: {', '.join(skills)}\n\n{description or ''}"[:8000]


async def embed_posting(db: AsyncSession, posting_id: UUID) -> bool:
    """Embed one posting and store the vector. Returns False if the posting is gone."""
    from app.models.posting import Posting

    posting = await db.get(Posting, posting_id)
    if posting is None:
        return False
    vector = await generate_embedding(
        embedding_text(posting.title, posting.company, posting.description, posting.skills or [])
    )
    await store_embedding(db, posting_id, vector)
    return True


def enqueue_embed_job(posting_id: UUID) -> None:
    """
    Embed the posting in the background so the request that created it doesn't wait
    on OpenAI. Failures are logged, never raised: a posting without a
    vector still works for keyword search and can be backfilled later.
    Skipped when the site has no OPENAI_API_KEY (smart search off), so no job is started
    only to fail.
    """
    from app.config import get_settings

    if not get_settings().openai_api_key:
        return
    try:
        from app import jobs

        jobs.enqueue("embed_posting", str(posting_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not enqueue embedding job for %s: %s", posting_id, exc)


async def embed_one(posting_id: UUID) -> None:
    """Background job entry point: embed one posting and commit."""
    from app.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        if await embed_posting(db, posting_id):
            await db.commit()


async def backfill(db: AsyncSession, batch_size: int = 50) -> int:
    """Embed every posting that doesn't have a vector yet. Returns how many were embedded."""
    from app.models.posting import Posting
    from app.models.posting_embedding import PostingEmbedding

    missing_stmt = (
        select(Posting.id)
        .outerjoin(PostingEmbedding, PostingEmbedding.posting_id == Posting.id)
        .where(PostingEmbedding.posting_id.is_(None))
    )
    ids = list((await db.execute(missing_stmt)).scalars().all())

    done = 0
    for i, posting_id in enumerate(ids, start=1):
        if await embed_posting(db, posting_id):
            done += 1
        if i % batch_size == 0:
            await db.commit()  # commit in batches so a failure doesn't lose everything
    await db.commit()
    return done


async def _main() -> None:
    from app.db import AsyncSessionLocal, engine

    async with AsyncSessionLocal() as db:
        count = await backfill(db)
    await engine.dispose()
    print(f"Embedded {count} postings.")


if __name__ == "__main__":
    asyncio.run(_main())
