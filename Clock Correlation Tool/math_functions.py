import numpy as np
from pathlib import Path
from scipy.interpolate import CubicSpline
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u

from misc import get_constants, load_dsn_database, log_callback


# Import Constants
constants = get_constants()
JD_1985 = constants['JD_1985']
# WGS84_A = constants['WGS84_A'] # 6378.137 (Semi-major axis in km)
# WGS84_E2 = constants['WGS84_E2'] # 1.0 / 298.257223563
# WGS84_FLATTENING = constants['WGS84_FLATTENING'] # 2.0 * WGS84_FLATTENING - WGS84_FLATTENING**2


def get_ground_station_position(time_array, dss_codes, time_offsets=None, legacy=True):
    """
    Calculates ECI (or GCRS) ground station position.
    
    legacy=True:  Replicates the Delphi spherical distance model and legacy GHA.
    legacy=False: Uses Astropy for rigorous IAU-2006 transformations, fully 
                  vectorized for high performance on massive arrays.
    """
    log_callback("Extrapolating Groundstation Positions...")

    def precess2000_matrix(jd):
        """Replicates the legacy precess2000 procedure from UNITASTR.PAS."""
        DtoR = 1.74532925199433E-02
        t = (jd - 2451545.0) / 36525.0
        zeta = 0.6406161 * t + 0.0000839 * (t**2) + 0.0000050 * (t**3)
        zee  = 0.6406161 * t + 0.0003041 * (t**2) + 0.0000051 * (t**3)
        theta = 0.5567530 * t - 0.0001185 * (t**2) - 0.0000116 * (t**3)

        czeta, szeta = np.cos(zeta * DtoR), np.sin(zeta * DtoR)
        czee, szee   = np.cos(zee * DtoR), np.sin(zee * DtoR)
        ctheta, stheta = np.cos(theta * DtoR), np.sin(theta * DtoR)

        pmat = np.zeros((3, 3))
        pmat[0, 0] = (czeta * ctheta * czee) - (szeta * szee)
        pmat[1, 0] = (-szeta * ctheta * czee) - (czeta * szee)
        pmat[2, 0] = -stheta * czee
        pmat[0, 1] = (czeta * ctheta * szee) + (szeta * czee)
        pmat[1, 1] = (-szeta * ctheta * szee) + (czeta * czee)
        pmat[2, 1] = -stheta * szee
        pmat[0, 2] = czeta * stheta
        pmat[1, 2] = -szeta * stheta
        pmat[2, 2] = ctheta
        return pmat

    def compute_gha_from_jd(jd_current):
        """Calculates GHA directly from an absolute Julian Date."""
        twopi = 2.0 * np.pi
        
        # 0h UT boundary truncation matching legacy handling
        jd_int = np.floor(jd_current - 0.5) + 0.5
        T = (jd_int - 2451545.0) / 36525.0

        GMST0 = 24110.54841 + (8640184.812866 * T) + (0.093104 * (T ** 2))
        GHA0 = (twopi * GMST0 / 86400.0) % twopi

        sec_of_day = (jd_current - jd_int) * 86400.0
        GHA = GHA0 + 1.00273790935 * twopi * (sec_of_day / 86400.0)
        return GHA % twopi

    dsn_db = load_dsn_database(Path(__file__).parent.resolve() / "dsn_data.json")

    # Pre-allocate output arrays
    gs_positions = np.zeros((len(time_array), 3), dtype=np.float64)
    dsn_delay = np.zeros(len(time_array), dtype=np.float64)

    # Find unique stations in this dataset to avoid redundant calculations
    unique_stations = np.unique(dss_codes)

    for code in unique_stations:
        code_str = str(code)
        if code_str not in dsn_db:
            continue
            
        station = dsn_db[code_str]
        
        # Create a boolean mask for all data points belonging to this station
        mask = (dss_codes == code)
        
        # Populate constant station delays for these indices
        dsn_delay[mask] = station['delay']

        # Vectorized time offset extraction and Julian Date calculation
        offsets = time_offsets[mask] if time_offsets is not None else 0.0
        jd_array = JD_1985 + ((time_array[mask] - offsets) / 86400.0)

        if legacy:
            # --- LEGACY MODE: Iterative Spherical Model ---
            lon_rad = np.radians(station['longitude'])
            lat_rad = np.radians(station['latitude'])
            R = station['distance']
            
            x_ecef = R * np.cos(lat_rad) * np.cos(lon_rad)
            y_ecef = R * np.cos(lat_rad) * np.sin(lon_rad)
            z_ecef = R * np.sin(lat_rad)
            pos_ecef = np.array([x_ecef, y_ecef, z_ecef])
            
            # Since the legacy precession functions are scalar, we loop 
            # only over the masked indices. (Can also be vectorized later if needed)
            masked_indices = np.where(mask)[0]
            for idx, jd in zip(masked_indices, jd_array):
                pmat = precess2000_matrix(jd)
                gha = compute_gha_from_jd(jd)
                c, s = np.cos(gha), np.sin(gha)

                rot_mat = np.array([
                    [c, -s, 0.0], 
                    [s,  c, 0.0], 
                    [0.0, 0.0, 1.0]
                ])
                gs_positions[idx] = (pmat @ rot_mat) @ pos_ecef

        else:
            # --- MODERN MODE: Vectorized Astropy Transformation ---
            lon_deg = station['longitude']
            lat_deg = station['latitude']
            alt_km = station.get('height', 0.0)

            loc = EarthLocation.from_geodetic(
                lon=lon_deg * u.deg, 
                lat=lat_deg * u.deg, 
                height=alt_km * u.km
            )

            # Create a single Time object containing the entire array of JDs
            t_array = Time(jd_array, format='jd', scale='utc')

            # Astropy processes the entire array of times simultaneously 
            gcrs_pos = loc.get_gcrs(t_array)

            # Extract Cartesian arrays and map them back to the correct indices
            gs_positions[mask, 0] = gcrs_pos.cartesian.x.to_value(u.km)
            gs_positions[mask, 1] = gcrs_pos.cartesian.y.to_value(u.km)
            gs_positions[mask, 2] = gcrs_pos.cartesian.z.to_value(u.km)

    return gs_positions, dsn_delay


