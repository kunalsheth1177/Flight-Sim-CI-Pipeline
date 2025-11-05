from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .physics import SimpleAircraft2D, ControlInput, Environment, initial_state
from .telemetry import TelemetryConfig, TelemetryRecorder, compare_csvs
from .rpc import RpcConfig, UdpServer, UdpClient
from . import scenarios as scenarios_mod


def run_sim(
    scenario: str,
    seed: int,
    hz: int,
    duration_s: float,
    loss_p: float,
    latency_ms: int,
    golden: Optional[str],
    out_csv: str,
) -> int:
    sim = SimpleAircraft2D()
    state = initial_state()

    # Scenario control function
    if scenario == "takeoff_landing":
        control_fn = scenarios_mod.takeoff_landing(seed=seed, wind=0.0)
        gps_jitter_std = 0.0
    elif scenario == "wind_gusts":
        control_fn = scenarios_mod.wind_gusts(seed=seed, gust_std=2.0)
        gps_jitter_std = 0.0
    elif scenario == "gps_jitter":
        control_fn = scenarios_mod.takeoff_landing(seed=seed, wind=0.0)
        gps_jitter_std = scenarios_mod.gps_jitter(seed=seed, std=1.5)
    else:
        print(f"Unknown scenario: {scenario}")
        return 2

    # Telemetry
    tel = TelemetryRecorder(TelemetryConfig(hz=hz, gps_jitter_std_m=gps_jitter_std, rng_seed=seed))

    # RPC server/client
    server = UdpServer(RpcConfig(loss_p=loss_p, latency_ms=latency_ms, rand_seed=seed))
    server.start()
    client = UdpClient(server.address)

    dt_s = 1.0 / float(hz)
    steps = int(round(duration_s / dt_s))
    t0 = time.monotonic()
    last_applied_thrust = 0.0
    last_applied_pitch = 0.0
    for i in range(steps):
        t = i * dt_s
        thrust, pitch, wind = control_fn(t)
        client.send(thrust, pitch)
        # Poll any available command to apply (respecting latency inside server)
        msg = server.poll_next()
        if msg is None:
            applied_thrust = last_applied_thrust
            applied_pitch = last_applied_pitch
        else:
            applied_thrust = float(msg.get("thrust_01", last_applied_thrust))
            applied_pitch = float(msg.get("pitch_deg", last_applied_pitch))
        last_applied_thrust = applied_thrust
        last_applied_pitch = applied_pitch

        state = sim.step(
            state,
            ControlInput(thrust_01=applied_thrust, pitch_deg=applied_pitch),
            Environment(wind_x_mps=float(wind)),
            dt_s,
        )
        tel.record(
            {
                "time_s": state.time_s,
                "pos_x_m": state.pos_x_m,
                "pos_y_m": state.pos_y_m,
                "vel_x_mps": state.vel_x_mps,
                "vel_y_mps": state.vel_y_mps,
                "thrust_01": applied_thrust,
                "pitch_deg": applied_pitch,
                "wind_x_mps": float(wind),
            }
        )
        # Pace roughly real-time if possible (best-effort)
        target = t0 + (i + 1) * dt_s
        now = time.monotonic()
        if target > now:
            time.sleep(min(0.005, target - now))

    # Save outputs
    tel.save_csv(out_csv)
    # Plot
    df = tel.to_dataframe()
    os.makedirs("plots", exist_ok=True)
    base = os.path.splitext(os.path.basename(out_csv))[0]
    out_png = os.path.join("plots", f"{base}.png")
    if not df.empty:
        fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        ax[0].plot(df["time_s"], df["pos_y_m"], label="Altitude (m)")
        ax[0].legend()
        ax[1].plot(df["time_s"], df["vel_x_mps"], label="Vx (m/s)")
        ax[1].legend()
        ax[1].set_xlabel("Time (s)")
        fig.tight_layout()
        fig.savefig(out_png)
        plt.close(fig)

    # Compare goldens
    if golden:
        ok, reason = compare_csvs(golden, out_csv, atol=1e-1)
        if ok:
            print("SIM PASSED")
            return 0
        else:
            print(f"SIM FAILED: {reason}")
            return 1
    else:
        print("SIM COMPLETED (no golden)")
        return 0


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", required=True, choices=["takeoff_landing", "wind_gusts", "gps_jitter"]) 
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--hz", type=int, default=20)
    p.add_argument("--duration-s", type=float, default=15.0)
    p.add_argument("--loss-p", type=float, default=0.0)
    p.add_argument("--latency-ms", type=int, default=0)
    p.add_argument("--golden", type=str, default="")
    p.add_argument("--out", type=str, required=True)
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    return run_sim(
        scenario=args.scenario,
        seed=args.seed,
        hz=args.hz,
        duration_s=args.duration_s,
        loss_p=args.loss_p,
        latency_ms=args.latency_ms,
        golden=args.golden or None,
        out_csv=args.out,
    )


if __name__ == "__main__":
    sys.exit(main())

