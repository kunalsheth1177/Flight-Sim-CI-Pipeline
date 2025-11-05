import os
import tempfile

from sim.cli import run_sim
from sim.telemetry import compare_csvs


def test_takeoff_golden_comparison():
    tmpdir = tempfile.mkdtemp()
    out_csv = os.path.join(tmpdir, "run.csv")
    golden = os.path.join("telemetry", "golden_takeoff_landing.csv")
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
    ok, reason = compare_csvs(
        golden,
        out_csv,
        atol=0.5,
        per_column_atol={"pos_y_m": 0.02},
    )
    assert ok, reason

