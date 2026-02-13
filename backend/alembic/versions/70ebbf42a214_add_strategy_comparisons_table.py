"""add_strategy_comparisons_table

Revision ID: 70ebbf42a214
Revises: 84c0a2590498
Create Date: 2026-02-12 22:17:25.740660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '70ebbf42a214'
down_revision: Union[str, Sequence[str], None] = '84c0a2590498'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 이미 존재하는 enum 타입 재사용
markettype = postgresql.ENUM('KR', 'US', name='markettype', create_type=False)
timeframetype = postgresql.ENUM('H1', 'D1', name='timeframetype', create_type=False)
jobstatus = postgresql.ENUM('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', name='jobstatus', create_type=False)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('strategy_comparisons',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('market', markettype, nullable=False),
    sa.Column('symbols', sa.JSON(), nullable=False),
    sa.Column('timeframe', timeframetype, nullable=False),
    sa.Column('start_date', sa.DateTime(), nullable=False),
    sa.Column('end_date', sa.DateTime(), nullable=False),
    sa.Column('initial_capital', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('strategies', sa.JSON(), nullable=False),
    sa.Column('backtest_ids', sa.JSON(), nullable=False),
    sa.Column('job_status', jobstatus, nullable=False),
    sa.Column('job_error', sa.String(), nullable=True),
    sa.Column('progress', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('strategy_comparisons')
