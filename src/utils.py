import logging
import math
import shapely.geometry as shapely_geom

logger = logging.getLogger(__name__)

def get_radius_at_lat(lat): # radians
    WGS_ELLIPSOID = (6378137.0, 6356752.314)

    f1 = math.pow((math.pow(WGS_ELLIPSOID[0], 2) * math.cos(lat)), 2)
    f2 = math.pow((math.pow(WGS_ELLIPSOID[1], 2) * math.sin(lat)), 2)
    f3 = math.pow((WGS_ELLIPSOID[0] * math.cos(lat)), 2)
    f4 = math.pow((WGS_ELLIPSOID[1] * math.sin(lat)), 2)

    radius = math.sqrt((f1 + f2) / (f3 + f4))

    return radius


def _distance(pt1, pt2, R=6371000):
    
    lon1, lat1, lon2, lat2 = map(math.radians, [pt1.x, pt1.y, pt2.x, pt2.y])

    # R = get_radius_at_lat((lat1 + lat2) / 2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat/2.0)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2.0)**2

    c = 2 * math.asin(math.sqrt(a))
    return R * c


def _fwd(lon1, lat1, heading_radians, distance=1000, R=6371000):

    lon1, lat1 = map(math.radians, [lon1, lat1])

    # R = get_radius_at_lat(lat1)
    
    lat2 = math.asin( math.sin(lat1)*math.cos(distance/R) + math.cos(lat1)*math.sin(distance/R)*math.cos(heading_radians))

    lon2 = lon1 + math.atan2(math.sin(heading_radians)*math.sin(distance/R)*math.cos(lat1), math.cos(distance/R)-math.sin(lat1)*math.sin(lat2))

    return map(math.degrees, [lon2, lat2])

def _bearing(pt1, pt2):
    lon1, lat1, lon2, lat2 = map(math.radians, [pt1.x, pt1.y, pt2.x, pt2.y])

    dL = lon2 - lon1
    X = math.cos(lat2) * math.sin(dL)
    Y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dL)
    return math.atan2(X, Y)

def _distance_to_line(line, nacra_pt, heading):
    # R = get_radius_at_lat(math.radians(nacra[1]))

    heading = math.radians(heading) if heading <= 180 else math.radians(heading - 360)
    ep_lon, ep_lat = _fwd(nacra_pt.x, nacra_pt.y, heading)

    # nacra_pt = shapely_geom.Point(*nacra)
    nacra_travel = shapely_geom.LineString([nacra_pt, shapely_geom.Point(ep_lon, ep_lat)])
    cross = nacra_travel.intersection(line)

    if type(cross) == shapely_geom.point.Point:
        return _distance(nacra_pt, cross)
    else:
        line0_heading = _bearing(nacra_pt, shapely_geom.Point(*line.coords[0]))
        line1_heading = _bearing(nacra_pt, shapely_geom.Point(*line.coords[1]))

        if abs(heading - line0_heading) < abs(heading - line1_heading):
            return _distance(nacra_pt, shapely_geom.Point(*line.coords[0]))
        else:
            return _distance(nacra_pt, shapely_geom.Point(*line.coords[1]))

def seconds_to_line(line, location, heading, speed, **kwargs):
    logger.info(
        "gate",
        extra=dict(
            line=str(line), location=str(location), heading=heading, speed=speed
        ),
    )
    return _distance_to_line(line, location, heading) / ((speed + 1e-5) * _knots_to_mps)