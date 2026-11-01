"""add email authentication fields

Revision ID: 20261101_01
Revises:
Create Date: 2026-11-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20261101_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(
            sa.Column(
                "email",
                sa.String(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "email_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "auth_version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.create_unique_constraint(
            "uq_user_email",
            ["email"],
        )

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "auth_action_tokens" not in inspector.get_table_names():
        op.create_table(
            "auth_action_tokens",
            sa.Column(
                "id",
                sa.Integer(),
                primary_key=True,
            ),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("user.id"),
                nullable=False,
            ),
            sa.Column(
                "token_hash",
                sa.String(),
                nullable=False,
            ),
            sa.Column(
                "purpose",
                sa.String(),
                nullable=False,
            ),
            sa.Column(
                "target_email",
                sa.String(),
                nullable=True,
            ),
            sa.Column(
                "expires_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.Column(
                "used_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

        op.create_index(
            "ix_auth_action_tokens_user_id",
            "auth_action_tokens",
            ["user_id"],
        )

        op.create_index(
            "ix_auth_action_tokens_token_hash",
            "auth_action_tokens",
            ["token_hash"],
            unique=True,
        )

        op.create_index(
            "ix_auth_action_tokens_purpose",
            "auth_action_tokens",
            ["purpose"],
        )


def downgrade():
    op.drop_index(
        "ix_auth_action_tokens_purpose",
        table_name="auth_action_tokens",
    )

    op.drop_index(
        "ix_auth_action_tokens_token_hash",
        table_name="auth_action_tokens",
    )

    op.drop_index(
        "ix_auth_action_tokens_user_id",
        table_name="auth_action_tokens",
    )

    op.drop_table("auth_action_tokens")

    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_constraint(
            "uq_user_email",
            type_="unique",
        )
        batch_op.drop_column("auth_version")
        batch_op.drop_column("email_verified")
        batch_op.drop_column("email")
