"""
CLI commands for managing reviews.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database.session import get_async_session
from app.database.repositories.company import CompanyRepository
from app.database.repositories.review_source import ReviewSourceRepository
from app.database.repositories.review import ReviewRepository
from app.services.embedding_service import get_embedding_service
from app.utils.logging import get_logger

console = Console()
logger = get_logger("review_cli")


@click.group(name="reviews")
def review_group():
    """Commands for managing reviews."""
    pass


@review_group.command(name="ingest-mock")
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True),
    default="data/mock_reviews.py",
    help="Path to mock reviews file",
)
@click.option(
    "--skip-embeddings",
    is_flag=True,
    help="Skip generating embeddings (faster for testing)",
)
@click.option(
    "--batch-size",
    "-b",
    type=int,
    default=50,
    help="Batch size for embedding generation",
)
def ingest_mock_reviews(
    file: str, skip_embeddings: bool, batch_size: int
):
    """
    Ingest mock reviews from the data/mock_reviews.py file.
    
    This will:
    - Create companies if they don't exist
    - Create a review source for mock data
    - Insert all reviews into the database
    - Generate embeddings for each review (unless --skip-embeddings is set)
    """
    asyncio.run(_ingest_mock_reviews(file, skip_embeddings, batch_size))


async def _ingest_mock_reviews(
    file_path: str, skip_embeddings: bool, batch_size: int
):
    """Internal async function to ingest mock reviews."""
    
    console.print("\n[bold blue]🚀 Starting Mock Review Ingestion[/bold blue]\n")
    
    # Load mock reviews
    console.print(f"📂 Loading mock reviews from: {file_path}")
    mock_reviews = _load_mock_reviews(file_path)
    
    if not mock_reviews:
        console.print("[red]❌ No reviews found in file[/red]")
        return
    
    total_reviews = sum(len(reviews) for reviews in mock_reviews.values())
    console.print(f"[green]✓[/green] Loaded {total_reviews} reviews for {len(mock_reviews)} companies\n")
    
    async with get_async_session() as db:
        # Create or get review source
        console.print("📋 Setting up review source...")
        source = await _get_or_create_review_source(db)
        console.print(f"[green]✓[/green] Review source ready: {source.name}\n")
        
        # Get embedding service
        embedding_service = None
        if not skip_embeddings:
            embedding_service = get_embedding_service()
            console.print("[yellow]🤖 Embedding service initialized[/yellow]\n")
        
        # Process each company
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            for company_name, reviews in mock_reviews.items():
                task = progress.add_task(
                    f"Processing {company_name}...",
                    total=None
                )
                
                # Create or get company
                company = await _get_or_create_company(db, company_name)
                
                # Insert reviews
                inserted_reviews = []
                for review_data in reviews:
                    # Parse date if present
                    review_date = None
                    if review_data.get("date"):
                        from datetime import datetime as dt
                        try:
                            review_date = dt.strptime(review_data["date"], "%Y-%m-%d")
                        except:
                            pass
                    
                    review = await ReviewRepository.create(
                        db=db,
                        company_id=company.id,
                        content=review_data["text"],
                        platform=review_data.get("source"),  # source → platform
                        source_id=source.id,  # Optional: link to review_sources table if needed
                        author=review_data.get("author"),
                        sentiment_score=_rating_to_sentiment(review_data.get("rating", 3)),
                        review_date=review_date,  # Actual review date from data
                        metadata={
                            "rating": review_data.get("rating"),
                            "category": review_data.get("category", "review"),
                        },
                    )
                    inserted_reviews.append(review)
                
                await db.commit()
                
                # Generate embeddings if not skipped
                if not skip_embeddings and embedding_service:
                    progress.update(
                        task,
                        description=f"Generating embeddings for {company_name}..."
                    )
                    
                    # Process in batches
                    for i in range(0, len(inserted_reviews), batch_size):
                        batch = inserted_reviews[i:i + batch_size]
                        texts = [r.content for r in batch]
                        
                        embeddings = await embedding_service.generate_embeddings_batch(
                            texts,
                            batch_size=len(batch)
                        )
                        
                        for review, embedding in zip(batch, embeddings):
                            if embedding:
                                await ReviewRepository.update_embedding(
                                    db, review.id, embedding
                                )
                        
                        await db.commit()
                
                progress.update(
                    task,
                    description=f"[green]✓[/green] {company_name}: {len(inserted_reviews)} reviews"
                )
                progress.remove_task(task)
                
                console.print(
                    f"  [green]✓[/green] {company_name}: "
                    f"{len(inserted_reviews)} reviews {'with embeddings' if not skip_embeddings else 'imported'}"
                )
    
    console.print("\n[bold green]🎉 Ingestion Complete![/bold green]")
    console.print(f"\nSummary:")
    console.print(f"  • Companies: {len(mock_reviews)}")
    console.print(f"  • Total Reviews: {total_reviews}")
    console.print(f"  • Embeddings: {'Generated' if not skip_embeddings else 'Skipped'}")
    console.print()


def _load_mock_reviews(file_path: str) -> dict:
    """Load mock reviews from Python file."""
    import importlib.util
    
    spec = importlib.util.spec_from_file_location("mock_reviews", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    return module.MOCK_REVIEWS


async def _get_or_create_company(db, company_name: str):
    """Get or create a company."""
    from app.database.models.company import Company
    from sqlalchemy.future import select
    
    # Try to find existing
    result = await db.execute(
        select(Company).filter(Company.name == company_name)
    )
    company = result.scalar_one_or_none()
    
    if company:
        return company
    
    # Create new company
    # Get or create a default user for company ownership
    from app.database.models.user import User
    result = await db.execute(
        select(User).limit(1)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Create a system user
        user = User(
            email="system@needleai.local",
            full_name="System User",
            clerk_user_id="system",
        )
        db.add(user)
        await db.flush()
    
    company = Company(
        name=company_name,
        created_by=user.id,
        description=f"Auto-created company for {company_name} reviews",
    )
    db.add(company)
    await db.flush()
    
    return company


async def _get_or_create_review_source(db):
    """Get or create a review source for mock data."""
    from sqlalchemy.future import select
    from app.database.models.review_source import ReviewSource
    
    # Try to find existing
    result = await db.execute(
        select(ReviewSource).filter(ReviewSource.name == "Mock Data Import")
    )
    source = result.scalar_one_or_none()
    
    if source:
        return source
    
    # Create new source
    source = ReviewSource(
        name="Mock Data Import",
        source_type="CUSTOM_CSV",
        description="Imported from mock_reviews.py for testing",
        config={},
        cost_per_review=0.0,
        is_active=True,
    )
    db.add(source)
    await db.flush()
    
    return source


def _rating_to_sentiment(rating: int) -> float:
    """
    Convert 1-5 star rating to -1 to 1 sentiment score.
    
    1 star = -1.0 (very negative)
    3 stars = 0.0 (neutral)
    5 stars = 1.0 (very positive)
    """
    if rating is None:
        return 0.0
    
    # Convert 1-5 to -1 to 1
    return (rating - 3) / 2.0


@review_group.command(name="generate-embeddings")
@click.option(
    "--company",
    "-c",
    type=str,
    help="Company name to filter reviews",
)
@click.option(
    "--batch-size",
    "-b",
    type=int,
    default=100,
    help="Batch size for processing",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    help="Limit number of reviews to process",
)
def generate_embeddings_cmd(
    company: Optional[str], batch_size: int, limit: Optional[int]
):
    """Generate embeddings for reviews that don't have them."""
    asyncio.run(_generate_embeddings(company, batch_size, limit))