def two_pass_coefficient_solver(x, y, scale=1e-6, initrate=0.25625000600):
    """Executes a two-pass solver using a dynamic 3-sigma rejection filter
       to accommodate modern ephemeris geometry without truncating the pass.
    """
    log_callback("Solving for coefficients...")

    if len(x) < 3:
        return {"status": "INSUFFICIENT_DATA"}

    def build_amat_avec(x_arr, y_arr):
        x_scaled = x_arr * scale
        y_stripped = y_arr - (initrate * x_arr)

        N = len(x_arr)
        sum_x1 = np.sum(x_scaled)
        sum_x2 = np.sum(x_scaled**2)
        sum_x3 = np.sum(x_scaled**3)
        sum_x4 = np.sum(x_scaled**4)

        amat = np.array(
            [[N, sum_x1, sum_x2], [sum_x1, sum_x2, sum_x3], [sum_x2, sum_x3, sum_x4]],
            dtype=np.float64,
        )

        avec = np.array(
            [np.sum(y_stripped),
             np.sum(x_scaled * y_stripped),
             np.sum((x_scaled**2) * y_stripped)],
            dtype=np.float64,
        )

        return amat, avec

    def solve_coeffs(amat, avec):
        try:
            p_raw = np.linalg.inv(amat) @ avec
            return {
                "T0": p_raw[0],
                "R0": (p_raw[1] * scale) + initrate,
                "D0": p_raw[2] * (scale**2) * 2.0,
            }
        except np.linalg.LinAlgError:
            return None

    # --- PASS 1: Initial Fit ---
    amat_p1, avec_p1 = build_amat_avec(x, y)
    coeffs_p1 = solve_coeffs(amat_p1, avec_p1)

    if coeffs_p1 is None:
        return {"status": "SOLVE_FAILED_P1"}

    # --- RESIDUAL PRUNING (Dynamic 3-Sigma Logic) ---
    y_predicted = (
        coeffs_p1["T0"]
        + (coeffs_p1["R0"] * x)
        + ((coeffs_p1["D0"] / 2.0) * (x**2))
    )
    resid = y_predicted - y

    # Calculate standard deviation and set dynamic limit
    sigma = np.std(resid, ddof=1)
    dynamic_limit = 3 * sigma

    # Filter points where the absolute residual is within the limit
    valid_mask = np.abs(resid) <= dynamic_limit

    x_clean = x[valid_mask]
    y_clean = y[valid_mask]

    if len(x_clean) < 3:
        return {"status": "INSUFFICIENT_CLEAN_DATA"}

    # --- PASS 2: Re-Fit on Cleaned Data ---
    amat_p2, avec_p2 = build_amat_avec(x_clean, y_clean)
    coeffs_p2 = solve_coeffs(amat_p2, avec_p2)

    if coeffs_p2 is None:
        return {"status": "SOLVE_FAILED_P2"}

    # Degrees of freedom for 3-parameter quadratic fit (T0, R0, D0)
    n_clean = len(x_clean)
    dof = n_clean - 3
    if dof <= 0:
        return {"status": "INSUFFICIENT_DOF"}

    # Variance of Residuals evaluated on the cleaned dataset using physical coefficients
    y_pred_clean = coeffs_p2["T0"] + (coeffs_p2["R0"] * x_clean) + ((coeffs_p2["D0"] / 2.0) * (x_clean**2))
    residuals = y_clean - y_pred_clean

    w = 1.0  # Unit weights assumption for unweighted least squares
    sum_w = float(n_clean)
    sse = np.sum(w * (residuals**2))
    s2 = sse / dof

    # OFLS Spec 4.4.3.3: Determine Uncertainty For Quadratic Least Squares Fit
    sigma_meas = np.sqrt(s2)  # random error of an individual measurement
    n_sqrt = np.sqrt(sum_w)  # n^(1/2) where n = statistical weight sum
    d = (np.max(x_clean) - np.min(x_clean)) / 2.0  # half-duration of clean data

    base_unc = sigma_meas / n_sqrt

    sigma_0 = np.sqrt(9.0 / 4.0) * base_unc
    sigma_1 = np.sqrt(3.0) * base_unc / d
    sigma_2 = np.sqrt(45.0 / 4.0) * base_unc / (d**2)
    std_devs = np.array([sigma_0, sigma_1, sigma_2], dtype=np.float64)

    return {
        "status": "SUCCESS",
        "coeffs": coeffs_p2,
        "amat_p2": amat_p2,
        "avec_p2": avec_p2,
        "std_devs": std_devs,
        "s2": s2,
        "sse": sse,
        "n_clean": len(x_clean),
    }


