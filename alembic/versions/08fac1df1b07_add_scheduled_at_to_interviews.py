"""add scheduled_at to interviews

Revision ID: 08fac1df1b07
Revises: 2abaecd3e0ad
Create Date: 2026-09-22 14:33:30.759168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08fac1df1b07'
down_revision: Union[str, None] = '2abaecd3e0ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interviews', sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('interviews', 'scheduled_at')