from urllib.parse import urlencode

import requests

from heatmap.common import Coord


class GoogleBike(object):
    def __init__(self, api_key: str):
        """
        Uses Google's Distance Matrix API to retrieve the travel time between two points.
        WARNING! The API is not free, and you will be charged for its use.
        :param api_key: Your key for the api
        """
        self._key = api_key
        self._base_uri = 'https://maps.googleapis.com/maps/api/distancematrix/json'

    def average_time_between(self, from_pt: Coord, to_pt: Coord) -> float:
        """
        Returns the average time needed to travel from 'from_pt' to 'to_pt' by bike
        :param from_pt: origin coordinate
        :param to_pt: destination coordinate
        :raises ValueError: If the response body does not contain valid json.
        :return: a float representing the time in seconds
        """
        uri = self._get_uri(from_pt, to_pt)
        res = requests.get(uri)
        data = _get_rest_json(res)
        row = data['rows'][0]['elements'][0]
        duration_s = row.get('duration', {}).get('value', None)

        return duration_s

    def _get_uri(self, from_pt: Coord, to_pt: Coord) -> str:
        """
        Make the URI for the request to the API.
        :param from_pt: origin coordinate
        :param to_pt: destination coordinate
        :return: the URI
        """
        query_strings = urlencode({
            'units': 'metric',
            'origins': _coords_to_str(*from_pt),
            'destinations': _coords_to_str(*to_pt),
            'mode': 'bicycling',
            'key': self._key,
        })
        return f'{self._base_uri}?{query_strings}'


def _json_decode_failed(res):
    """ Simply raises a decoding error """
    raise ValueError(f'Got something weird ({res.status_code}): \n {res.text}')


def _coords_to_str(lat: float, lon: float) -> str:
    """
    Converts a coordinate into the way that the URI for the request
    expects it.
    :param lat: latitude
    :param lon: longitude
    :return: a string representing the coordinate
    """
    lat_str = '%.6f' % lat
    lon_str = '%.6f' % lon
    return f'{lat_str},{lon_str}'


def _get_rest_json(res: requests.Response):
    """
    Decodes the json request or throws an error.
    :param res: the response instance
    :raises ValueError: If the response body does not contain valid json.
    :return: json data
    """
    if res.status_code != 200:
        return _json_decode_failed(res)
    try:
        data = res.json()
    except ValueError:
        return _json_decode_failed(res)
    if data.get('status').lower() != 'ok':
        return _json_decode_failed(res)
    return data
