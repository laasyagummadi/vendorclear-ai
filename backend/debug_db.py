import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.analysis import Analysis

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Analysis).order_by(Analysis.created_at.desc()).limit(3))
        analyses = result.scalars().all()
        for a in analyses:
            print("="*40)
            print("ID:", a.id)
            print("Extracted:", a.extracted_fields)
            print("Raw text:")
            print(a.raw_text)

if __name__ == "__main__":
    asyncio.run(main())
