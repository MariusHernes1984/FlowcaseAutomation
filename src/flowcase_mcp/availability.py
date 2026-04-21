"""Availability index: maps Flowcase consultants to monthly billing rates.

Source is an Excel file exported from PowerBI ("PBI KONsulent.xlsx"), one
row per consultant with monthly billing rates as decimals (0.78 = 78 %
billed). The file path is read from ``FLOWCASE_AVAILABILITY_PATH``,
defaulting to ``data/availability.xlsx`` relative to the current working
directory.

The index lookups by normalized display name (Flowcase user.name == Excel
employee name). It auto-reloads when the file's mtime changes, so a user
can drop in a new export without restarting the server.
"""

from __future__ import annotations

import logging
import os
import threading
import unicodedata
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PATH = "data/availability.xlsx"
MONTH_COLUMNS = ("January", "February", "March", "April")


def _normalize_name(raw: str | None) -> str:
    """Lowercase, trim, collapse whitespace, drop punctuation."""
    if not raw:
        return ""
    text = unicodedata.normalize("NFKC", str(raw)).strip().lower()
    # Replace common separators with spaces, collapse
    for ch in ("-", "_", "."):
        text = text.replace(ch, " ")
    return " ".join(text.split())


def _token_key(raw: str | None) -> str:
    """Order-insensitive key for matching: sorted normalized tokens."""
    norm = _normalize_name(raw)
    if not norm:
        return ""
    return " ".join(sorted(norm.split()))


def _to_float_or_none(value: Any) -> float | None:
    """Coerce a cell value to float; treat None, NaN, and non-numeric as None."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    # NaN is the only float that doesn't equal itself
    if f != f:
        return None
    return f


class AvailabilityIndex:
    """Lazily-loaded, mtime-aware index of consultant billing rates."""

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        self._path = Path(
            path or os.environ.get("FLOWCASE_AVAILABILITY_PATH", DEFAULT_PATH)
        )
        self._lock = threading.Lock()
        self._by_norm_name: dict[str, dict[str, Any]] = {}
        self._by_token_key: dict[str, dict[str, Any]] = {}
        self._mtime: float | None = None
        self._loaded_rows: int = 0

    @property
    def path(self) -> Path:
        return self._path

    @property
    def loaded_rows(self) -> int:
        self._maybe_reload()
        return self._loaded_rows

    def _file_mtime(self) -> float | None:
        try:
            return self._path.stat().st_mtime
        except FileNotFoundError:
            return None

    def _maybe_reload(self) -> None:
        mtime = self._file_mtime()
        if mtime is None:
            # File missing — treat as empty index
            if self._mtime is not None:
                with self._lock:
                    self._by_norm_name.clear()
                    self._by_token_key.clear()
                    self._loaded_rows = 0
                    self._mtime = None
            return
        if mtime == self._mtime and self._loaded_rows:
            return
        with self._lock:
            # Re-check inside the lock
            if mtime == self._mtime and self._loaded_rows:
                return
            self._load()
            self._mtime = mtime

    def _load(self) -> None:
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError(
                "pandas is required to load the availability Excel. "
                "Install it via `pip install pandas openpyxl`."
            ) from exc

        df = pd.read_excel(self._path, sheet_name=0)
        # Row 0 is a sub-header ("employee", "Billing rate", ...). Drop it.
        if len(df) and df.iloc[0, 0] == "employee":
            df = df.iloc[1:].reset_index(drop=True)

        name_col = df.columns[0]
        by_norm: dict[str, dict[str, Any]] = {}
        by_token: dict[str, dict[str, Any]] = {}

        for row in df.itertuples(index=False):
            name = getattr(row, name_col if isinstance(name_col, str) else "_0", None)
            # itertuples mangles non-identifier column names; fetch via _asdict
            record_dict = row._asdict() if hasattr(row, "_asdict") else None
            if record_dict is None:
                continue
            name = list(record_dict.values())[0]
            if not isinstance(name, str) or not name.strip():
                continue

            months: dict[str, float | None] = {}
            for col in MONTH_COLUMNS:
                months[col.lower()] = _to_float_or_none(record_dict.get(col))

            valid_rates = [v for v in months.values() if v is not None]
            avg_billed = sum(valid_rates) / len(valid_rates) if valid_rates else None

            record = {
                "name": name.strip(),
                "months": months,
                "avg_billed": avg_billed,
                "avg_available": (1.0 - avg_billed) if avg_billed is not None else None,
            }
            by_norm[_normalize_name(name)] = record
            by_token[_token_key(name)] = record

        self._by_norm_name = by_norm
        self._by_token_key = by_token
        self._loaded_rows = len(by_norm)
        logger.info(
            "AvailabilityIndex loaded %d rows from %s", self._loaded_rows, self._path
        )

    def get_by_name(self, name: str | None) -> dict[str, Any] | None:
        """Look up a consultant by display name.

        Tries exact normalized match first, then token-sorted match
        (order-insensitive). Returns ``None`` if no match or file missing.
        """
        if not name:
            return None
        self._maybe_reload()
        norm = _normalize_name(name)
        if norm in self._by_norm_name:
            return self._by_norm_name[norm]
        token = _token_key(name)
        if token in self._by_token_key:
            return self._by_token_key[token]
        return None

    def available(self) -> bool:
        self._maybe_reload()
        return self._loaded_rows > 0


_default_index: AvailabilityIndex | None = None


def get_default_index() -> AvailabilityIndex:
    """Process-wide singleton index bound to the configured path."""
    global _default_index
    if _default_index is None:
        _default_index = AvailabilityIndex()
    return _default_index
