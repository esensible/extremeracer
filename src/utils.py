import logging
import math
from typing import Tuple

logger = logging.getLogger(__name__)

KNOTS_TO_MPS = 0.514444444


def local_radius(lat: float) -> float:
    """
    Calculate the Earth's radius at a given latitude (in radians) using the WGS84 ellipsoid model.

    Args:
        lat (float): Latitude in radians.

    Returns:
        float: Earth's radius at the given latitude in meters.
    """
    WGS_ELLIPSOID = (6378137.0, 6356752.314)

    f1 = math.pow((math.pow(WGS_ELLIPSOID[0], 2) * math.cos(lat)), 2)
    f2 = math.pow((math.pow(WGS_ELLIPSOID[1], 2) * math.sin(lat)), 2)
    f3 = math.pow((WGS_ELLIPSOID[0] * math.cos(lat)), 2)
    f4 = math.pow((WGS_ELLIPSOID[1] * math.sin(lat)), 2)

    radius = math.sqrt((f1 + f2) / (f3 + f4))

    return radius


# def intersection_point(pt_lat: float, pt_lon: float, pt_heading: float, lat1: float, lon1: float, lat2: float, lon2: float, R: float = 6371000) -> Tuple[float, float]:
#     import shapely.geometry as sg

#     distance = 5000
#     ep_lat = math.asin( math.sin(pt_lat)*math.cos(distance/R) + math.cos(pt_lat)*math.sin(distance/R)*math.cos(pt_heading))
#     ep_lon = pt_lon + math.atan2(math.sin(pt_heading)*math.sin(distance/R)*math.cos(pt_lat), math.cos(distance/R)-math.sin(pt_lat)*math.sin(lat2))

#     line = sg.LineString([sg.Point(math.degrees(lon1), math.degrees(lat1)), sg.Point(math.degrees(lon2), math.degrees(lat2))])
#     travel = sg.LineString([sg.Point(math.degrees(pt_lon), math.degrees(pt_lat)), sg.Point(math.degrees(ep_lon), math.degrees(ep_lat))])
#     cross = travel.intersection(line)

#     return math.radians(cross.y), math.radians(cross.x)


def great_circle_intersection(a_lat, a_lon, b_lat, b_lon, c_lat, c_lon, d_lat, d_lon):
    # TODO: Normal of start line doesn't need to be recalculated every time

    # cartesian coordinates
    xa, ya, za = (
        math.cos(a_lat) * math.cos(a_lon),
        math.cos(a_lat) * math.sin(a_lon),
        math.sin(a_lat),
    )
    xb, yb, zb = (
        math.cos(b_lat) * math.cos(b_lon),
        math.cos(b_lat) * math.sin(b_lon),
        math.sin(b_lat),
    )
    # normal vector, normalized
    n1 = (ya * zb - za * yb, za * xb - xa * zb, xa * yb - ya * xb)
    magnitude = math.sqrt(n1[0]**2 + n1[1]**2 + n1[2]**2)
    n1 = (n1[0] / magnitude, n1[1] / magnitude, n1[2] / magnitude)

    # cartesian coordinates
    xc, yc, zc = (
        math.cos(c_lat) * math.cos(c_lon),
        math.cos(c_lat) * math.sin(c_lon),
        math.sin(c_lat),
    )
    xd, yd, zd = (
        math.cos(d_lat) * math.cos(d_lon),
        math.cos(d_lat) * math.sin(d_lon),
        math.sin(d_lat),
    )
    # normal vector, normalized
    n2 = (yc * zd - zc * yd, zc * xd - xc * zd, xc * yd - yc * xd)
    magnitude = math.sqrt(n2[0]**2 + n2[1]**2 + n2[2]**2)
    n2 = (n2[0] / magnitude, n2[1] / magnitude, n2[2] / magnitude)

    # Compute line of intersection between two planes
    L = (
        n1[1] * n2[2] - n1[2] * n2[1],
        n1[2] * n2[0] - n1[0] * n2[2],
        n1[0] * n2[1] - n1[1] * n2[0],
    )

    # Find two intersection points
    int_lat1 = math.atan2(L[2], math.sqrt(L[0] ** 2 + L[1] ** 2))
    int_lon1 = math.atan2(L[1], L[0])
    int_lat2 = math.atan2(-L[2], math.sqrt(L[0] ** 2 + L[1] ** 2))
    int_lon2 = math.atan2(-L[1], -L[0])

    # Choose the intersection point that is closest to pt_lat, pt_lon
    if math.sqrt((int_lat1 - c_lat) ** 2 + (int_lon1 - c_lon) ** 2) < math.sqrt(
        (int_lat2 - c_lat) ** 2 + (int_lon2 - c_lon) ** 2
    ):
        return int_lat1, int_lon1
    else:
        return int_lat2, int_lon2


def intersection_point(
    pt_lat: float,
    pt_lon: float,
    pt_heading: float,
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    R: float = 6371000,
) -> Tuple[float, float]:
    # Calculate the end point of the second line using the distance and heading
    distance = 5000
    ep_lat = math.asin(
        math.sin(pt_lat) * math.cos(distance / R)
        + math.cos(pt_lat) * math.sin(distance / R) * math.cos(pt_heading)
    )
    ep_lon = pt_lon + math.atan2(
        math.sin(pt_heading) * math.sin(distance / R) * math.cos(pt_lat),
        math.cos(distance / R) - math.sin(pt_lat) * math.sin(ep_lat),
    )

    # Find the intersection point
    intersection_lat, intersection_lon = great_circle_intersection(
        lat1, lon1, lat2, lon2, pt_lat, pt_lon, ep_lat, ep_lon
    )

    return intersection_lat, intersection_lon


