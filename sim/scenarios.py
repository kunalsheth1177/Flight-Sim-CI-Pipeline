from __future__ import annotations

from typing import Callable, Tuple
import numpy as np


def takeoff_landing(seed: int, wind: float = 0.0) -> Callable[[float], Tuple[float, float, float]]:
    np.random.default_rng(int(seed))
    # Deterministic schedule: roll ~0-3.5s, rotate to ~10° for climb until ~8s,
    # then approach from ~12s with reduced thrust and pitch back toward 0°.
    def control_fn(t_s: float) -> Tuple[float, float, float]:
        # Baseline wind kept constant (default 0.0) for determinism
        if t_s < 3.5:
            # Roll: ramp thrust to takeoff power, keep pitch near 0°
            thrust = 0.25 + 0.65 * (t_s / 3.5)  # ≈0.25 → 0.9 by 3.5s
            pitch = 0.0
        elif t_s < 8.0:
            # Rotate and initial climb
            thrust = 0.85
            pitch = 10.0  # between 8–12°; choose 10°
        elif t_s < 12.0:
            # Climb/cruise segment
            thrust = 0.7
            pitch = 4.0
        else:
            # Approach: idle thrust with strong nose-down to ensure descent
            thrust = 0.0
            pitch = -20.0
        return float(thrust), float(pitch), float(wind)

    return control_fn


def wind_gusts(seed: int, gust_std: float) -> Callable[[float], Tuple[float, float, float]]:
    rng = np.random.default_rng(int(seed))
    def control_fn(t_s: float) -> Tuple[float, float, float]:
        thrust = 0.6
        pitch = 2.0
        wind = rng.normal(0.0, float(gust_std))
        return float(thrust), float(pitch), float(wind)
    return control_fn


def gps_jitter(seed: int, std: float) -> float:
    # Returns std deviation to be applied by telemetry on positions only
    np.random.default_rng(int(seed))
    return float(std)

