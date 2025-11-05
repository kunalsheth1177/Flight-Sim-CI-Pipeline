from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
import math


@dataclass
class AircraftState:
    time_s: float
    pos_x_m: float
    pos_y_m: float
    vel_x_mps: float
    vel_y_mps: float
    pitch_deg: float


@dataclass
class ControlInput:
    thrust_01: float  # 0..1 throttle
    pitch_deg: float  # nose up positive


@dataclass
class Environment:
    wind_x_mps: float = 0.0


class SimpleAircraft2D:
    def __init__(
        self,
        mass_kg: float = 1000.0,
        max_thrust_accel_mps2: float = 12.0,
        air_density_kgpm3: float = 1.225,
        drag_coeff: float = 0.6,
        frontal_area_m2: float = 1.5,
        lift_k_per_mass: float = 0.08,
        gravity_mps2: float = 9.81,
        vertical_damping_per_s: float = 1.0,
    ) -> None:
        self.mass_kg = mass_kg
        self.max_thrust_accel_mps2 = max_thrust_accel_mps2
        self.air_density_kgpm3 = air_density_kgpm3
        self.drag_coeff = drag_coeff
        self.frontal_area_m2 = frontal_area_m2
        self.lift_k_per_mass = lift_k_per_mass
        self.gravity_mps2 = gravity_mps2
        self.vertical_damping_per_s = vertical_damping_per_s

    def step(
        self,
        state: AircraftState,
        control: ControlInput,
        env: Environment,
        dt_s: float,
    ) -> AircraftState:
        # Clamp inputs
        thrust = max(0.0, min(1.0, control.thrust_01))
        pitch_rad = math.radians(control.pitch_deg)

        # Thrust components (acceleration per mass)
        thrust_ax = self.max_thrust_accel_mps2 * thrust * math.cos(pitch_rad)
        thrust_ay = self.max_thrust_accel_mps2 * thrust * math.sin(pitch_rad)

        # Air-relative velocity
        rel_vx = state.vel_x_mps - env.wind_x_mps
        rel_vy = state.vel_y_mps
        speed = math.hypot(rel_vx, rel_vy)

        # Drag: D = 0.5 * rho * Cd * A * v^2, direction opposite airspeed
        if speed > 0.0:
            drag_acc_mag = 0.5 * self.air_density_kgpm3 * self.drag_coeff * self.frontal_area_m2 * (speed * speed) / self.mass_kg
            drag_acc_mag = min(drag_acc_mag, 50.0)
            ux = rel_vx / speed
            uy = rel_vy / speed
            drag_ax = -drag_acc_mag * ux
            drag_ay = -drag_acc_mag * uy
        else:
            drag_ax = 0.0
            drag_ay = 0.0

        # Lift: L = kL * v^2 * max(sin(alpha), 0) upward only (alpha ≈ pitch)
        lift_acc = self.lift_k_per_mass * (speed * speed) * max(math.sin(pitch_rad), 0.0)
        lift_acc = min(lift_acc, 20.0)
        lift_ax = 0.0
        lift_ay = lift_acc

        # Gravity
        grav_ax = 0.0
        grav_ay = -self.gravity_mps2

        # Net acceleration
        ax = thrust_ax + drag_ax + lift_ax + grav_ax
        # Simple vertical damping to bleed climb/descent energy in the toy model
        damping_ay = -self.vertical_damping_per_s * state.vel_y_mps
        ay = thrust_ay + drag_ay + lift_ay + grav_ay + damping_ay

        # Integrate (explicit Euler)
        new_vx = state.vel_x_mps + ax * dt_s
        new_vy = state.vel_y_mps + ay * dt_s
        # Cap speeds to avoid numerical blow-up in toy model
        new_vx = max(-300.0, min(300.0, new_vx))
        new_vy = max(-300.0, min(300.0, new_vy))
        new_x = state.pos_x_m + state.vel_x_mps * dt_s
        new_y = max(0.0, state.pos_y_m + state.vel_y_mps * dt_s)

        return AircraftState(
            time_s=state.time_s + dt_s,
            pos_x_m=new_x,
            pos_y_m=new_y,
            vel_x_mps=new_vx,
            vel_y_mps=new_vy,
            pitch_deg=control.pitch_deg,
        )


def initial_state() -> AircraftState:
    return AircraftState(time_s=0.0, pos_x_m=0.0, pos_y_m=0.0, vel_x_mps=0.0, vel_y_mps=0.0, pitch_deg=0.0)

