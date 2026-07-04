import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# 0. Unit
# ============================================================
URAD = 1e-6
UM = 1e-6


# ============================================================
# 1. Truth thermal bias model
#    "Fourier + drift + model error" version
#    Later replace this part with TD x Femap result CSV.
# ============================================================
def thermal_deformation_truth_model(t,
                                    orbit_period=5400.0,
                                    baseline_m=1.0,
                                    seed=10):
    """
    Mock high-fidelity thermal deformation / LOS bias truth.

    This is intentionally more realistic than a pure sinusoid:
      1. Fourier-like orbital thermal response
      2. Eclipse transition disturbance
      3. Long-term drift
      4. Correlated model error / unmodeled thermal behavior

    Output:
        theta_true_urad: LOS bias caused by thermal deformation [urad], shape=(N, 2)

    Interpretation:
        Femap gives relative displacement dx, dy at optical reference points.
        LOS bias is approximated as theta = displacement / baseline.
    """
    rng = np.random.default_rng(seed)
    t = np.asarray(t)
    phi = 2.0 * np.pi * t / orbit_period

    # ------------------------------------------------------------
    # 1) Main periodic thermal response
    # ------------------------------------------------------------
    dx_um = (
        110.0 * np.sin(phi - 0.45)
        + 25.0 * np.sin(2.0 * phi + 0.70)
        + 12.0 * np.cos(3.0 * phi - 0.10)
    )
    dy_um = (
        75.0 * np.cos(phi + 0.90)
        + 22.0 * np.sin(2.0 * phi - 0.40)
        - 10.0 * np.cos(3.0 * phi + 0.30)
    )

    # ------------------------------------------------------------
    # 2) Eclipse flag and transition disturbance
    #    eclipse itself causes a quasi-static offset.
    #    ingress/egress cause sharp but smooth transient terms.
    # ------------------------------------------------------------
    eclipse = (np.sin(phi) < -0.25).astype(float)

    # Smooth transition-like disturbance using gradient of eclipse flag.
    # For a discrete simulation this acts like ingress / egress impulse.
    transition = np.gradient(eclipse)
    transition = transition / (np.max(np.abs(transition)) + 1e-12)

    dx_um += 35.0 * eclipse + 18.0 * transition
    dy_um += -25.0 * eclipse - 14.0 * transition

    # ------------------------------------------------------------
    # 3) Long-term drift
    #    Represents thermo-optical aging / operation-mode history.
    #    For one orbit this is small; over multiple orbits it matters.
    # ------------------------------------------------------------
    total_span = max(t[-1] - t[0], 1.0)
    normalized_time = (t - t[0]) / total_span
    dx_um += 35.0 * normalized_time
    dy_um += -22.0 * normalized_time

    # ------------------------------------------------------------
    # 4) Correlated model error
    #    This is not captured well by simple Fourier feedforward.
    # ------------------------------------------------------------
    ar = np.zeros((len(t), 2))
    sigma = 4.0
    rho = 0.92
    for k in range(1, len(t)):
        ar[k] = rho * ar[k - 1] + rng.normal(0.0, sigma, size=2)

    dx_um += ar[:, 0]
    dy_um += ar[:, 1]

    # displacement -> angular LOS bias
    theta_x_urad = (dx_um * UM / baseline_m) / URAD
    theta_y_urad = (dy_um * UM / baseline_m) / URAD

    return np.vstack([theta_x_urad, theta_y_urad]).T


# Backward-compatible alias.
def thermal_deformation_model(t, orbit_period=5400.0, baseline_m=1.0):
    return thermal_deformation_truth_model(
        t,
        orbit_period=orbit_period,
        baseline_m=baseline_m,
    )


# ============================================================
# 2. Lightweight correction models
# ============================================================
def fourier_features(t, orbit_period=5400.0, order=2, include_drift=False):
    """
    Lightweight onboard-friendly feature vector.

    Features:
        [1, sin(phi), cos(phi), sin(2phi), cos(2phi), ...]
    Optionally:
        normalized time as a linear drift term

    shape: (N, n_features)
    """
    t = np.asarray(t)
    phi = 2.0 * np.pi * t / orbit_period

    cols = [np.ones_like(t)]
    for n in range(1, order + 1):
        cols.append(np.sin(n * phi))
        cols.append(np.cos(n * phi))

    if include_drift:
        total_span = max(t[-1] - t[0], 1.0)
        tau = (t - t[0]) / total_span
        cols.append(tau)

    return np.vstack(cols).T


