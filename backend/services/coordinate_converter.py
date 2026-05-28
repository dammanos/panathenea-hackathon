"""Coordinate conversions between EGSA87, WGS84, GGRS87, and TM07.

Pipeline:
  EGSA87 -> TM reverse (GRS80) -> GGRS87 geographic -> Helmert -> WGS84
  WGS84 -> inverse Helmert -> GGRS87 geographic -> TM forward (GRS80) -> EGSA87
  TM07 uses the same TM projection but on WGS84 ellipsoid (no Helmert).
"""

import math

# ---------------------------------------------------------------------------
# Ellipsoid constants
# ---------------------------------------------------------------------------
GRS80_A = 6_378_137.0
GRS80_F = 1.0 / 298.257222101
GRS80_B = GRS80_A * (1.0 - GRS80_F)
GRS80_E2 = 2.0 * GRS80_F - GRS80_F ** 2  # first eccentricity squared
GRS80_EP2 = GRS80_E2 / (1.0 - GRS80_E2)   # second eccentricity squared

WGS84_A = 6_378_137.0
WGS84_F = 1.0 / 298.257223563
WGS84_B = WGS84_A * (1.0 - WGS84_F)
WGS84_E2 = 2.0 * WGS84_F - WGS84_F ** 2
WGS84_EP2 = WGS84_E2 / (1.0 - WGS84_E2)

# ---------------------------------------------------------------------------
# Greek Grid Transverse Mercator parameters
# ---------------------------------------------------------------------------
TM_LON0 = math.radians(24.0)   # central meridian
TM_K0 = 0.9996                  # scale factor
TM_FE = 500_000.0               # false easting
TM_FN = 0.0                     # false northing

# ---------------------------------------------------------------------------
# 3-parameter Helmert: GGRS87 -> WGS84
# ---------------------------------------------------------------------------
DX = -199.87
DY = 74.79
DZ = 246.62


# ---------------------------------------------------------------------------
# Meridional arc length
# ---------------------------------------------------------------------------

def _meridional_arc(phi: float, a: float, e2: float) -> float:
    """Compute meridional arc from equator to latitude phi."""
    e4 = e2 * e2
    e6 = e4 * e2
    A0 = 1.0 - e2 / 4.0 - 3.0 * e4 / 64.0 - 5.0 * e6 / 256.0
    A2 = 3.0 / 8.0 * (e2 + e4 / 4.0 + 15.0 * e6 / 128.0)
    A4 = 15.0 / 256.0 * (e4 + 3.0 * e6 / 4.0)
    A6 = 35.0 * e6 / 3072.0
    return a * (
        A0 * phi
        - A2 * math.sin(2.0 * phi)
        + A4 * math.sin(4.0 * phi)
        - A6 * math.sin(6.0 * phi)
    )


def _footpoint_latitude(M: float, a: float, e2: float) -> float:
    """Compute footpoint latitude from meridional arc distance M."""
    e4 = e2 * e2
    e6 = e4 * e2
    A0 = 1.0 - e2 / 4.0 - 3.0 * e4 / 64.0 - 5.0 * e6 / 256.0
    mu = M / (a * A0)

    e1 = (1.0 - math.sqrt(1.0 - e2)) / (1.0 + math.sqrt(1.0 - e2))
    e1_2 = e1 * e1
    e1_3 = e1_2 * e1
    e1_4 = e1_3 * e1

    return (
        mu
        + (3.0 * e1 / 2.0 - 27.0 * e1_3 / 32.0) * math.sin(2.0 * mu)
        + (21.0 * e1_2 / 16.0 - 55.0 * e1_4 / 32.0) * math.sin(4.0 * mu)
        + (151.0 * e1_3 / 96.0) * math.sin(6.0 * mu)
        + (1097.0 * e1_4 / 512.0) * math.sin(8.0 * mu)
    )


# ---------------------------------------------------------------------------
# Transverse Mercator forward / reverse (Redfearn)
# ---------------------------------------------------------------------------

