"""
Making and saving embeddings with OpenAI text-embedding-3-small, which gives 1536 numbers.

generate_embedding  calls OpenAI and gives back a list of floats
store_embedding     saves the vector in posting_embeddings without committing
embed_posting       builds the text for one job, embeds it and saves it
enqueue_embed_job   embeds a job in the background if it can
backfill            embeds every job that has no vector yet

Jobs need embeddings for smart search, similar jobs and resume matching.
After seeding or a bulk import run

    python -m app.ingest.embed            # embeds jobs that are missing a vector
"""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

logger = logging.getLogger(__name__)


async def generate_embedding(text: str) -> list[float]:
    """Make a 1536 number embedding for this text."""
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
    Save or update the embedding for a job in posting_embeddings.
    The caller owns the transaction and commits.
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
    """The text we embed for a job. Kept in one place so every caller agrees."""
    return f"{title} at {company}\nSkills: {', '.join(skills)}\n\n{description or ''}"[:8000]


async def embed_posting(db: AsyncSession, posting_id: UUID) -> bool:
    """Embed one job and save the vector. Gives back False if the job is gone."""
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
    Embed the job in the background so the request that made it does not wait
    on OpenAI. Failures get logged and never raised. A job without a vector
    still works for keyword search and can be filled in later.
    Skipped when the site has no OPENAI_API_KEY, since smart search is off
    and the job would only fail.
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
    """Where the background job starts. Embed one job and commit."""
    from app.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        if await embed_posting(db, posting_id):
            await db.commit()


async def backfill(db: AsyncSession, batch_size: int = 50) -> int:
    """Embed every job that has no vector yet. Gives back how many got done."""
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
            await db.commit()  # commit in batches so one failure does not lose everything
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
