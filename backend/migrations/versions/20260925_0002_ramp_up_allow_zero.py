"""Alinha a constraint de ramp_up_per_window com a API (permite zero).

A API valida ``ramp_up_per_window >= 0`` (carga constante é um cenário
legítimo, sem incremento por janela). A migration inicial usava ``> 0``,
o que rejeitava no banco um valor aceito pela API. Esta migration alinha
a regra do banco à da aplicação.

Revision ID: 20260925_0002
Revises: 20260917_0001
Create Date: 2026-09-25
"""
from collections.abc import Sequence

from alembic import op


revision: str = "20260925_0002"
down_revision: str | None = "20260917_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_scenario_ramp_up", "test_scenarios", type_="check")
    op.create_check_constraint(
        "ck_scenario_ramp_up", "test_scenarios", "ramp_up_per_window >= 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_scenario_ramp_up", "test_scenarios", type_="check")
    op.create_check_constraint(
        "ck_scenario_ramp_up", "test_scenarios", "ramp_up_per_window > 0"
    )
