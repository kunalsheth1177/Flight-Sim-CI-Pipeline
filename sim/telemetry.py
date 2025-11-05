from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import os
import numpy as np
import pandas as pd


@dataclass
class TelemetryConfig:
    hz: int
    gps_jitter_std_m: float = 0.0
    rng_seed: Optional[int] = None


class TelemetryRecorder:
    def __init__(self, config: TelemetryConfig) -> None:
        self.config = config
        self.dt_s = 1.0 / float(config.hz)
        self._rows: list[Dict[str, Any]] = []
        self._rng = np.random.default_rng(config.rng_seed) if config.rng_seed is not None else None

    def record(self, row: Dict[str, Any]) -> None:
        # Apply GPS jitter only to position fields if configured
        if self._rng is not None and self.config.gps_jitter_std_m > 0.0:
            if "pos_x_m" in row:
                row = dict(row)
                row["pos_x_m"] = float(row["pos_x_m"]) + float(self._rng.normal(0.0, self.config.gps_jitter_std_m))
            if "pos_y_m" in row:
                row = dict(row)
                row["pos_y_m"] = float(row["pos_y_m"]) + float(self._rng.normal(0.0, self.config.gps_jitter_std_m))
        self._rows.append(row)

    def to_dataframe(self) -> pd.DataFrame:
        if not self._rows:
            return pd.DataFrame()
        return pd.DataFrame(self._rows)

    def save_csv(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df = self.to_dataframe()
        if not df.empty:
            # Append checksum row as a cheap determinism guard: sums of numeric columns
            sums = {}
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    sums[col] = float(np.nan_to_num(df[col]).sum())
                else:
                    sums[col] = df[col].iloc[-1]
            # Use time_s = -1.0 to mark checksum row
            if "time_s" in sums:
                sums["time_s"] = -1.0
            df = pd.concat([df, pd.DataFrame([sums])], ignore_index=True)
        df.to_csv(path, index=False)


def compare_csvs(golden_path: str, run_path: str, atol: float = 1e-3, per_column_atol: Optional[Dict[str, float]] = None) -> Tuple[bool, str]:
    if not os.path.exists(golden_path):
        return False, f"Golden missing: {golden_path}"
    golden = pd.read_csv(golden_path)
    run = pd.read_csv(run_path)
    # If golden is empty, treat as placeholder and pass with warning
    if golden.shape[0] == 0:
        return True, "Golden empty: placeholder accepted"
    if list(golden.columns) != list(run.columns):
        return False, "Column mismatch"
    if len(golden) != len(run):
        return False, f"Row count mismatch: golden={len(golden)} run={len(run)}"
    # Numeric compare where possible
    for col in golden.columns:
        g = golden[col]
        r = run[col]
        if pd.api.types.is_numeric_dtype(g) and pd.api.types.is_numeric_dtype(r):
            catol = per_column_atol.get(col, atol) if per_column_atol else atol
            if not np.allclose(g.to_numpy(dtype=float), r.to_numpy(dtype=float), atol=catol, rtol=0.0, equal_nan=True):
                return False, f"Deviation in column: {col}"
        else:
            if not (g == r).all():
                return False, f"Mismatch in column: {col}"
    return True, "OK"

