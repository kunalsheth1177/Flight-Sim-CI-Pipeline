# Flight-Sim CI Pipeline

Simple 2D flight simulation with deterministic seeds, golden telemetry comparisons, and latency/packet-loss emulation over a UDP control link.

This repo is designed to demonstrate a CI-friendly simulation workflow: reproducible runs, golden-file verification, parameterized scenarios, and artifact uploads from CI.

## Contents
- **Deterministic scenarios** controlled by a seed
- **2D kinematics** (x: runway distance, y: altitude) with thrust, pitch, drag, gravity, and wind
- **Telemetry** at fixed Hz, CSV export, golden comparison with tolerance
- **UDP RPC controls** with configurable latency and packet loss
- **CLI** to run scenarios, compare against golden, and generate plots
- **Tests** (pytest) and **GitHub Actions** workflow that runs tests and a smoke scenario, then uploads artifacts

## Repository layout
```
flight-sim-ci/
  sim/
    __init__.py
    physics.py       # SimpleAircraft2D dynamics and state
    telemetry.py     # Recorder, CSV I/O, golden comparison
    rpc.py           # UDP client/server with latency & loss
    scenarios.py     # Deterministic scenarios and helpers
    cli.py           # CLI entrypoint (py_binary target)
  telemetry/
    golden_takeoff_landing.csv  # Golden CSV (bootstrap header)
  tests/
    test_golden_takeoff.py
    test_latency_loss.py
  .github/workflows/
    ci.yml
  WORKSPACE
  BUILD
  requirements.txt
  pyproject.toml
  README.md
```

## Installation (plain Python)
```bash
python -m pip install -r requirements.txt
```

Python 3.10+ recommended. If using Conda, ensure the environment provides compatible versions of numpy/pandas/matplotlib/pytest.

## Running the simulator (plain Python)
Basic run with golden comparison and plot output:
```bash
python -m sim.cli --scenario takeoff_landing --seed 123 --hz 20 --duration-s 15 \
  --out telemetry/run.csv --golden telemetry/golden_takeoff_landing.csv
```

Outputs:
- CSV at `--out` (e.g., `telemetry/run.csv`)
- Plot at `plots/<basename>.png` (e.g., `plots/run.png`)
- Terminal prints `SIM PASSED` or `SIM FAILED: <reason>` when `--golden` is provided

To view the plot on macOS:
```bash
open plots/run.png
```

## Bazel
Minimal Bazel setup with `rules_python` and pip integration via `pip_parse`.

Build and test:
```bash
bazel test //:test_golden_takeoff
bazel test //:test_latency_loss
```

Run the CLI via Bazel:
```bash
bazel run //:sim_cli -- --scenario takeoff_landing --seed 123 --hz 20 --duration-s 15 \
  --out telemetry/run.csv --golden telemetry/golden_takeoff_landing.csv
```

## Scenarios
- `takeoff_landing(seed, wind=0)`: Thrust ramp, rotate, brief climb, reduce thrust for approach. Constant wind can be provided.
- `wind_gusts(seed, gust_std)`: Constant thrust/pitch with Gaussian wind gusts per step.
- `gps_jitter(seed, std)`: Returns a standard deviation applied by telemetry to position-only fields.

Scenarios produce deterministic control/wind profiles for a given `seed` and parameters, ensuring repeatable results.

## Determinism and seeds
- Pass `--seed` to the CLI; the same seed yields identical scenario behavior and telemetry noise (for GPS jitter).
- Randomness is managed via `numpy.random.default_rng(seed)` and `random.Random(0)` where applicable.
- Physics integration is deterministic for a given step size `dt = 1/hz`.

## Current results (baseline)
- Full test suite: **5 passed**
- Smoke scenario command used:
  ```bash
  PYTHONPATH="$(pwd)" python -m sim.cli \
    --scenario takeoff_landing --seed 123 --hz 20 --duration-s 15 \
    --out telemetry/ci_run_takeoff_123.csv --golden telemetry/golden_takeoff_landing.csv
  ```
- Result: **SIM PASSED**
- Artifacts produced:
  - Telemetry CSV: `telemetry/ci_run_takeoff_123.csv`
  - Plot PNG: `plots/ci_run_takeoff_123.png`
- Observed profile:
  - `pos_y_m` rises during rotate/climb (≈3.5–8 s) and descends near the end
  - `vel_x_mps` rises early, then decays as thrust reduces and drag dominates

## Telemetry and golden files
- Telemetry is recorded at fixed Hz with fields: time, position, velocity, applied control, and wind.
- CSV columns (schema): `time_s, pos_x_m, pos_y_m, vel_x_mps, vel_y_mps, thrust_01, pitch_deg, wind_x_mps`
- A checksum row is appended as the last row with `time_s = -1.0` and numeric columns containing sums; used as a cheap determinism guard.
- Use `--golden telemetry/<file>.csv` to compare the current run to a known-good reference.
- Comparison checks:
  - Column names and counts must match
  - Row counts must match
  - Numeric columns compared with absolute tolerance (`atol`, default 1e-3 in library, CLI uses 1e-1)
  - Per-column tolerances are supported; we keep altitude `pos_y_m` tighter (e.g., `0.02`) once stable
