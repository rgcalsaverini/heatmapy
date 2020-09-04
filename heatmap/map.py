import json
import multiprocessing
import os
import threading
from concurrent.futures.thread import ThreadPoolExecutor
from time import sleep
from typing import List, Dict, Callable, TextIO, Optional, Union

from geopy.distance import distance
from shapely.geometry import shape, Polygon, MultiPolygon

from heatmap.common import Coord
from heatmap.renderers.common import BaseRenderer


def _parse_geo_json(data: dict) -> List[Polygon]:
    """
    Parse GeoJson data into a list of polygons
    :param data: dict data of the geo poly
    :return: A list of shapely polygons
    """
    return [shape(f['geometry']) for f in data['features']]


def _create_square(origin: Coord, side: float) -> Polygon:
    """
    Return a Polygon representing representing a square from an origin and the side
    :param origin: the origin point
    :param side: the measurement of one side of the square
    :return: A closed Polygon
    """
    dest = distance(meters=side).destination(origin, 35)
    coords = [origin, [dest[0], origin[1]], dest, [origin[0], dest[1]], origin]
    # points = [[p.latitude, p.longitude] if isinstance(p, Point) else list(p) for p in coords]
    return Polygon(coords)


def _parse_jsonl(stream: TextIO):
    """
    Parse a json lines file (http://jsonlines.org/).
    :param stream: file stream
    :return: list of dicts
    """
    return [json.loads(line.strip()) for line in stream.readlines()]


