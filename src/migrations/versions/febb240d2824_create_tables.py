"""empty message

Revision ID: febb240d2824
Revises: 
Create Date: 2024-07-27 06:12:05.298323

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from models import User

# revision identifiers, used by Alembic.
revision: str = "febb240d2824"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=32), nullable=False),
        sa.Column("password", sa.String(length=32), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=True, default=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "account",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Numeric(), nullable=True),
        sa.Column("id_user", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["id_user"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "transaction",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("summ", sa.Numeric(), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(timezone('utc', now()))"),
            onupdate=sa.func.now(),
        ),
        sa.Column("id_user", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["id_user"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("transaction")
    op.drop_table("account")
    op.drop_table("user")
    # ### end Alembic commands ###
