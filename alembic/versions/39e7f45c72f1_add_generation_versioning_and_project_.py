"""add_generation_versioning_and_project_active_tracking

Revision ID: 39e7f45c72f1
Revises: e011ab9dd223
Create Date: 2025-10-14 23:00:26.651466

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '39e7f45c72f1'
down_revision: Union[str, Sequence[str], None] = 'e011ab9dd223'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add version tracking to generations and active generation tracking to projects."""
    
    # Add new columns to generations table
    op.add_column('generations', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('generations', sa.Column('version_name', sa.String(length=50), nullable=True))
    op.add_column('generations', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('generations', sa.Column('storage_path', sa.String(length=500), nullable=True))
    op.add_column('generations', sa.Column('file_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('generations', sa.Column('total_size_bytes', sa.Integer(), nullable=True))
    op.add_column('generations', sa.Column('diff_from_previous', sa.Text(), nullable=True))
    op.add_column('generations', sa.Column('changes_summary', sa.JSON(), nullable=True))
    
    # Add new columns to projects table
    op.add_column('projects', sa.Column('latest_version', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('projects', sa.Column('active_generation_id', sa.String(length=36), nullable=True))
    
    # Add foreign key constraint for active_generation_id
    op.create_foreign_key(
        'fk_projects_active_generation',
        'projects', 'generations',
        ['active_generation_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Migrate existing data: Set version numbers for existing generations
    # This uses ROW_NUMBER to assign sequential version numbers per project
    op.execute("""
        UPDATE generations g
        SET 
            version = subq.row_num,
            storage_path = './storage/projects/' || g.id
        FROM (
            SELECT 
                id,
                ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY created_at) as row_num
            FROM generations
        ) subq
        WHERE g.id = subq.id
    """)
    
    # Update projects with latest_version based on their generations
    op.execute("""
        UPDATE projects p
        SET latest_version = COALESCE(
            (SELECT MAX(version)
             FROM generations g
             WHERE g.project_id = p.id),
            0
        )
    """)
    
    # Set the most recent generation as active for each project (optional, can be null)
    op.execute("""
        UPDATE projects p
        SET active_generation_id = (
            SELECT g.id
            FROM generations g
            WHERE g.project_id = p.id
            AND g.status = 'completed'
            ORDER BY g.created_at DESC
            LIMIT 1
        )
    """)
    
    # Mark those active generations in the generations table
    op.execute("""
        UPDATE generations g
        SET is_active = true
        FROM projects p
        WHERE g.id = p.active_generation_id
    """)


def downgrade() -> None:
    """Downgrade schema - Remove version tracking fields."""
    
    # Drop foreign key constraint
    op.drop_constraint('fk_projects_active_generation', 'projects', type_='foreignkey')
    
    # Drop columns from projects table
    op.drop_column('projects', 'active_generation_id')
    op.drop_column('projects', 'latest_version')
    
    # Drop columns from generations table
    op.drop_column('generations', 'changes_summary')
    op.drop_column('generations', 'diff_from_previous')
    op.drop_column('generations', 'total_size_bytes')
    op.drop_column('generations', 'file_count')
    op.drop_column('generations', 'storage_path')
    op.drop_column('generations', 'is_active')
    op.drop_column('generations', 'version_name')
    op.drop_column('generations', 'version')