class HeatMap(object):
    def __init__(self,
                 origin: Optional[Coord],
                 geo_poly: dict,
                 square_size: int = 250,
                 load_intermediate_results=False,
                 save_intermediate_results=True,
                 filename=None,
                 num_threads=1):
        """
        Creates a basic heatmap.

        :param origin: origin point of the heatmap. This might not make sense in many cases,
                    and in such cases can be omitted
        :param geo_poly: GeoJson polygon of the enclosing area
        :param square_size: Size of one unit of the heatmap
        :param load_intermediate_results: if set to true, will try to load previously generated data
        :param save_intermediate_results: if set to true, will save intermediate data, to resume processing later
        :param filename: a file name (without extension) representing this heatmap
        :param num_threads: number of threads to use when extracting values
        """
        self.origin = origin
        self._boundaries: List[Polygon] = _parse_geo_json(geo_poly)
        self.square_size = square_size
        self.squares: Dict[int, Polygon] = dict()
        self._values = dict()
        self._bbox = None
        self.load_intermediate_results = load_intermediate_results
        self.save_intermediate_results = save_intermediate_results
        filename = filename or 'intermediate_result'
        self.intermediate_file_name = f'{filename}.jsonl'
        self.map_file_name = f'{filename}.html'
        manager = multiprocessing.Manager()
        self._lock = manager.Lock()
        self.num_threads = num_threads
        self._missing = set()
        self.poly_region = []
        self.poly_opts = {}

    def set_value(self, idx: int, value: Union[float, dict]) -> None:
        """
        Sets the value for one unit on the heatmap, given its idx and a value.
        :param idx: the index of the unit
        :param value: either a float or a dict representing the value
        :return: nothing
        """
        if isinstance(value, dict):
            data = {
                'idx': idx,
                'poly': list(self.squares[idx].exterior.coords),
                'value': None,
                **value,
            }
        else:
            data = {
                'idx': idx,
                'poly': list(self.squares[idx].exterior.coords),
                'value': value,
            }
        with self._lock:
            self._values[idx] = data
            if self.save_intermediate_results:
                with open(self.intermediate_file_name, 'a') as fp:
                    fp.write('%s\n' % json.dumps(data).strip())

    @property
    def bounding_box(self):
        """ Returns the bounding box of the region described by the polygon. """
        if not self._bbox:
            min_lat = None
            min_lon = None
            max_lat = None
            max_lon = None

            for poly in self._boundaries:
                p_min_la, p_min_lo, p_max_la, p_max_lo = poly.bounds
                min_lat = min(min_lat or p_min_la, p_min_la)
                min_lon = min(min_lon or p_min_lo, p_min_lo)
                max_lat = max(max_lat or p_max_la, p_max_la)
                max_lon = max(max_lon or p_max_lo, p_max_lo)

            self._bbox = [min_lat, min_lon], [max_lat, max_lon]
        return self._bbox

    def generate(self, getter: Callable[[Coord, Coord], Union[dict, float]]) -> None:
        """
        Generate the heatmap.
        :param getter: A getter function on the format 'getter(origin, pt) -> float' that
                       returns the heatmap value for two specific points.
        """
        self._generate_units()
        self._get_values(getter)

    def render(self, renderer: BaseRenderer, before_saving: Callable[[BaseRenderer, 'HeatMap'], None] = None) -> None:
        """
        Render the heatmap
        :param renderer: the renderer to be used.
        :param before_saving: An optional function to call before saving. Can be used to add extra features such as
                              markers and polygons.
        """
        print('Rendering...')
        renderer.render(list(self._values.values()), self.poly_region, self.poly_opts)
        if before_saving:
            before_saving(renderer, self)
        renderer.save_to_file(self.map_file_name)

    def normalize(self, custom_func: Callable[[float, float, float], float] = None):
        """
        Normalize the data into a 0..1 scale, keeping the original value on a new key called 'original_value'
        """
        print('Normalizing...')
        min_val = None
        max_val = None

        for item in self._values.values():
            if item['value'] is None:
                continue
            min_val = min(item['value'], min_val or item['value'])
            max_val = max(item['value'], max_val or item['value'])

        for key, item in self._values.items():
            if item['value'] is None:
                continue
            self._values[key]['original_value'] = item['value']
            if custom_func:
                self._values[key]['value'] = custom_func(item['value'], min_val, max_val)
            else:
                self._values[key]['value'] = (item['value'] - min_val) / (max_val - min_val)

    def generate_polygon(self, selector: Callable[[dict], bool], **opts):
        print('Generating area polygon...')
        poly_region = None
        for item in self._values.values():
            if selector(item):
                if poly_region is None:
                    poly_region = Polygon(item['poly'])
                else:
                    poly_region = poly_region.union(self.squares[item['idx']])

        poly_region = list(poly_region) if isinstance(poly_region, MultiPolygon) else [poly_region]
        self.poly_region = []
        for poly in poly_region:
            if not poly:
                continue
            poly = poly.buffer(0.005, resolution=2).buffer(-0.008, resolution=2).buffer(0.003, resolution=2)

            if isinstance(poly, MultiPolygon):
                united_poly = poly[0]
                for poly_part in poly[1:]:
                    united_poly = united_poly.union(poly_part)
                united_poly = list(united_poly) if isinstance(united_poly, MultiPolygon) else [united_poly]
            else:
                united_poly = [poly]
            self.poly_region.extend([p for p in united_poly if not p.is_empty])
        self.poly_opts = opts

    def _generate_units(self):
        """
        Generate the units on the heatmap
        """
        print('Generating units...')
        current_lat = self.bounding_box[0][0]
        idx = 0
        while current_lat < self.bounding_box[1][0]:
            current_lon = self.bounding_box[0][1]
            new_lat = current_lat
            while current_lon < self.bounding_box[1][1]:
                rect = _create_square((current_lat, current_lon), self.square_size)
                _, __, new_lat, current_lon = rect.bounds
                if any(p.contains(rect) for p in self._boundaries):
                    self.squares[idx] = rect
                    idx += 1
            current_lat = new_lat

    def _get_values(self, getter: Callable[[Coord, Coord], Union[dict, float]]):
        """
        Get the values for each individual unit
        """
        if self.load_intermediate_results and os.path.isfile(self.intermediate_file_name):
            with open(self.intermediate_file_name, 'r') as fp:
                self._values = {i['idx']: i for i in _parse_jsonl(fp)}

        if self.save_intermediate_results and not os.path.isfile(
                self.intermediate_file_name) or not self.load_intermediate_results:
            open(self.intermediate_file_name, 'w').close()

        present = set(i['idx'] for i in self._values.values())
        self._missing = set(i for i in self.squares.keys() if i not in present)

        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            while len(self._missing) > 0:
                idx = self._missing.pop()
                square = self.squares[idx]
                coords_x, coords_y = square.exterior.coords.xy
                cx = sum(coords_x[0:4]) / 4.0
                cy = sum(coords_y[0:4]) / 4.0
                args = ((cy, cx), idx, getter)
                executor.submit(self._get_one, *args)

    def _get_one(self, point: Coord, index: int, getter: Callable[[Coord, Coord], Union[dict, float]]):
        """
        Get one single unit's value. Retries if not successful
        """
        try:
            if threading.current_thread().name.endswith('0_0'):
                print(len(self._values), '/', len(self.squares.keys()))
            value = None
            for i in range(5):
                try:
                    value = getter(self.origin, point)
                except (BaseException, Exception):
                    value = False
                if value is not False and value is not None:
                    break
                else:
                    sleep(0.5)
            if value is False:
                self._missing.add(index)
                sleep(5)
            else:
                self.set_value(index, value)
        except Exception as e:
            print(e)
