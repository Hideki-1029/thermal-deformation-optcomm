"""Body / STT attitude from orbit-catalog face assignments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FACE_OUTWARD_BODY = {
    "PX": np.array([1.0, 0.0, 0.0]),
    "MX": np.array([-1.0, 0.0, 0.0]),
    "PY": np.array([0.0, 1.0, 0.0]),
    "MY": np.array([0.0, -1.0, 0.0]),
    "PZ": np.array([0.0, 0.0, 1.0]),
    "MZ": np.array([0.0, 0.0, -1.0]),
}

EARTH_RADIUS_M = 6371000.0


@dataclass(frozen=True)
class BodyAttitudeEcef:
    """Columns of ``R_ecef_from_body`` are body +X/+Y/+Z in ECEF."""

    R_ecef_from_body: np.ndarray  # (3, 3)
    sun_face: str
    velocity_face: str
    nadir_face: str

    @property
    def body_x_ecef(self) -> np.ndarray:
        return self.R_ecef_from_body[:, 0]

    @property
    def body_y_ecef(self) -> np.ndarray:
        return self.R_ecef_from_body[:, 1]

    @property
    def body_z_ecef(self) -> np.ndarray:
        return self.R_ecef_from_body[:, 2]

    @property
    def lct_boresight_ecef(self) -> np.ndarray:
        """LCT outward optical axis = body -Z."""
        return -self.body_z_ecef


@dataclass(frozen=True)
class PartnerGeometry:
    """Where the known target is placed for position→angle conversion."""

    mode: str
    range_m: float
    direction_ecef: np.ndarray
    realistic_link: bool
    notes: str


def _unit(vec: np.ndarray) -> np.ndarray:
    v = np.asarray(vec, dtype=float)
    n = np.linalg.norm(v)
    if n <= 0.0:
        raise ValueError("Zero vector cannot be normalized")
    return v / n


def _normalize_face(face: str) -> str:
    text = str(face).strip().upper()
    if "~" in text:
        text = text.split("~", 1)[0]
    if text not in FACE_OUTWARD_BODY:
        raise ValueError(f"Unknown body face {face!r}")
    return text


def body_axis_ecef_from_face(face: str, aligned_ecef: np.ndarray) -> tuple[str, np.ndarray]:
    """
    Face outward is aligned to ``aligned_ecef``.

    Returns (axis_name in {x,y,z}, body +axis unit in ECEF).
    """
    face_u = _normalize_face(face)
    outward = FACE_OUTWARD_BODY[face_u]
    axis_index = int(np.argmax(np.abs(outward)))
    axis_name = "xyz"[axis_index]
    sign = float(outward[axis_index])
    return axis_name, _unit(sign * np.asarray(aligned_ecef, dtype=float))


def rtn_unit_vectors(
    position_ecef_m: np.ndarray,
    velocity_ecef_m_s: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (radial, along_track, cross_track) unit vectors in ECEF."""
    radial = _unit(position_ecef_m)
    cross = np.cross(position_ecef_m, velocity_ecef_m_s)
    cross = _unit(cross)
    along = _unit(np.cross(cross, radial))
    return radial, along, cross


def build_body_attitude_ecef(
    *,
    position_ecef_m: np.ndarray,
    velocity_ecef_m_s: np.ndarray,
    sun_ecef_unit: np.ndarray,
    sun_face: str,
    velocity_face: str,
    nadir_face: str | None = None,
) -> BodyAttitudeEcef:
    """
    Build ECEF←body DCM from catalog face assignments.

    Primary constraints: ``sun_face`` ∥ sun, ``velocity_face`` ∥ velocity.
    Orthonormalize prioritizing the velocity-constrained axis, then sun.
    ``nadir_face`` only sets the sign of its body axis when needed.
    """
    radial, along, _cross = rtn_unit_vectors(position_ecef_m, velocity_ecef_m_s)
    sun_u = _unit(sun_ecef_unit)
    vel_u = _unit(along)

    name_s, vec_s = body_axis_ecef_from_face(sun_face, sun_u)
    name_v, vec_v = body_axis_ecef_from_face(velocity_face, vel_u)
    if name_s == name_v:
        raise ValueError(
            f"sun_face={sun_face} and velocity_face={velocity_face} "
            "constrain the same body axis"
        )

    free = next(name for name in ("x", "y", "z") if name not in (name_s, name_v))

    # Gram-Schmidt: velocity axis first, then sun.
    a_hat = _unit(vec_v)
    b_perp = vec_s - float(np.dot(vec_s, a_hat)) * a_hat
    if np.linalg.norm(b_perp) < 1e-8:
        raise ValueError("Sun and velocity axes are nearly parallel")
    b_hat = _unit(b_perp)
    if float(np.dot(b_hat, vec_s)) < 0.0:
        b_hat = -b_hat

    axes: dict[str, np.ndarray] = {name_v: a_hat, name_s: b_hat}
    if free == "x":
        axes["x"] = _unit(np.cross(axes["y"], axes["z"]))
    elif free == "y":
        axes["y"] = _unit(np.cross(axes["z"], axes["x"]))
    else:
        axes["z"] = _unit(np.cross(axes["x"], axes["y"]))

    R = np.column_stack([axes["x"], axes["y"], axes["z"]])

    if nadir_face is not None:
        nadir = -radial
        name_n, vec_n_desired = body_axis_ecef_from_face(nadir_face, nadir)
        axis_index = "xyz".index(name_n)
        if float(np.dot(R[:, axis_index], vec_n_desired)) < 0.0:
            R = R.copy()
            R[:, axis_index] *= -1.0

    return BodyAttitudeEcef(
        R_ecef_from_body=R,
        sun_face=_normalize_face(sun_face),
        velocity_face=_normalize_face(velocity_face),
        nadir_face=_normalize_face(nadir_face) if nadir_face is not None else "",
    )


