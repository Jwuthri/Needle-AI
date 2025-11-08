"""
Alembic environment configuration for NeedleAi.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import get_settings

# Import your models and database base
from app.database.base import Base
from app.database.models import *  # Import all models

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config


def get_next_revision_number():
    """Generate sequential revision numbers (001, 002, 003, etc.)"""
    import glob
    versions_dir = os.path.join(os.path.dirname(__file__), 'versions')
    existing_files = glob.glob(os.path.join(versions_dir, '*.py'))
    
    # Extract numbers from existing migration files
    numbers = []
    for filepath in existing_files:
        filename = os.path.basename(filepath)
        if filename == '__init__.py':
            continue
        # Try to extract leading digits
        parts = filename.split('_')
        if parts[0].isdigit():
            numbers.append(int(parts[0]))
    
    # Get next number
    if numbers:
        next_num = max(numbers) + 1
    else:
        next_num = 1
    
    return f"{next_num:03d}"


# Override revision ID generation to use sequential numbers
def process_revision_directives(context, revision, directives):
    """Hook to customize revision generation"""
    if directives:
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []
        else:
            # Set custom revision ID
            script.rev_id = get_next_revision_number()

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Get database URL from settings
settings = get_settings()
database_url = settings.database_url

# Override the sqlalchemy.url in alembic.ini with the one from settings
config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Create engine configuration
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
