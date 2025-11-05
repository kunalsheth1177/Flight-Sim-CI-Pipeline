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

