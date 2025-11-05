import os
import tempfile
import numpy as np
import pandas as pd

from sim.cli import run_sim


EXPECTED_COLUMNS = [
    "time_s",
    "pos_x_m",
    "pos_y_m",
    "vel_x_mps",
    "vel_y_mps",
    "thrust_01",
    "pitch_deg",
    "wind_x_mps",
]


def test_schema_and_profile_takeoff():
    tmpdir = tempfile.mkdtemp()
    out_csv = os.path.join(tmpdir, "run.csv")

    rc = run_sim(
        scenario="takeoff_landing",
        seed=123,
        hz=20,
        duration_s=15.0,
        loss_p=0.0,
        latency_ms=0,
        golden=None,
        out_csv=out_csv,
    )
    assert rc == 0

    df = pd.read_csv(out_csv)
    # Ignore checksum row (time_s == -1.0)
    df = df[df["time_s"] >= 0]

    # Schema check
    assert list(df.columns) == EXPECTED_COLUMNS

    # Helper to slice by time window
    def window(t0, t1):
        return df[(df["time_s"] >= t0) & (df["time_s"] < t1)].copy()

    # Altitude rises during rotate/climb (3.5–8s)
    climb = window(3.5, 8.0)
    dy = np.diff(climb["pos_y_m"].to_numpy())
    assert np.nanmean(dy) > 0.0

    # Altitude at final time should be lower than at 13s (descent near end)
    y_end = float(df["pos_y_m"].iloc[-1])
    y_13 = float(df[df["time_s"] >= 13.0]["pos_y_m"].iloc[0])
    assert y_end < y_13 - 0.1

    # Vx rises then decays: final Vx should be lower than peak by margin
    vx = df["vel_x_mps"].to_numpy()
    vmax = float(np.max(vx))
    vfinal = float(vx[-1])
    assert vfinal < vmax - 0.5  # ensure noticeable decay

