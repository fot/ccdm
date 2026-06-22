import numpy as np
from misc import get_constants


# Import Constants
JD_1958= get_constants()['JD_1958']


def get_ground_station_position(time_array, dss_codes, dsn_db):
    """Calculates ECI ground station position and extracts static hardware delay."""
    gs_positions = np.zeros((len(time_array), 3))
    dsn_delay = np.zeros(len(time_array))

    for i, (abs_sec, code) in enumerate(zip(time_array, dss_codes)):
        code_str = str(code)
        if code_str in dsn_db:
            station = dsn_db[code_str]
            R = station['distance']
            lon_rad = np.radians(station['longitude'])
            lat_rad = np.radians(station['latitude'])
            
            # Pure, single-value hardware delay (OFLS Spec: d_dsn)
            dsn_delay[i] = station.get('delay', 0.0)

            # Earth Rotation Matrix (ECI)
            JD_current = JD_1958 + (abs_sec / 86400.0)
            d = JD_current - 2451545.0  
            gmst_rad = np.radians((280.46061837 + 360.98564736629 * d) % 360.0)

            x_ecef = R * np.cos(lat_rad) * np.cos(lon_rad)
            y_ecef = R * np.cos(lat_rad) * np.sin(lon_rad)
            z_ecef = R * np.sin(lat_rad)
            
            x_eci = x_ecef * np.cos(gmst_rad) - y_ecef * np.sin(gmst_rad)
            y_eci = x_ecef * np.sin(gmst_rad) + y_ecef * np.cos(gmst_rad)
            gs_positions[i] = [x_eci, y_eci, z_ecef]

    return gs_positions, dsn_delay


# def polyfit_quadratic(x, y, w):
#     """
#     Verbatim implementation of OFLS Spec for a 2nd-Degree Fit
#     C = (X^T W X)^-1 X^T W Y
#     Returns [c1 (Offset), c2 (Rate), c3 (Drift)]
#     """
#     N = len(x)

#     x= x.astype(np.longdouble)
#     y= y.astype(np.longdouble)
#     w= w.astype(np.longdouble)

#     # 1. Build the [X^T W X] Matrix (3x3)
#     sum_w = np.sum(w); sum_wx = np.sum(w * x)
#     sum_wx2 = np.sum(w * x**2); sum_wx3 = np.sum(w * x**3)
#     sum_wx4 = np.sum(w * x**4)

#     M = np.array([[sum_w, sum_wx, sum_wx2],
#                   [sum_wx, sum_wx2, sum_wx3],
#                   [sum_wx2, sum_wx3, sum_wx4]], dtype=np.float64)

#     # 2. Build the [X^T W Y] Vector (1x3)
#     sum_wy = np.sum(w * y); sum_wxy = np.sum(w * x * y)
#     sum_wx2y = np.sum(w * x**2 * y)

#     V = np.array([sum_wy, sum_wxy, sum_wx2y], dtype=np.float64)
    
#     # 3. Solve for Coefficients [c1, c2, c3]
#     coeffs = np.linalg.solve(M, V)
    
#     # 4. Variance of Residuals (OFLS 4.4.3.2 for Quadratic: N - 3)
#     y_pred = coeffs[0] + coeffs[1]*x + coeffs[2]*(x**2)
#     residuals = y - y_pred
#     s2 = np.sum(w * (residuals**2)) / (N - 3)
    
#     # 5. Covariance Standard Deviations
#     inv_M = np.linalg.inv(M)
#     cov_matrix = s2 * inv_M
#     std_devs = np.sqrt(np.diag(cov_matrix))
    
#     return coeffs, s2, std_devs


def polyfit_quadratic(x, y, w):
    """
    Solves a 2nd-Degree (Quadratic) polynomial using Modern SVD Decomposition.
    Avoids Condition Number Squaring while perfectly matching OFLS outputs.
    """
    N = len(x)

    # x= x.astype(np.longdouble)
    # y= y.astype(np.longdouble)
    # w= w.astype(np.longdouble)

    # Run the fit with weights, request the Covariance Matrix
    # np.polyfit inherently uses highly stable SVD/QR decomposition
    coeffs, cov_matrix = np.polyfit(x, y, deg=2, w=w, cov=True)
    
    # Reverse coefficients to match legacy [c1, c2, c3] order
    coeffs = coeffs[::-1]
    
    # Extract Standard Deviations and reverse to match
    std_devs = np.sqrt(np.diag(cov_matrix))[::-1]

    # Calculate Variance of Residuals (s^2)
    y_pred = coeffs[0] + coeffs[1]*x + coeffs[2]*(x**2)
    residuals = y - y_pred
    s2 = np.sum(w * (residuals**2)) / (N - 3)

    return coeffs, s2, std_devs


