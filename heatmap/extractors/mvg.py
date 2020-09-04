import time
from copy import deepcopy
from datetime import datetime
from json.decoder import JSONDecodeError
from typing import Optional, Any
from urllib.parse import urlencode

import requests

from heatmap.common import Coord


class MVGExtractor(object):
    def __init__(self, api_key: str):
        """
        Extracts distance data from the MVG (Munich's subway operator) API.

        :param api_key: The MVG API key
        """
        self._key = api_key
        self._base_uri = 'https://apps.mvg-fahrinfo.de/v12/rest/12.0'

    def get_route_custom(self, ref_time: Optional[float] = None, **opts) -> dict:
        """
        Get route data between two points from custom parameters.
        :param ref_time: Reference timestamp for the query. Leave empty for 'now'
        :param opts: Extra options
        :return: Route info as a dict
        """
        url_args = {
            **_route_request_defaults,
            **opts,
            'time': int(time.time() * 1000) or ref_time,
        }
        return self._make_request('routing/', url_args)

    def get_route_from_coords(self, from_pt: Coord, to_pt: Coord, ref_time: Optional[float] = None, **opts) -> dict:
        """
        Get route to a point from another arbitrary point.
        :param from_pt: origin coordinates
        :param to_pt: destination coordinates
        :param ref_time: Reference timestamp for the query. Leave empty for 'now'
        :param opts: Extra options
        :return: Route info as a dict
        """
        return self.get_route_custom(ref_time=ref_time,
                                     fromLatitude=from_pt[0],
                                     fromLongitude=from_pt[1],
                                     toLatitude=to_pt[0],
                                     toLongitude=to_pt[1],
                                     **opts)

    def average_time_between(self, from_pt: Coord, to_pt: Coord, ref_date: datetime, **opts) -> Optional[float]:
        """
        Return the average travel time between two points by taking the average of the 3-fastest routes.

        :param from_pt: origin coordinates
        :param to_pt: destination coordinates
        :param ref_date: Reference date-time for the query.
        :param opts: extra options
        :return: The average travel time in seconds, or None if no route was found.
        """
        ref_time = int(ref_date.timestamp() * 1000)
        route = self.get_route_from_coords(from_pt, to_pt, ref_time=ref_time, **opts)
        times = []
        for conn in route['connectionList']:
            duration_min = (conn['arrival'] - conn['departure']) / 1000.0
            times.append(duration_min)
        three_shortest = sorted(times)[0:3]
        if not three_shortest:
            return None
        return sum(three_shortest) / len(three_shortest)

    def _make_request(self, path: str, url_args: Optional[dict] = None, method: str = 'get'):
        """
        Makes a request to the API

        :param path: endpoint path
        :param url_args: URL query strings
        :param method: HTTP method
        :return: json response
        """
        req_method = getattr(requests, method)

        url_args = deepcopy(url_args or {})

        if method == 'get':
            url_args['apiKey'] = self._key

        if url_args:
            args = urlencode({k: _coerce_to_string(v) for k, v in (url_args or {}).items()})
            args = f'?{args}'
        else:
            args = ''
        uri = f'{self._base_uri.rstrip("/")}/{path.lstrip("/")}{args}'
        headers = {
            'User-Agent': 'MVG Fahrinfo Android 5.10',
            'Host': 'apps.mvg-fahrinfo.de',
        }
        res = req_method(uri, headers=headers)
        try:
            return res.json()
        except JSONDecodeError:
            return None


def _coerce_to_string(value: Any) -> str:
    """
    Coerce a value to string to be used on the request's URI
    :param value: anything
    :return: a string
    """
    if value is True:
        return 'true'
    if value is False:
        return 'false'
    if isinstance(value, float):
        return '%.5f' % value
    return str(value)


# Default parameters for the route request
_route_request_defaults = {
    'language': 'en',
    'transportTypeBus': True,
    'transportTypeTrain': True,
    'transportTypeCable': True,
    'transportTypeBoat': True,
    'transportTypeTram': True,
    'transportTypeSBahn': True,
    'transportTypeUnderground': True,
    'maxTravelTimeFootwayToStation': 10,
    'maxTravelTimeFootwayToDestination': 10,
    'arrival': False,
    'lowfloorVehicles': False,
    'showZoom': False,
    'walkSpeed': 'NORMAL',
    'noEscalators': False,
    'noSolidStairs': False,
    'noElevators': False,
    'lineInformation': False,
    'wheelchair': False,
    'changeLimit': 9,
}

_muenchen = 'München'