def ridge_fit(Phi, y, lam=1e-4):
    """
    Ridge regression for multi-output LOS bias fitting.

    Phi: (N, p)
    y  : (N, 2)
    returns:
        coef: (p, 2)
    """
    p = Phi.shape[1]
    A = Phi.T @ Phi + lam * np.eye(p)
    B = Phi.T @ y
    coef = np.linalg.solve(A, B)
    return coef


def rls_update(coef, P, phi, y, forgetting_factor=0.995):
    """
    Recursive least squares update for multi-output coefficients.

    coef: (p, 2)
    P   : (p, p)
    phi : (p,)
    y   : (2,)
    """
    phi = phi.reshape(-1, 1)
    denom = forgetting_factor + (phi.T @ P @ phi)[0, 0]
    K = (P @ phi) / denom  # (p, 1)

    y_hat = (phi.T @ coef).ravel()
    innovation = y - y_hat

    coef = coef + K @ innovation.reshape(1, -1)
    P = (P - K @ phi.T @ P) / forgetting_factor

    return coef, P, innovation


def build_static_prediction(theta_reference_urad):
    """
    Static bias correction: only the mean thermal LOS bias is corrected.
    """
    return np.mean(theta_reference_urad, axis=0)


def build_fourier_prediction(t,
                             theta_reference_urad,
                             orbit_period=5400.0,
                             order=2,
                             include_drift=False,
                             ridge_lam=1e-3):
    """
    Fit a lightweight Fourier model from high-fidelity reference data.
    """
    Phi = fourier_features(
        t,
        orbit_period=orbit_period,
        order=order,
        include_drift=include_drift,
    )
    coef = ridge_fit(Phi, theta_reference_urad, lam=ridge_lam)
    theta_hat = Phi @ coef
    return theta_hat, coef


def build_adaptive_prediction(t,
                              theta_true_urad,
                              initial_coef,
                              orbit_period=5400.0,
                              order=2,
                              include_drift=False,
                              reference_noise_urad=8.0,
                              reference_interval=3,
                              forgetting_factor=0.995,
                              seed=100):
    """
    Online adaptive correction model.

    At each acquisition opportunity:
      1. Predict thermal LOS bias using current coefficient.
      2. After acquisition, suppose a noisy residual/reference observation is available
         every `reference_interval` opportunities.
      3. Update the correction model by RLS.

    In a real system, the reference observation would come from:
      - PAT residual after successful acquisition
      - QD / FPM residual
      - received power based scan peak estimate
      - attitude / star tracker aided residual separation

    Here we use noisy theta_true_urad as the idealized reference signal.
    """
    rng = np.random.default_rng(seed)

    Phi = fourier_features(
        t,
        orbit_period=orbit_period,
        order=order,
        include_drift=include_drift,
    )

    coef = initial_coef.copy()
    p = Phi.shape[1]
    P = 1e3 * np.eye(p)

    theta_hat_adaptive = np.zeros_like(theta_true_urad)
    innovations = np.full_like(theta_true_urad, np.nan)

    for k in range(len(t)):
        phi_k = Phi[k]

        # Prediction used for scan center correction
        theta_hat_adaptive[k] = phi_k @ coef

        # Reference-triggered update after this opportunity
        reference_available = (k % reference_interval == 0)
        if reference_available:
            y_obs = theta_true_urad[k] + rng.normal(0.0, reference_noise_urad, size=2)
            coef, P, innovation = rls_update(
                coef,
                P,
                phi_k,
                y_obs,
                forgetting_factor=forgetting_factor,
            )
            innovations[k] = innovation

    return theta_hat_adaptive, innovations


# Previous name kept, but now it returns a deliberately imperfect FF estimate.
def feedforward_model(theta_true_urad, model_error_scale=0.15, seed=1):
    """
    Backward-compatible mock feedforward model.
    Prefer build_fourier_prediction() for the updated architecture.
    """
    rng = np.random.default_rng(seed)

    scale_x = 1.0 - model_error_scale
    scale_y = 1.0 - 0.7 * model_error_scale

    theta_hat = theta_true_urad.copy()
    theta_hat[:, 0] *= scale_x
    theta_hat[:, 1] *= scale_y
    theta_hat += rng.normal(0.0, 5.0, size=theta_hat.shape)

    return theta_hat


