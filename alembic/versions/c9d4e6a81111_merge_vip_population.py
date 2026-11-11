"""Join VIP rewards and population-history migration branches.

Both branches are additive. Preserve their revision identities so databases
already upgraded along either path can reach the same head without rewriting
or reapplying an existing migration.
"""

revision = "c9d4e6a81111"
down_revision = ("c8e2a4f61009", "f4b9c2d6e310")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