def distance(
    lat1: float, lon1: float, lat2: float, lon2: float, R: float = 6371000
) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    given their latitude and longitude coordinates in radians.

    Args:
        lat1 (float): Latitude of point 1 in radians.
        lon1 (float): Longitude of point 1 in radians.
        lat2 (float): Latitude of point 2 in radians.
        lon2 (float): Longitude of point 2 in radians.
        R (float, optional): Earth's radius in meters. Default is 6,371,000 meters.

    Returns:
        float: The great-circle distance between the two points in meters.
    """
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    )

    c = 2 * math.asin(math.sqrt(a))
    return R * c


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the initial bearing (also called forward azimuth) from point 1 to point 2
    given their latitude and longitude coordinates in radians.

    Args:
        lat1 (float): Latitude of point 1 in radians.
        lon1 (float): Longitude of point 1 in radians.
        lat2 (float): Latitude of point 2 in radians.
        lon2 (float): Longitude of point 2 in radians.

    Returns:
        float: Initial bearing from point 1 to point 2 in radians.
    """
    dL = lon2 - lon1
    X = math.cos(lat2) * math.sin(dL)
    Y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dL)
    bearing_rad = math.atan2(X, Y)

    # Normalize bearing to the range 0 to 2 * pi
    bearing_rad = (bearing_rad + 2 * math.pi) % (2 * math.pi)
    return bearing_rad


def simple_diff(heading1: float, heading2: float) -> float:
    heading1 = math.fmod(heading1, 2 * math.pi)
    heading2 = math.fmod(heading2, 2 * math.pi)

    if heading1 < 0:
        heading1 += 2 * math.pi

    if heading2 < 0:
        heading2 += 2 * math.pi

    diff = heading1 - heading2
    while diff > math.pi:
        diff -= 2 * math.pi
    while diff < -math.pi:
        diff += 2 * math.pi
    return diff


def seconds_to_line(
    boat_lat: float,
    boat_lon: float,
    boat_heading: float,
    boat_speed: float,
    stbd_lat: float,
    stbd_lon: float,
    port_lat: float,
    port_lon: float,
    line_heading: float,
    line_length: float,
    R: float = 6371000,
) -> Tuple[bool, int, float]:
    """
    Calculate the perpendicular distance from a boat to a line defined by two points (starboard and port) and a heading.

    Args:
        boat_lat (float): Latitude of the boat's position in radians.
        boat_lon (float): Longitude of the boat's position in radians.
        boat_heading (float): Heading of the boat in radians.
        boat_speed (float): Speed of the boat in knots.
        stbd_lat (float): Latitude of the starboard point in radians.
        stbd_lon (float): Longitude of the starboard point in radians.
        port_lat (float): Latitude of the port point in radians.
        port_lon (float): Longitude of the port point in radians.
        line_heading (float): Heading from the starboard point to the port point in radians.
        line_length (float): Length of the line in meters.
        R (float, optional): Earth's radius in meters. Default is 6,371,000 meters.

    Returns:
        float: % of the way along the line the boat will cross (0-100)
        float: time in seconds to the line
    """

    boat_speed = (
        max(boat_speed, 1e-5) * KNOTS_TO_MPS
    )  # convert knots to m/s and ensure it's not zero

    # Calculate the bearing from boat to stbd (stbd_heading) and boat to port (port_heading)
    stbd_heading = bearing(boat_lat, boat_lon, stbd_lat, stbd_lon)
    port_heading = bearing(boat_lat, boat_lon, port_lat, port_lon)

    angle_diff_stbd_port = simple_diff(stbd_heading, port_heading)

    if angle_diff_stbd_port > 0:
        # boat is on the right side of the line
        angle_diff_boat_stbd = simple_diff(stbd_heading, boat_heading)
        angle_diff_boat_port = simple_diff(boat_heading, port_heading)

        if angle_diff_boat_stbd > 0 and angle_diff_boat_port > 0:
            # boat heading intersects the line

            try:
                lat1, lon1 = intersection_point(
                    boat_lat,
                    boat_lon,
                    boat_heading,
                    stbd_lat,
                    stbd_lon,
                    port_lat,
                    port_lon,
                    R,
                )
                d = distance(boat_lat, boat_lon, lat1, lon1, R)
                # Distance from port (left) to line crossing - 0 to 100
                line_perc = distance(port_lat, port_lon, lat1, lon1, R) / line_length

                return True, line_perc, d / boat_speed
            except:
                return False, 50, 10000

        elif simple_diff(line_heading, boat_heading) > 0:
            print("heading away")
        else:
            print("no cross")
    else:
        print("wrong side")

    stbd_distance = distance(boat_lat, boat_lon, stbd_lat, stbd_lon, R)
    port_distance = distance(boat_lat, boat_lon, port_lat, port_lon, R)
    if stbd_distance < port_distance:
        return False, 1, stbd_distance / boat_speed
    else:
        return False, 0, port_distance / boat_speed