def _tm_forward(
    lat_rad: float, lon_rad: float,
    a: float, e2: float, ep2: float,
    lon0: float, k0: float, fe: float, fn: float,
) -> tuple[float, float]:
    """Geographic -> Transverse Mercator (Redfearn forward, 6th-order)."""
    phi = lat_rad
    dlam = lon_rad - lon0

    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    tan_phi = math.tan(phi)

    N = a / math.sqrt(1.0 - e2 * sin_phi ** 2)
    T = tan_phi ** 2
    C = ep2 * cos_phi ** 2
    A = dlam * cos_phi
    M = _meridional_arc(phi, a, e2)

    A2 = A * A
    A3 = A2 * A
    A4 = A3 * A
    A5 = A4 * A
    A6 = A5 * A

    easting = fe + k0 * N * (
        A
        + A3 / 6.0 * (1.0 - T + C)
        + A5 / 120.0 * (5.0 - 18.0 * T + T * T + 72.0 * C - 58.0 * ep2)
    )

    northing = fn + k0 * (
        M
        + N * tan_phi * (
            A2 / 2.0
            + A4 / 24.0 * (5.0 - T + 9.0 * C + 4.0 * C * C)
            + A6 / 720.0 * (61.0 - 58.0 * T + T * T + 600.0 * C - 330.0 * ep2)
        )
    )

    return easting, northing


def _tm_reverse(
    easting: float, northing: float,
    a: float, e2: float, ep2: float,
    lon0: float, k0: float, fe: float, fn: float,
) -> tuple[float, float]:
    """Transverse Mercator -> Geographic (Redfearn reverse, 6th-order)."""
    M = (northing - fn) / k0
    phi1 = _footpoint_latitude(M, a, e2)

    sin_phi1 = math.sin(phi1)
    cos_phi1 = math.cos(phi1)
    tan_phi1 = math.tan(phi1)

    N1 = a / math.sqrt(1.0 - e2 * sin_phi1 ** 2)
    R1 = a * (1.0 - e2) / ((1.0 - e2 * sin_phi1 ** 2) ** 1.5)
    T1 = tan_phi1 ** 2
    C1 = ep2 * cos_phi1 ** 2
    D = (easting - fe) / (N1 * k0)

    D2 = D * D
    D3 = D2 * D
    D4 = D3 * D
    D5 = D4 * D
    D6 = D5 * D

    lat = phi1 - (N1 * tan_phi1 / R1) * (
        D2 / 2.0
        - D4 / 24.0 * (5.0 + 3.0 * T1 + 10.0 * C1 - 4.0 * C1 * C1 - 9.0 * ep2)
        + D6 / 720.0 * (61.0 + 90.0 * T1 + 298.0 * C1 + 45.0 * T1 * T1
                         - 252.0 * ep2 - 3.0 * C1 * C1)
    )

    lon = lon0 + (1.0 / cos_phi1) * (
        D
        - D3 / 6.0 * (1.0 + 2.0 * T1 + C1)
        + D5 / 120.0 * (5.0 - 2.0 * C1 + 28.0 * T1 - 3.0 * C1 * C1
                         + 8.0 * ep2 + 24.0 * T1 * T1)
    )

    return lat, lon


# ---------------------------------------------------------------------------
# ECEF <-> Geographic
# ---------------------------------------------------------------------------

def _geo_to_ecef(
    lat_rad: float, lon_rad: float, h: float,
    a: float, e2: float,
) -> tuple[float, float, float]:
    """Geographic (radians) + ellipsoidal height -> ECEF XYZ."""
    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    N = a / math.sqrt(1.0 - e2 * sin_lat ** 2)
    X = (N + h) * cos_lat * math.cos(lon_rad)
    Y = (N + h) * cos_lat * math.sin(lon_rad)
    Z = (N * (1.0 - e2) + h) * sin_lat
    return X, Y, Z


