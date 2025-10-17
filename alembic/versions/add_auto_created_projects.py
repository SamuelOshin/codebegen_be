"""Add auto_created fields to projects table

Revision ID: add_auto_created_projects
Revises: previous_migration
Create Date: 2025-10-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_auto_created_projects'
down_revision = '39e7f45c72f1'  # Correctly points to the versioning migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add auto-creation tracking fields to projects table"""
    
    # Add auto_created column
    op.add_column('projects', sa.Column(
        'auto_created',
        sa.Boolean(),
        nullable=False,
        server_default='false'
    ))
    
    # Add creation_source column
    op.add_column('projects', sa.Column(
        'creation_source',
        sa.String(length=50),
        nullable=True
    ))
    
    # Add original_prompt column
    op.add_column('projects', sa.Column(
        'original_prompt',
        sa.Text(),
        nullable=True
    ))


def downgrade() -> None:
    """Remove auto-creation tracking fields from projects table"""
    
    op.drop_column('projects', 'original_prompt')
    op.drop_column('projects', 'creation_source')
    op.drop_column('projects', 'auto_created')
