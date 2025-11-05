import os
import tempfile
import numpy as np
import pandas as pd

from sim.cli import run_sim


def test_checksum_row_matches_sums():
    tmpdir = tempfile.mkdtemp()
    out_csv = os.path.join(tmpdir, "run.csv")
    rc = run_sim(
        scenario="takeoff_landing",
        seed=123,
        hz=20,
        duration_s=5.0,
        loss_p=0.1,
        latency_ms=50,
        golden=None,
        out_csv=out_csv,
    )
    assert rc == 0
    df = pd.read_csv(out_csv)
    assert not df.empty
    # Last row is checksum with time_s == -1.0
    chk = df.iloc[-1]
    assert float(chk["time_s"]) == -1.0
    body = df[df["time_s"] >= 0]
    for col in df.columns:
        if col == "time_s":
            continue
        if pd.api.types.is_numeric_dtype(body[col]):
            expected = float(np.nan_to_num(body[col]).sum())
            assert abs(float(chk[col]) - expected) < 1e-6
        else:
            # Non-numeric mirrors the last value
            assert chk[col] == body[col].iloc[-1]