async def _generate_embeddings(
    company_name: Optional[str], batch_size: int, limit: Optional[int]
):
    """Generate embeddings for reviews."""
    
    console.print("\n[bold blue]🤖 Generating Review Embeddings[/bold blue]\n")
    
    async with get_async_session() as db:
        # Get company if specified
        company_id = None
        if company_name:
            from app.database.models.company import Company
            from sqlalchemy.future import select
            
            result = await db.execute(
                select(Company).filter(Company.name == company_name)
            )
            company = result.scalar_one_or_none()
            
            if not company:
                console.print(f"[red]❌ Company '{company_name}' not found[/red]")
                return
            
            company_id = company.id
            console.print(f"[green]✓[/green] Filtering by company: {company_name}\n")
        
        # Get reviews without embeddings
        reviews = await ReviewRepository.get_reviews_without_embeddings(
            db, limit=limit or 10000, company_id=company_id
        )
        
        if not reviews:
            console.print("[yellow]No reviews found without embeddings[/yellow]")
            return
        
        console.print(f"Found {len(reviews)} reviews without embeddings\n")
        
        # Generate embeddings
        embedding_service = get_embedding_service()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Generating embeddings...", total=len(reviews))
            
            for i in range(0, len(reviews), batch_size):
                batch = reviews[i:i + batch_size]
                texts = [r.content for r in batch]
                
                embeddings = await embedding_service.generate_embeddings_batch(
                    texts, batch_size=len(batch)
                )
                
                successful = 0
                for review, embedding in zip(batch, embeddings):
                    if embedding:
                        await ReviewRepository.update_embedding(
                            db, review.id, embedding
                        )
                        successful += 1
                
                await db.commit()
                progress.update(task, advance=len(batch))
                
                console.print(
                    f"  [green]✓[/green] Processed batch {i//batch_size + 1}: "
                    f"{successful}/{len(batch)} successful"
                )
    
    console.print("\n[bold green]✓ Embedding generation complete![/bold green]\n")


