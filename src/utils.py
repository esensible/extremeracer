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

def intersection_point(pt_lat: float, pt_lon: float, point_heading: float, lat1: float, lon1: float, lat2: float, lon2: float, R: float = 6371000) -> Tuple[float, float]:
    def normalize_longitude(lon: float) -> float:
        return (lon + math.pi) % (2 * math.pi) - math.pi
    
    def initial_bearing(lat1, lon1, lat2, lon2):
        y = math.sin(lon2 - lon1) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
        return normalize_longitude(math.atan2(y, x))

    # Calculate the initial bearings from point 1 to point 2, and from the given point to point 1 and point 2
    bearing12 = initial_bearing(lat1, lon1, lat2, lon2)
    bearing1_pt = initial_bearing(lat1, lon1, pt_lat, pt_lon)
    bearing2_pt = initial_bearing(lat2, lon2, pt_lat, pt_lon)

    # Calculate the angular distance between point 1 and point 2
    delta_sigma12 = math.acos(math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))

    # Calculate the spherical excess E
    E = math.atan2(math.sin(bearing12 - bearing1_pt) * math.sin(delta_sigma12), math.cos(bearing2_pt) - math.cos(bearing1_pt) * math.cos(bearing12))

    # Calculate the angular distance between point 1 and the intersection point
    delta_sigma1i = math.atan2(math.sin(E), math.cos(bearing1_pt) + math.cos(E) * math.cos(bearing12))

    # Calculate the latitude and longitude of the intersection point
    intersection_lat = math.asin(math.sin(lat1) * math.cos(delta_sigma1i) + math.cos(lat1) * math.sin(delta_sigma1i) * math.cos(point_heading))
    intersection_lon = normalize_longitude(lon1 + math.atan2(math.sin(point_heading) * math.sin(delta_sigma1i) * math.cos(lat1), math.cos(delta_sigma1i) - math.sin(lat1) * math.sin(intersection_lat)))

    return intersection_lat, intersection_lon

def distance(lat1: float, lon1: float, lat2: float, lon2: float, R: float = 6371000) -> float:
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


def seconds_to_line(boat_lat: float, boat_lon: float, boat_heading: float, boat_speed: float, stbd_lat: float, stbd_lon: float, port_lat: float, port_lon: float, line_heading: float, R: float = 6371000) -> float:
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
        R (float, optional): Earth's radius in meters. Default is 6,371,000 meters.

    Returns:
        float: Perpendicular distance from the boat to the line defined by the starboard and port points in meters.
    """

    boat_speed = max(boat_speed, 1e-5) * KNOTS_TO_MPS # convert knots to m/s and ensure it's not zero

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

            lat1, lon1 = intersection_point(boat_lat, boat_lon, boat_heading, stbd_lat, stbd_lon, port_lat, port_lon, R)
            d = distance(boat_lat, boat_lon, lat1, lon1, R)
            print(boat_lat, boat_lon, boat_heading)
            print(stbd_lat, stbd_lon, port_lat, port_lon)
            print(lat1, lon1, d)
            return None, d / boat_speed

        elif simple_diff(line_heading, boat_heading) > 0:
            print("heading away")
        else:
            print("no cross")
    else:
        print("wrong side")

    stbd_distance = distance(boat_lat, boat_lon, stbd_lat, stbd_lon, R)
    port_distance = distance(boat_lat, boat_lon, port_lat, port_lon, R)
    if (stbd_distance < port_distance):
        return "stbd", stbd_distance / boat_speed
    else:
        return "port", port_distance / boat_speed