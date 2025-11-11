#!/usr/bin/env python3
"""
Main CLI entry point for NeedleAi commands.
"""

import click
from app.cli_commands.review_commands import review_group


@click.group()
def cli():
    """NeedleAi CLI - Manage your application from the command line."""
    pass


# Register command groups
cli.add_command(review_group)


if __name__ == "__main__":
    cli()