def ephemeris_interpolator(target_times, erp_times, erp_pos, erp_vel, legacy_mode=True):
    """
    Interpolates spacecraft position and velocity from ephemeris data.
    
    legacy=True:  Vectorized Cubic Hermite Spline matching the legacy Delphi 
                  tool. Uses 2-point bounds (C1 continuous).
    legacy=False: Global Cubic Spline fit enforcing smooth spacecraft 
                  acceleration across all boundaries (C2 continuous).
    """
    log_callback("Extrapolating Spacecraft Ephemeris...")
    target_times = np.asarray(target_times, dtype=np.float64)
    erp_times = np.asarray(erp_times, dtype=np.float64)
    erp_pos = np.asarray(erp_pos, dtype=np.float64)
    erp_vel = np.asarray(erp_vel, dtype=np.float64)

    if legacy_mode:
        # --- LEGACY MODE: Piecewise Cubic Hermite Spline ---
        # Find the nearest preceding ephemeris index
        indices = np.searchsorted(erp_times, target_times, side='right')
        indices = np.clip(indices, 1, len(erp_times) - 1)

        idx0 = indices - 1
        idx1 = indices

        t0 = erp_times[idx0]
        p0 = erp_pos[idx0]
        v0 = erp_vel[idx0]

        t1 = erp_times[idx1]
        p1 = erp_pos[idx1]
        v1 = erp_vel[idx1]

        # Time intervals (1D arrays of length N)
        T = t1 - t0
        t = target_times - t0

        # Avoid division by zero if timestamps overlap
        with np.errstate(divide='ignore', invalid='ignore'):
            tau = np.where(T != 0, t / T, 0.0)

        # Hermite basis functions
        tau2 = tau ** 2
        tau3 = tau ** 3

        h00 = 2.0 * tau3 - 3.0 * tau2 + 1.0
        h10 = tau3 - 2.0 * tau2 + tau
        h01 = -2.0 * tau3 + 3.0 * tau2
        h11 = tau3 - tau2

        # Expand dims for broadcasting against (N, 3) position/velocity arrays
        h00_ext = h00[:, np.newaxis]
        h10_ext = h10[:, np.newaxis]
        h01_ext = h01[:, np.newaxis]
        h11_ext = h11[:, np.newaxis]
        T_ext = T[:, np.newaxis]

        # Position interpolation (Shape: N, 3)
        interp_pos = (h00_ext * p0 +
                      h10_ext * (v0 * T_ext) +
                      h01_ext * p1 +
                      h11_ext * (v1 * T_ext))

        # Derivative of Hermite basis functions
        dh00 = 6.0 * tau2 - 6.0 * tau
        dh10 = 3.0 * tau2 - 4.0 * tau + 1.0
        dh01 = -6.0 * tau2 + 6.0 * tau
        dh11 = 3.0 * tau2 - 2.0 * tau

        dh00_ext = dh00[:, np.newaxis]
        dh10_ext = dh10[:, np.newaxis]
        dh01_ext = dh01[:, np.newaxis]
        dh11_ext = dh11[:, np.newaxis]

        # Velocity interpolation scaled by 1/T due to chain rule (dt/tau)
        with np.errstate(divide='ignore', invalid='ignore'):
            inv_T = np.where(T != 0, 1.0 / T, 0.0)[:, np.newaxis]

        interp_vel = inv_T * (
                      dh00_ext * p0 +
                      dh10_ext * (v0 * T_ext) +
                      dh01_ext * p1 +
                      dh11_ext * (v1 * T_ext)
        )

        return interp_pos, interp_vel

    else:
        # --- MODERN MODE: SciPy Global Cubic Spline ---
        # Fits a continuous spline to the ephemeris positions.
        # bc_type='clamped' forces the spline boundaries to exactly match 
        # the known velocity at the first and last ephemeris points.

        spline = CubicSpline(erp_times, erp_pos, bc_type=((1, erp_vel[0]), (1, erp_vel[-1])))

        # Evaluate the spline for position
        interp_pos = spline(target_times)

        # Evaluate the first derivative of the spline for perfectly consistent velocity
        interp_vel = spline(target_times, 1)

        return interp_pos, interp_vel