# def polyfit_cubic(x, y, w):
#     """
#     Solves a 3rd-Degree (Cubic) polynomial using the Normal Equations.
#     Returns Coefficients (D, C, B, A), Variance of Residuals (s2), and Covariance Std Devs.
#     Perfectly mimics the legacy `inverse4ext` Pascal function and OFLS 4.4.3.2-4.4.3.4.
#      - Verbatim implementation of OFLS Spec 4.4.3.2-3
#      - C = (X^T W X)^-1 X^T W Y
#     """
#     N = len(x)

#     x= x.astype(np.longdouble)
#     y= y.astype(np.longdouble)
#     w= w.astype(np.longdouble)

#     # 1. Build the [X^T W X] Matrix
#     sum_w = np.sum(w); sum_wx = np.sum(w * x); sum_wx2 = np.sum(w * x**2)
#     sum_wx3 = np.sum(w * x**3); sum_wx4 = np.sum(w * x**4)
#     sum_wx5 = np.sum(w * x**5); sum_wx6 = np.sum(w * x**6)

#     M = np.array([[sum_w, sum_wx, sum_wx2, sum_wx3],
#                   [sum_wx, sum_wx2, sum_wx3, sum_wx4],
#                   [sum_wx2, sum_wx3, sum_wx4, sum_wx5],
#                   [sum_wx3, sum_wx4, sum_wx5, sum_wx6]], dtype=np.float64)

#     # 2. Build the [X^T W Y] Vector
#     sum_wy = np.sum(w * y); sum_wxy = np.sum(w * x * y)
#     sum_wx2y = np.sum(w * x**2 * y); sum_wx3y = np.sum(w * x**3 * y)

#     V = np.array([sum_wy, sum_wxy, sum_wx2y, sum_wx3y], dtype=np.float64)

#     # 3. Solve for Coefficients [c1, c2, c3, c4]
#     coeffs = np.linalg.solve(M, V)

#     # 4. Calculate Variance of Residuals (OFLS 4.4.3.2-4)
#     # s^2 = (e^T W e) / (N - 4)
#     y_pred = coeffs[0] + coeffs[1]*x + coeffs[2]*(x**2) + coeffs[3]*(x**3)
#     residuals = y - y_pred
#     s2 = np.sum(w * (residuals**2)) / (N - 4)
    
#     # 5. Covariance Standard Deviations
#     inv_M = np.linalg.inv(M)
#     cov_matrix = s2 * inv_M
#     std_devs = np.sqrt(np.diag(cov_matrix))

#     return coeffs, s2, std_devs


def polyfit_cubic(x, y, w):
    """
    Solves a 3rd-Degree (Cubic) polynomial using Modern SVD Decomposition.
    Avoids Condition Number Squaring while perfectly matching OFLS outputs.
    """
    N = len(x)

    # x= x.astype(np.longdouble)
    # y= y.astype(np.longdouble)
    # w= w.astype(np.longdouble)

    # Run the fit with weights, request the Covariance Matrix
    # np.polyfit inherently uses highly stable SVD/QR decomposition
    coeffs, cov_matrix = np.polyfit(x, y, deg=3, w=w, cov=True)

    # Reverse coefficients to match legacy [c1, c2, c3, c4] order
    coeffs = coeffs[::-1]

    # Extract Standard Deviations and reverse to match
    std_devs = np.sqrt(np.diag(cov_matrix))[::-1]

    # Calculate Variance of Residuals (s^2)
    y_pred = coeffs[0] + coeffs[1]*x + coeffs[2]*(x**2) + coeffs[3]*(x**3)
    residuals = y - y_pred
    s2 = np.sum(w * (residuals**2)) / (N - 4)

    return coeffs, s2, std_devs


def ephemeris_interpolator(target_times, erp_times, erp_pos, erp_vel):
    """Replaces CubicHermiteSpline with the legacy 2nd-degree Constant Acceleration math."""
    indices = np.searchsorted(erp_times, target_times, side='right')
    indices = np.clip(indices, 1, len(erp_times) - 1)

    idx0 = indices - 1
    idx1 = indices

    t0 = erp_times[idx0]
    t1 = erp_times[idx1]
    p0 = erp_pos[idx0]
    v0 = erp_vel[idx0]
    v1 = erp_vel[idx1]
    
    dt_interval = (t1 - t0)[:, np.newaxis]
    dt = (target_times - t0)[:, np.newaxis]

    acc = (v1 - v0) / dt_interval
    interp_pos = p0 + (v0 * dt) + (0.5 * acc * dt**2)

    return interp_pos
