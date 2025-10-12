#!/usr/bin/env python3
"""
Database management script for NeedleAi.
Provides functions to create database, run migrations, and manage schema.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
import re

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("❌ psycopg2 not installed. Install it with: pip install psycopg2-binary")
    sys.exit(1)


class DatabaseManager:
    """Manage database creation and migrations."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL. If None, reads from environment.
        """
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/needleai"
        )
        self._parse_database_url()

    def _parse_database_url(self):
        """Parse database URL into components."""
        # Format: postgresql://user:password@host:port/dbname
        pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
        match = re.match(pattern, self.database_url)

        if not match:
            raise ValueError(f"Invalid DATABASE_URL format: {self.database_url}")

        self.user = match.group(1)
        self.password = match.group(2)
        self.host = match.group(3)
        self.port = int(match.group(4))
        self.dbname = match.group(5)

    def check_postgres_connection(self) -> bool:
        """
        Check if PostgreSQL server is accessible.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname="postgres"
            )
            conn.close()
            return True
        except psycopg2.OperationalError as e:
            print(f"❌ Cannot connect to PostgreSQL: {e}")
            return False

    def database_exists(self) -> bool:
        """
        Check if the database exists.

        Returns:
            True if database exists, False otherwise.
        """
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.dbname,)
            )
            exists = cursor.fetchone() is not None

            cursor.close()
            conn.close()
            return exists
        except psycopg2.Error as e:
            print(f"❌ Error checking database: {e}")
            return False

    def create_database(self) -> bool:
        """
        Create the database if it doesn't exist.

        Returns:
            True if database was created or already exists, False on error.
        """
        if self.database_exists():
            print(f"✅ Database '{self.dbname}' already exists")
            return True

        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            print(f"🏗️  Creating database '{self.dbname}'...")
            cursor.execute(f'CREATE DATABASE "{self.dbname}"')

            cursor.close()
            conn.close()

            print(f"✅ Database '{self.dbname}' created successfully")
            return True
        except psycopg2.Error as e:
            print(f"❌ Error creating database: {e}")
            return False

    def drop_database(self, force: bool = False) -> bool:
        """
        Drop the database.

        Args:
            force: If True, doesn't ask for confirmation.

        Returns:
            True if database was dropped, False otherwise.
        """
        if not force:
            response = input(f"⚠️  Are you sure you want to drop database '{self.dbname}'? (yes/no): ")
            if response.lower() != "yes":
                print("❌ Aborted")
                return False

        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Terminate active connections
            cursor.execute(
                """
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                AND pid <> pg_backend_pid()
                """,
                (self.dbname,)
            )

            print(f"🗑️  Dropping database '{self.dbname}'...")
            cursor.execute(f'DROP DATABASE IF EXISTS "{self.dbname}"')

            cursor.close()
            conn.close()

            print(f"✅ Database '{self.dbname}' dropped successfully")
            return True
        except psycopg2.Error as e:
            print(f"❌ Error dropping database: {e}")
            return False

    def run_migrations(self, revision: str = "head") -> bool:
        """
        Run Alembic migrations.

        Args:
            revision: Target revision (default: "head" for latest)

        Returns:
            True if migrations successful, False otherwise.
        """
        # Find alembic.ini
        backend_dir = Path(__file__).parent.parent
        alembic_ini = backend_dir / "alembic.ini"

        if not alembic_ini.exists():
            print(f"❌ alembic.ini not found at {alembic_ini}")
            return False

        print(f"🔄 Running migrations to revision: {revision}")

        try:
            # Run alembic upgrade
            result = subprocess.run(
                ["alembic", "upgrade", revision],
                cwd=backend_dir,
                capture_output=True,
                text=True,
                check=True
            )

            print(result.stdout)
            print("✅ Migrations completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Migration failed:")
            print(e.stderr)
            return False
        except FileNotFoundError:
            print("❌ Alembic not found. Install it with: pip install alembic")
            return False

    def get_current_revision(self) -> Optional[str]:
        """
        Get current database revision.

        Returns:
            Current revision string or None if error.
        """
        backend_dir = Path(__file__).parent.parent

        try:
            result = subprocess.run(
                ["alembic", "current"],
                cwd=backend_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def get_migration_history(self) -> Optional[str]:
        """
        Get migration history.

        Returns:
            Migration history string or None if error.
        """
        backend_dir = Path(__file__).parent.parent

        try:
            result = subprocess.run(
                ["alembic", "history"],
                cwd=backend_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def reset_database(self) -> bool:
        """
        Reset database (drop, create, migrate).

        Returns:
            True if reset successful, False otherwise.
        """
        print("🔄 Resetting database...")

        if not self.drop_database(force=False):
            return False

        if not self.create_database():
            return False

        if not self.run_migrations():
            return False

        print("✅ Database reset completed successfully")
        return True


def main():
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="NeedleAi Database Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--database-url",
        help="PostgreSQL connection URL (default: from DATABASE_URL env var)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create database
    subparsers.add_parser("create", help="Create database")

    # Drop database
    drop_parser = subparsers.add_parser("drop", help="Drop database")
    drop_parser.add_argument("--force", action="store_true", help="Skip confirmation")

    # Run migrations
    migrate_parser = subparsers.add_parser("migrate", help="Run migrations")
    migrate_parser.add_argument(
        "--revision",
        default="head",
        help="Target revision (default: head)",
    )

    # Check status
    subparsers.add_parser("status", help="Show database status")

    # Reset database
    subparsers.add_parser("reset", help="Reset database (drop, create, migrate)")

    # Full setup
    subparsers.add_parser("setup", help="Full setup (create database + run migrations)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize manager
    db_manager = DatabaseManager(database_url=args.database_url)

    print("🗄️  NeedleAi Database Manager")
    print(f"   Database: {db_manager.dbname}")
    print(f"   Host: {db_manager.host}:{db_manager.port}")
    print(f"   User: {db_manager.user}")
    print()

    # Execute command
    if args.command == "create":
        if not db_manager.check_postgres_connection():
            return 1
        return 0 if db_manager.create_database() else 1

    elif args.command == "drop":
        if not db_manager.check_postgres_connection():
            return 1
        return 0 if db_manager.drop_database(force=args.force) else 1

    elif args.command == "migrate":
        return 0 if db_manager.run_migrations(revision=args.revision) else 1

    elif args.command == "status":
        if not db_manager.check_postgres_connection():
            return 1

        exists = db_manager.database_exists()
        print(f"Database exists: {'✅ Yes' if exists else '❌ No'}")

        if exists:
            current = db_manager.get_current_revision()
            if current:
                print(f"\nCurrent revision:")
                print(current)

            history = db_manager.get_migration_history()
            if history:
                print(f"\nMigration history:")
                print(history)
        return 0

    elif args.command == "reset":
        if not db_manager.check_postgres_connection():
            return 1
        return 0 if db_manager.reset_database() else 1

    elif args.command == "setup":
        if not db_manager.check_postgres_connection():
            return 1

        if not db_manager.create_database():
            return 1

        if not db_manager.run_migrations():
            return 1

        print()
        print("🎉 Database setup completed successfully!")
        print(f"   Connection: {db_manager.database_url}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

