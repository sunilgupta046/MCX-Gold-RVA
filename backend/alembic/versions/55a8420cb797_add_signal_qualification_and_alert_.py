"""add_signal_qualification_and_alert_fields

Revision ID: 55a8420cb797
Revises: df4b4527bdc7
Create Date: 2026-10-21 22:38:10.755893

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55a8420cb797'
down_revision: Union[str, Sequence[str], None] = 'df4b4527bdc7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('rva_signals', sa.Column('base_expiry_date', sa.Date(), nullable=True))
    op.add_column('rva_signals', sa.Column('quote_expiry_date', sa.Date(), nullable=True))
    op.add_column('rva_signals', sa.Column('base_normalized_price', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('quote_normalized_price', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('adjusted_spread', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('expected_gross_edge_bps', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('expected_gross_edge_inr', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('estimated_costs_bps', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('estimated_costs_inr', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('expected_net_edge_bps', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('expected_net_edge_inr', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('cost_coverage_ratio', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('liquidity_status', sa.String(length=32), nullable=True))
    op.add_column('rva_signals', sa.Column('expiry_status', sa.String(length=32), nullable=True))
    op.add_column('rva_signals', sa.Column('base_volume', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('quote_volume', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('base_oi', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('quote_oi', sa.Float(), nullable=True))
    op.add_column('rva_signals', sa.Column('base_dte', sa.Integer(), nullable=True))
    op.add_column('rva_signals', sa.Column('quote_dte', sa.Integer(), nullable=True))
    op.add_column('rva_signals', sa.Column('rejection_reasons_json', sa.Text(), nullable=True))
    op.add_column('rva_signals', sa.Column('signal_explanation', sa.Text(), nullable=True))
    op.add_column('rva_signals', sa.Column('disclaimer', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('rva_signals', 'disclaimer')
    op.drop_column('rva_signals', 'signal_explanation')
    op.drop_column('rva_signals', 'rejection_reasons_json')
    op.drop_column('rva_signals', 'quote_dte')
    op.drop_column('rva_signals', 'base_dte')
    op.drop_column('rva_signals', 'quote_oi')
    op.drop_column('rva_signals', 'base_oi')
    op.drop_column('rva_signals', 'quote_volume')
    op.drop_column('rva_signals', 'base_volume')
    op.drop_column('rva_signals', 'expiry_status')
    op.drop_column('rva_signals', 'liquidity_status')
    op.drop_column('rva_signals', 'cost_coverage_ratio')
    op.drop_column('rva_signals', 'expected_net_edge_inr')
    op.drop_column('rva_signals', 'expected_net_edge_bps')
    op.drop_column('rva_signals', 'estimated_costs_inr')
    op.drop_column('rva_signals', 'estimated_costs_bps')
    op.drop_column('rva_signals', 'expected_gross_edge_inr')
    op.drop_column('rva_signals', 'expected_gross_edge_bps')
    op.drop_column('rva_signals', 'adjusted_spread')
    op.drop_column('rva_signals', 'quote_normalized_price')
    op.drop_column('rva_signals', 'base_normalized_price')
    op.drop_column('rva_signals', 'quote_expiry_date')
    op.drop_column('rva_signals', 'base_expiry_date')
