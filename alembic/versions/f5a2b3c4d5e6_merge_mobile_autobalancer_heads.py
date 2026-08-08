"""Merge the Mobile Admin and Autobalancer migration branches.

Revision ID: f5a2b3c4d5e6
Revises: b42e9a1c7d3f, c8a4e2f6b901
Create Date: 2026-08-04
"""

from typing import Sequence, Union


revision: str = "f5a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = (
    "b42e9a1c7d3f",
    "c8a4e2f6b901",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Join the two already-applied schema branches."""


def downgrade() -> None:
    """Split branches again when downgrading past the merge point."""