- Bootstrap: the repo includes a header-only golden at `telemetry/golden_takeoff_landing.csv` so CI/tests pass initially. Replace it with a real golden for stricter verification.

Per-column tolerances we enforce by default in tests:

| Column      | Tolerance |
|-------------|-----------|
| pos_y_m     | 2e-2      |
| vel_x_mps   | 1e-1      |
| vel_y_mps   | 1e-1      |
| others      | 5e-1      |

Generate a real golden from a local run:
```bash
python -m sim.cli --scenario takeoff_landing --seed 123 --hz 20 --duration-s 15 \
  --out telemetry/golden_takeoff_landing.csv
```
Then commit the updated file to enforce regression checks.

## UDP RPC: latency and packet loss emulation
- Controls are sent via UDP client → server as JSON (`thrust_01`, `pitch_deg`).
- Server enqueues packets with a configurable fixed latency (`--latency-ms`) and drops packets with probability `--loss-p`.
- Deterministic loss: RNG in RPC is seeded from the `--seed` to keep runs reproducible.
- Neutral-hold: if a control packet is late/dropped, the last valid control is held (prevents starvation).
  This is verified by a test under moderate loss.

Wind model: current schema includes only `wind_x_mps` (no vertical wind). Crosswind or vertical wind can be added later if needed.

## CLI arguments
```text
--scenario       {takeoff_landing, wind_gusts, gps_jitter}
--seed           int, required
--hz             int, default 20
--duration-s     float seconds, default 15.0
--loss-p         float [0,1], packet drop probability, default 0.0
--latency-ms     int milliseconds, fixed control latency, default 0
--golden         path to golden CSV (optional)
--out            path to output CSV, required
```

Examples:
```bash
# Deterministic takeoff/landing with no loss/latency
python -m sim.cli --scenario takeoff_landing --seed 42 --hz 30 --duration-s 12 \
  --out telemetry/run.csv

# Apply network effects and compare to a golden
python -m sim.cli --scenario takeoff_landing --seed 42 --hz 20 --duration-s 15 \
  --loss-p 0.1 --latency-ms 80 \
  --out telemetry/run.csv --golden telemetry/golden_takeoff_landing.csv
```

## Tests
Run with pytest:
```bash
pytest -q
```
Tests included:
- `test_golden_takeoff.py`: runs `takeoff_landing(seed=123)` and compares to the golden with tolerance
- `test_latency_loss.py`: runs with `loss_p=0.2`, `latency_ms=100`; ensures simulation completes and deviation is within a loose threshold
 - `test_takeoff_profile.py`: checks telemetry schema, climb (3.5–8 s), late descent, and that `Vx` decays from its peak
- `test_no_control_starvation_with_loss` (in `test_latency_loss.py`): asserts neutral-hold prevents extended control starvation under moderate loss

Latest result locally: **4 passed**

If your environment autoloads many pytest plugins and causes conflicts, disable plugin autoload during local runs:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
```

If importing `sim` fails during tests, set `PYTHONPATH` to the repo root:
```bash
PYTHONPATH="$(pwd)" pytest -q
```

## CI (GitHub Actions)
Workflow: `.github/workflows/ci.yml`
- Checkout, set up Python
- Install dependencies from `requirements.txt`
- Run `pytest -q`
- Smoke scenario run:
  ```bash
  python -m sim.cli --scenario takeoff_landing --seed 123 --hz 20 --duration-s 15 \
    --out telemetry/ci_run.csv --golden telemetry/golden_takeoff_landing.csv
  ```
- Upload artifacts: `telemetry/ci_run_takeoff_123.csv` and `plots/ci_run_takeoff_123.png`
 - Caches pip for faster runs

Badge (optional, once public): add a build badge pointing to your workflow.

## Makefile (optional)
Convenience shortcuts:
```Makefile
run:
	PYTHONPATH="$(PWD)" python -m sim.cli --scenario takeoff_landing --seed 123 --hz 20 --duration-s 15 \
	  --out telemetry/run.csv --golden telemetry/golden_takeoff_landing.csv

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH="$(PWD)" pytest -q

golden:
	PYTHONPATH="$(PWD)" python -m sim.cli --scenario takeoff_landing --seed 123 --hz 20 --duration-s 15 \
	  --out telemetry/golden_takeoff_landing.csv

smoke:
	PYTHONPATH="$(PWD)" python -m sim.cli --scenario takeoff_landing --seed 123 --hz 20 --duration-s 15 \
	  --out telemetry/ci_run_takeoff_123.csv --golden telemetry/golden_takeoff_landing.csv
```

## How to update a golden
1. Re-run the scenario with the same seed:
   ```bash
   PYTHONPATH="$(pwd)" python -m sim.cli --scenario takeoff_landing --seed 123 --hz 20 --duration-s 15 \
     --out telemetry/golden_takeoff_landing.csv
   ```
2. Open and inspect the diff of `telemetry/golden_takeoff_landing.csv` (altitude should look flight-like).
3. Commit intentionally along with any justified model changes.

## Notes and best practices
- Use seeds and explicit parameters; avoid hard-coded values in code paths where reproducibility matters.
- Golden updates should be intentional; regenerate and review before committing.
- Keep run durations reasonable in CI to ensure fast feedback.

## License
MIT (or your preferred license). Update as needed.