def _ecef_to_geo(
    X: float, Y: float, Z: float,
    a: float, e2: float,
) -> tuple[float, float, float]:
    """ECEF XYZ -> Geographic (radians) + ellipsoidal height. Bowring iterative."""
    b = a * math.sqrt(1.0 - e2)
    ep2 = (a * a - b * b) / (b * b)
    p = math.sqrt(X * X + Y * Y)
    lon = math.atan2(Y, X)

    # Bowring initial approximation
    theta = math.atan2(Z * a, p * b)
    lat = math.atan2(
        Z + ep2 * b * math.sin(theta) ** 3,
        p - e2 * a * math.cos(theta) ** 3,
    )

    # Iterate for convergence
    for _ in range(10):
        sin_lat = math.sin(lat)
        N = a / math.sqrt(1.0 - e2 * sin_lat ** 2)
        lat_new = math.atan2(Z + e2 * N * sin_lat, p)
        if abs(lat_new - lat) < 1e-14:
            break
        lat = lat_new

    sin_lat = math.sin(lat)
    N = a / math.sqrt(1.0 - e2 * sin_lat ** 2)
    h = p / math.cos(lat) - N if abs(math.cos(lat)) > 1e-10 else abs(Z) / abs(sin_lat) - N * (1.0 - e2)

    return lat, lon, h


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def egsa87_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """EGSA87 (easting, northing) -> WGS84 (lat_deg, lon_deg).

    Pipeline: TM reverse on GRS80 -> GGRS87 geo -> ECEF -> Helmert -> WGS84 geo.
    """
    # 1. TM reverse -> GGRS87 geographic (radians)
    lat_ggrs, lon_ggrs = _tm_reverse(
        x, y, GRS80_A, GRS80_E2, GRS80_EP2, TM_LON0, TM_K0, TM_FE, TM_FN,
    )

    # 2. GGRS87 geographic -> ECEF on GRS80
    X, Y, Z = _geo_to_ecef(lat_ggrs, lon_ggrs, 0.0, GRS80_A, GRS80_E2)

    # 3. 3-parameter Helmert GGRS87 -> WGS84
    X += DX
    Y += DY
    Z += DZ

    # 4. ECEF -> WGS84 geographic
    lat_wgs, lon_wgs, _ = _ecef_to_geo(X, Y, Z, WGS84_A, WGS84_E2)

    return math.degrees(lat_wgs), math.degrees(lon_wgs)


def wgs84_to_egsa87(lat: float, lon: float) -> tuple[float, float]:
    """WGS84 (lat_deg, lon_deg) -> EGSA87 (easting, northing).

    Pipeline: WGS84 geo -> ECEF -> inverse Helmert -> GGRS87 geo -> TM forward on GRS80.
    """
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    # 1. WGS84 geographic -> ECEF on WGS84
    X, Y, Z = _geo_to_ecef(lat_rad, lon_rad, 0.0, WGS84_A, WGS84_E2)

    # 2. Inverse Helmert: WGS84 -> GGRS87
    X -= DX
    Y -= DY
    Z -= DZ

    # 3. ECEF -> GGRS87 geographic on GRS80
    lat_ggrs, lon_ggrs, _ = _ecef_to_geo(X, Y, Z, GRS80_A, GRS80_E2)

    # 4. TM forward -> EGSA87
    easting, northing = _tm_forward(
        lat_ggrs, lon_ggrs, GRS80_A, GRS80_E2, GRS80_EP2, TM_LON0, TM_K0, TM_FE, TM_FN,
    )

    return easting, northing


def wgs84_to_tm07(lat: float, lon: float) -> tuple[float, float]:
    """WGS84 (lat_deg, lon_deg) -> TM07 (easting, northing).

    Same TM projection parameters but directly on WGS84 ellipsoid (no Helmert).
    """
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    return _tm_forward(
        lat_rad, lon_rad, WGS84_A, WGS84_E2, WGS84_EP2, TM_LON0, TM_K0, TM_FE, TM_FN,
    )


def tm07_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """TM07 (easting, northing) -> WGS84 (lat_deg, lon_deg).

    TM reverse directly on WGS84 ellipsoid.
    """
    lat_rad, lon_rad = _tm_reverse(
        x, y, WGS84_A, WGS84_E2, WGS84_EP2, TM_LON0, TM_K0, TM_FE, TM_FN,
    )
    return math.degrees(lat_rad), math.degrees(lon_rad)
