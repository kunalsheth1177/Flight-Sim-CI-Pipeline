import os
import tempfile

from sim.cli import run_sim
from sim.telemetry import compare_csvs
import pandas as pd


def test_latency_and_loss_complete():
    tmpdir = tempfile.mkdtemp()
    out_csv = os.path.join(tmpdir, "run.csv")
    golden = os.path.join("telemetry", "golden_takeoff_landing.csv")
    rc = run_sim(
        scenario="takeoff_landing",
        seed=123,
        hz=20,
        duration_s=10.0,
        loss_p=0.2,
        latency_ms=100,
        golden=None,
        out_csv=out_csv,
    )
    assert rc == 0
    ok, reason = compare_csvs(golden, out_csv, atol=1.0)
    # We expect deviations but still within loose threshold
    assert ok, reason


def test_no_control_starvation_with_loss():
    tmpdir = tempfile.mkdtemp()
    out_csv = os.path.join(tmpdir, "run.csv")
    rc = run_sim(
        scenario="takeoff_landing",
        seed=123,
        hz=20,
        duration_s=8.0,
        loss_p=0.3,
        latency_ms=120,
        golden=None,
        out_csv=out_csv,
    )
    assert rc == 0
    df = pd.read_csv(out_csv)
    # After initial seconds, thrust_01 should rarely be exactly 0 (neutral-hold keeps last valid)
    steady = df[df["time_s"] >= 1.0]
    zeros = (steady["thrust_01"].abs() < 1e-9).sum()
    frac_zero = zeros / max(1, len(steady))
    assert frac_zero < 0.25