@review_group.command(name="stats")
@click.option(
    "--company",
    "-c",
    type=str,
    help="Company name to show stats for",
)
def show_stats(company: Optional[str]):
    """Show statistics about reviews in the database."""
    asyncio.run(_show_stats(company))


async def _show_stats(company_name: Optional[str]):
    """Show review statistics."""
    
    console.print("\n[bold blue]📊 Review Statistics[/bold blue]\n")
    
    async with get_async_session() as db:
        from app.database.models.company import Company
        from app.database.models.review import Review
        from sqlalchemy.future import select
        from sqlalchemy import func
        
        if company_name:
            # Stats for specific company
            result = await db.execute(
                select(Company).filter(Company.name == company_name)
            )
            company = result.scalar_one_or_none()
            
            if not company:
                console.print(f"[red]❌ Company '{company_name}' not found[/red]")
                return
            
            # Get counts
            result = await db.execute(
                select(
                    func.count(Review.id).label("total"),
                    func.count(Review.embedding).label("with_embeddings"),
                ).filter(Review.company_id == company.id)
            )
            row = result.one()
            
            console.print(f"[bold]{company.name}[/bold]")
            console.print(f"  Total Reviews: {row.total}")
            console.print(f"  With Embeddings: {row.with_embeddings}")
            console.print(f"  Missing Embeddings: {row.total - row.with_embeddings}")
            
        else:
            # Overall stats
            result = await db.execute(
                select(
                    func.count(Review.id).label("total"),
                    func.count(Review.embedding).label("with_embeddings"),
                )
            )
            row = result.one()
            
            # Count companies
            result = await db.execute(select(func.count(Company.id)))
            company_count = result.scalar()
            
            console.print("[bold]Overall Statistics[/bold]")
            console.print(f"  Companies: {company_count}")
            console.print(f"  Total Reviews: {row.total}")
            console.print(f"  With Embeddings: {row.with_embeddings}")
            console.print(f"  Missing Embeddings: {row.total - row.with_embeddings}")
    
    console.print()

