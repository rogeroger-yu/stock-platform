"""Strategy persistence model — SQLAlchemy ORM."""

from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


class Strategy(Base):
    """Persistent strategy definition stored in SQLite.

    Supports creating, updating, and listing strategies with full
    parameter definitions so they can be re-instantiated for backtesting.
    """

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    strategy_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Strategy class key, e.g. 'momentum', 'mean_reversion'"
    )
    description: Mapped[str] = mapped_column(Text, default="")
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    symbols_json: Mapped[str] = mapped_column(Text, default="[]")

    # Evaluation metrics (updated after each backtest run)
    last_annual_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_max_drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    backtest_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
