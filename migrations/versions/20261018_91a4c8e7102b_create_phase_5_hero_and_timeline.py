"""create_phase_5_hero_and_timeline

Revision ID: 91a4c8e7102b
Revises: 798251d0bafb
Create Date: 2026-10-18 21:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91a4c8e7102b'
down_revision: Union[str, None] = '798251d0bafb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create hero_slides table
    op.create_table(
        'hero_slides',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('subtitle', sa.Text(), nullable=True),
        sa.Column('eyebrow', sa.String(length=150), nullable=True),
        sa.Column('background_image', sa.String(length=500), nullable=False),
        sa.Column('foreground_image', sa.String(length=500), nullable=True),
        sa.Column('primary_cta_label', sa.String(length=100), nullable=True),
        sa.Column('primary_cta_url', sa.String(length=500), nullable=True),
        sa.Column('secondary_cta_label', sa.String(length=100), nullable=True),
        sa.Column('secondary_cta_url', sa.String(length=500), nullable=True),
        sa.Column('text_align', sa.String(length=20), server_default='left', nullable=False),
        sa.Column('overlay_opacity', sa.Integer(), server_default='65', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('image_alt', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('hero_slides', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_hero_slides_id'), ['id'], unique=False)

    # 2. Create timeline_milestones table
    op.create_table(
        'timeline_milestones',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('year', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('image', sa.String(length=500), nullable=True),
        sa.Column('supporting_info', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('timeline_milestones', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_timeline_milestones_id'), ['id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('timeline_milestones', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_timeline_milestones_id'))
    op.drop_table('timeline_milestones')

    with op.batch_alter_table('hero_slides', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_hero_slides_id'))
    op.drop_table('hero_slides')