def classify_partner_geometry(
    *,
    position_ecef_m: np.ndarray,
    velocity_ecef_m_s: np.ndarray,
    attitude: BodyAttitudeEcef,
    isl_range_m: float,
    align_threshold: float = 0.8,
) -> PartnerGeometry:
    """
    Place a known target along the LCT boresight.

    - ~nadir  → ground station at altitude range (Earth surface along nadir)
    - ~zenith → still computable along boresight, but flagged unrealistic
    - ~±velocity or other → ISL-style target at ``isl_range_m``
    """
    radial, along, _ = rtn_unit_vectors(position_ecef_m, velocity_ecef_m_s)
    nadir = -radial
    zenith = radial
    boresight = attitude.lct_boresight_ecef
    altitude_m = max(float(np.linalg.norm(position_ecef_m) - EARTH_RADIUS_M), 1.0e3)

    dot_nadir = float(np.dot(boresight, nadir))
    dot_zenith = float(np.dot(boresight, zenith))
    dot_vel = float(np.dot(boresight, along))

    if dot_nadir >= align_threshold:
        return PartnerGeometry(
            mode="ground_nadir",
            range_m=altitude_m,
            direction_ecef=boresight,
            realistic_link=True,
            notes=(
                f"LCT~nadir; ground range~altitude={altitude_m/1e3:.0f} km"
            ),
        )
    if dot_zenith >= align_threshold:
        return PartnerGeometry(
            mode="zenith_proxy",
            range_m=float(isl_range_m),
            direction_ecef=boresight,
            realistic_link=False,
            notes="LCT~zenith; angle math OK but not a realistic Earth/ISL link",
        )
    if abs(dot_vel) >= align_threshold:
        sense = "along-track" if dot_vel > 0.0 else "anti-along-track"
        return PartnerGeometry(
            mode="isl_along_track",
            range_m=float(isl_range_m),
            direction_ecef=boresight,
            realistic_link=True,
            notes=f"LCT~{sense}; ISL range={isl_range_m/1e3:.0f} km",
        )
    return PartnerGeometry(
        mode="isl_along_boresight",
        range_m=float(isl_range_m),
        direction_ecef=boresight,
        realistic_link=True,
        notes=(
            f"LCT not aligned to RTN; ISL along boresight "
            f"range={isl_range_m/1e3:.0f} km"
        ),
    )


def position_error_to_stt_los_angle_urad(
    position_error_ecef_m: np.ndarray,
    attitude: BodyAttitudeEcef,
    range_m: float,
) -> np.ndarray:
    """
    Map chaser position error to STT-frame LOS angle [urad] (x, y).

    Partner is assumed along the LCT boresight (body -Z) at ``range_m``.
    Components match Femap ``far_field_los_angle_{x,y}`` style.
    """
    if range_m <= 0.0:
        raise ValueError("range_m must be positive")

    boresight = attitude.lct_boresight_ecef
    err = np.asarray(position_error_ecef_m, dtype=float)
    perp = err - float(np.dot(err, boresight)) * boresight
    tip_body = -(attitude.R_ecef_from_body.T @ perp) / range_m
    return np.array([tip_body[0], tip_body[1]], dtype=float) * 1.0e6
