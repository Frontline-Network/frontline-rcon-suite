"""Durable provenance for blacklist records created by a Barricade peer.

The caller must add this row in the *same transaction* that creates the record.
Existing records cannot be adopted merely because they match a player ID.
"""
from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import select

from rcon.models import Base
from rcon.barricade_scan_journal import BarricadeScanIntegration  # noqa: F401: register FK target


class BarricadeBlacklistOwnership(Base):
    __tablename__ = 'barricade_blacklist_ownership'
    record_id: Mapped[int] = mapped_column(ForeignKey('blacklist_record.id', ondelete='CASCADE'), primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False)
    integration_id: Mapped[str] = mapped_column(String(36), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(['server_number', 'integration_id'],
            ['barricade_scan_integration.server_number', 'barricade_scan_integration.integration_id'],
            ondelete='RESTRICT', name='fk_barricade_blacklist_owner_integration'),
        CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_barricade_blacklist_owner_server'),
    )


def is_owned(session, record_id, server_number, integration_id):
    row = session.get(BarricadeBlacklistOwnership, record_id)
    return bool(row and row.server_number == server_number and row.integration_id == integration_id)


def lock_current_binding(session, owner):
    server_number, integration_id, credential_id = owner
    binding = session.scalar(select(BarricadeScanIntegration).where(
        BarricadeScanIntegration.server_number == server_number,
        BarricadeScanIntegration.integration_id == integration_id).with_for_update())
    if binding is None or binding.credential_id != credential_id:
        raise ValueError('Barricade integration binding has changed')