# ============================================================
# 3. Coarse acquisition scan model
# ============================================================
def rectangular_spiral_scan(max_range_urad=400.0, step_urad=40.0):
    """
    Generate rectangular spiral scan points around scan center.
    """
    points = [(0.0, 0.0)]
    n = int(max_range_urad // step_urad)

    for r in range(1, n + 1):
        vals = np.arange(-r, r + 1) * step_urad

        # top and bottom edges
        for x in vals:
            points.append((x, r * step_urad))
            points.append((x, -r * step_urad))

        # left and right edges
        for y in vals[1:-1]:
            points.append((r * step_urad, y))
            points.append((-r * step_urad, y))

    return np.array(points)


def coarse_acquisition(pointing_error_urad,
                       scan_points_urad,
                       detect_radius_urad=25.0,
                       dwell_time_s=0.1):
    """
    pointing_error_urad:
        target position relative to scan center [urad], shape=(2,)

    Acquisition succeeds when scan point is within detect_radius.
    """
    diffs = scan_points_urad - pointing_error_urad
    distances = np.linalg.norm(diffs, axis=1)

    hit = np.where(distances <= detect_radius_urad)[0]

    if len(hit) == 0:
        return False, np.nan, np.array([np.nan, np.nan]), np.nan

    idx = hit[0]
    acquisition_time = (idx + 1) * dwell_time_s
    residual_after_acq = pointing_error_urad - scan_points_urad[idx]

    return True, acquisition_time, residual_after_acq, idx


# ============================================================
# 4. Fine tracking model
# ============================================================
def fine_tracking(residual_initial_urad,
                  dt=0.01,
                  duration_s=2.0,
                  control_bandwidth_hz=5.0,
                  sensor_noise_urad=1.0,
                  seed=0):
    """
    Very simple first-order fine tracking model:
        error_dot = -k * error + noise
    """
    rng = np.random.default_rng(seed)
    n = int(duration_s / dt)
    error = np.zeros((n, 2))
    error[0] = residual_initial_urad

    k = 2.0 * np.pi * control_bandwidth_hz

    for i in range(1, n):
        noise = rng.normal(0.0, sensor_noise_urad, size=2)
        error[i] = error[i - 1] + dt * (-k * error[i - 1]) + noise * np.sqrt(dt)

    rms = np.sqrt(np.mean(np.sum(error[int(n / 2):] ** 2, axis=1)))
    return error, rms


# ============================================================
# 5. Simulation
# ============================================================
def evaluate_case(case_name,
                  theta_correction_hat,
                  theta_thermal_true,
                  nonthermal_error,
                  scan_points,
                  detect_radius_urad=25.0,
                  dwell_time_s=0.1,
                  fine_tracking_seed_offset=0,
                  store_tracking_example_index=None):
    """
    Evaluate one correction case.

    Actual target position relative to scan center:
        pointing_error = nonthermal_error + theta_true - theta_hat
    """
    results = []
    tracking_example = None

    for i in range(len(theta_thermal_true)):
        pointing_error = (
            nonthermal_error[i]
            + theta_thermal_true[i]
            - theta_correction_hat[i]
        )

        ok, tacq, residual, scan_idx = coarse_acquisition(
            pointing_error,
            scan_points,
            detect_radius_urad=detect_radius_urad,
            dwell_time_s=dwell_time_s,
        )

        if ok:
            track_error, rms = fine_tracking(
                residual,
                seed=fine_tracking_seed_offset + i,
            )

            if store_tracking_example_index is not None and i == store_tracking_example_index:
                tracking_example = track_error
        else:
            rms = np.nan

        initial_norm = np.linalg.norm(pointing_error)
        correction_norm = np.linalg.norm(theta_correction_hat[i])
        thermal_residual_norm = np.linalg.norm(theta_thermal_true[i] - theta_correction_hat[i])

        results.append([
            ok,
            tacq,
            rms,
            initial_norm,
            correction_norm,
            thermal_residual_norm,
            scan_idx,
        ])

    return np.array(results, dtype=float), tracking_example


def run_simulation():
    rng = np.random.default_rng(42)

    # Multiple orbits make drift and model error visible.
    orbit_period = 5400.0
    n_orbits = 3
    n_samples = 240
    t = np.linspace(0, n_orbits * orbit_period, n_samples)

    # High-fidelity reference-like LOS bias truth.
    # This is what TD x Femap would eventually replace.
    theta_thermal_true = thermal_deformation_truth_model(
        t,
        orbit_period=orbit_period,
        seed=10,
    )

    # ------------------------------------------------------------
    # Lightweight correction models
    # ------------------------------------------------------------

    # Static bias model: trained from the first orbit.
    train_mask = t <= orbit_period
    theta_train = theta_thermal_true[train_mask]
    t_train = t[train_mask]

    static_bias = build_static_prediction(theta_train)
    theta_hat_static = np.tile(static_bias, (len(t), 1))

    # Fourier feedforward model:
    # Train on first orbit, then use for later opportunities.
    _, coef_fourier = build_fourier_prediction(
        t_train,
        theta_train,
        orbit_period=orbit_period,
        order=2,
        include_drift=False,
        ridge_lam=1e-3,
    )
    Phi_all = fourier_features(
        t,
        orbit_period=orbit_period,
        order=2,
        include_drift=False,
    )
    theta_hat_fourier = Phi_all @ coef_fourier

    # Fourier + drift model:
    # This tests whether adding a small drift feature helps.
    _, coef_fourier_drift = build_fourier_prediction(
        t_train,
        theta_train,
        orbit_period=orbit_period,
        order=2,
        include_drift=True,
        ridge_lam=1e-3,
    )
    Phi_all_drift = fourier_features(
        t,
        orbit_period=orbit_period,
        order=2,
        include_drift=True,
    )
    theta_hat_fourier_drift = Phi_all_drift @ coef_fourier_drift

    # Adaptive model:
    # Start from deliberately imperfect Fourier coefficients.
    initial_coef_adaptive = coef_fourier.copy()
    initial_coef_adaptive[1:, :] *= np.array([0.88, 0.93])  # amplitude mismatch

    theta_hat_adaptive, adaptive_innovations = build_adaptive_prediction(
        t,
        theta_thermal_true,
        initial_coef_adaptive,
        orbit_period=orbit_period,
        order=2,
        include_drift=False,
        reference_noise_urad=8.0,
        reference_interval=3,
        forgetting_factor=0.995,
        seed=100,
    )

    # No correction
    theta_hat_none = np.zeros_like(theta_thermal_true)

    # Attitude/orbit/open-loop pointing error not caused by thermal deformation.
    # This is treated as pass-to-pass random uncertainty.
    nonthermal_error = rng.normal(0.0, 45.0, size=theta_thermal_true.shape)

    scan_points = rectangular_spiral_scan(max_range_urad=400.0, step_urad=40.0)

    correction_models = {
        "no_correction": theta_hat_none,
        "static_bias": theta_hat_static,
        "fourier_ff": theta_hat_fourier,
        "fourier_plus_drift": theta_hat_fourier_drift,
        "ff_plus_adaptive": theta_hat_adaptive,
    }

    results = {}
    tracking_examples = {}
    example_idx = len(t) // 2

    for idx, (name, theta_hat) in enumerate(correction_models.items()):
        data, track_example = evaluate_case(
            name,
            theta_hat,
            theta_thermal_true,
            nonthermal_error,
            scan_points,
            detect_radius_urad=25.0,
            dwell_time_s=0.1,
            fine_tracking_seed_offset=1000 * idx,
            store_tracking_example_index=example_idx if name == "ff_plus_adaptive" else None,
        )
        results[name] = data

        if track_example is not None:
            tracking_examples[name] = track_example

    model_outputs = {
        "static_bias": theta_hat_static,
        "fourier_ff": theta_hat_fourier,
        "fourier_plus_drift": theta_hat_fourier_drift,
        "ff_plus_adaptive": theta_hat_adaptive,
        "adaptive_innovations": adaptive_innovations,
    }

    return t, theta_thermal_true, model_outputs, results, tracking_examples


# ============================================================
# 6. Plot and summary
# ============================================================
def summarize_results(results):
    """
    Print performance metrics for each case.
    """
    for name, data in results.items():
        success = data[:, 0].astype(bool)
        success_rate = np.mean(success)

        mean_tacq = np.nanmean(data[:, 1])
        median_tacq = np.nanmedian(data[:, 1])
        p95_tacq = np.nanpercentile(data[:, 1], 95)

        mean_initial_error = np.nanmean(data[:, 3])
        p95_initial_error = np.nanpercentile(data[:, 3], 95)

        mean_thermal_residual = np.nanmean(data[:, 5])
        p95_thermal_residual = np.nanpercentile(data[:, 5], 95)

        print(f"\n{name}")
        print(f"  Success rate                : {success_rate * 100:.1f} %")
        print(f"  Mean acq time               : {mean_tacq:.2f} s")
        print(f"  Median acq time             : {median_tacq:.2f} s")
        print(f"  95% acq time                : {p95_tacq:.2f} s")
        print(f"  Mean initial error          : {mean_initial_error:.1f} urad")
        print(f"  95% initial error           : {p95_initial_error:.1f} urad")
        print(f"  Mean thermal residual       : {mean_thermal_residual:.1f} urad")
        print(f"  95% thermal residual        : {p95_thermal_residual:.1f} urad")


def plot_results(t, theta_true, model_outputs, results, tracking_examples):
    time_min = t / 60.0

    # ------------------------------------------------------------
    # Thermal LOS bias true vs model predictions
    # ------------------------------------------------------------
    plt.figure(figsize=(11, 5))
    plt.plot(time_min, theta_true[:, 0], label="True thermal LOS x", linewidth=2)
    plt.plot(time_min, model_outputs["fourier_ff"][:, 0], "--", label="Fourier FF x")
    plt.plot(time_min, model_outputs["ff_plus_adaptive"][:, 0], "-.", label="FF + adaptive x")
    plt.xlabel("Time [min]")
    plt.ylabel("LOS bias x [urad]")
    plt.title("Thermal LOS bias prediction: x-axis")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(11, 5))
    plt.plot(time_min, theta_true[:, 1], label="True thermal LOS y", linewidth=2)
    plt.plot(time_min, model_outputs["fourier_ff"][:, 1], "--", label="Fourier FF y")
    plt.plot(time_min, model_outputs["ff_plus_adaptive"][:, 1], "-.", label="FF + adaptive y")
    plt.xlabel("Time [min]")
    plt.ylabel("LOS bias y [urad]")
    plt.title("Thermal LOS bias prediction: y-axis")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # ------------------------------------------------------------
    # Acquisition time comparison
    # ------------------------------------------------------------
    plt.figure(figsize=(11, 5))
    for name, data in results.items():
        plt.plot(time_min, data[:, 1], "o-", markersize=3, label=name)
    plt.xlabel("Time [min]")
    plt.ylabel("Acquisition time [s]")
    plt.title("Coarse acquisition time")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # ------------------------------------------------------------
    # Initial pointing error comparison
    # ------------------------------------------------------------
    plt.figure(figsize=(11, 5))
    for name, data in results.items():
        plt.plot(time_min, data[:, 3], label=name)
    plt.xlabel("Time [min]")
    plt.ylabel("Initial pointing error norm [urad]")
    plt.title("Initial pointing error before coarse acquisition")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # ------------------------------------------------------------
    # Thermal residual after correction
    # ------------------------------------------------------------
    plt.figure(figsize=(11, 5))
    for name, data in results.items():
        if name == "no_correction":
            continue
        plt.plot(time_min, data[:, 5], label=name)
    plt.xlabel("Time [min]")
    plt.ylabel("Thermal residual norm [urad]")
    plt.title("Thermal LOS residual after correction")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # ------------------------------------------------------------
    # Distribution style plot using plain matplotlib
    # ------------------------------------------------------------
    labels = list(results.keys())
    acq_data = [results[name][:, 1][~np.isnan(results[name][:, 1])] for name in labels]

    plt.figure(figsize=(11, 5))
    plt.boxplot(acq_data, labels=labels, showfliers=True)
    plt.ylabel("Acquisition time [s]")
    plt.title("Acquisition time distribution")
    plt.grid(True, axis="y")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.show()

    initial_data = [results[name][:, 3] for name in labels]

    plt.figure(figsize=(11, 5))
    plt.boxplot(initial_data, labels=labels, showfliers=True)
    plt.ylabel("Initial pointing error norm [urad]")
    plt.title("Initial pointing error distribution")
    plt.grid(True, axis="y")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.show()

    # ------------------------------------------------------------
    # Fine tracking example
    # ------------------------------------------------------------
    if "ff_plus_adaptive" in tracking_examples:
        track_error = tracking_examples["ff_plus_adaptive"]
        time_track = np.arange(len(track_error)) * 0.01

        plt.figure(figsize=(10, 5))
        plt.plot(time_track, track_error[:, 0], label="Tracking error x")
        plt.plot(time_track, track_error[:, 1], label="Tracking error y")
        plt.xlabel("Time [s]")
        plt.ylabel("Tracking error [urad]")
        plt.title("Fine tracking pull-in after acquisition: FF + adaptive")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    t, theta_true, model_outputs, results, tracking_examples = run_simulation()

    summarize_results(results)
    plot_results(t, theta_true, model_outputs, results, tracking_examples)