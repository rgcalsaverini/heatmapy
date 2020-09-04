from typing import Callable, List

import folium
from shapely.geometry import Polygon

from heatmap.common import Coord
from heatmap.renderers.common import BaseRenderer


def _default_color_scale(value: float) -> str:
    """ A green-to-red color scale """
    pct = 1 - max(0, min(1, value))
    hue = 130.0 * pct
    return 'hsl(%.2f, 75%%, 50%%)' % hue


class FoliumRenderer(BaseRenderer):
    def __init__(self,
                 color_scale: Callable[[float], any] = _default_color_scale,
                 zoom: int = 3,
                 center: Coord = None,
                 tiles: str = 'Stamen Toner',
                 opacity: float = 0.75,
                 *args,
                 **kwargs):
        """
        Renders the heatmap into an static HTML interactive map
        :param color_scale: the color scale for the heatmap
        :param zoom: the zoom level
        :param center: coordinates of the center of the map
        :param tiles: the name of the map texture used
        :param opacity: opacity of the heatmap
        """
        super().__init__(color_scale, *args, **kwargs)
        self._map = None
        self.zoom = zoom
        self.center = center
        self.tiles = tiles
        self.opacity = opacity
        self._layers = {
            'heatmap': folium.FeatureGroup(name='Heat map'),
        }

    def render(self, data: List[dict], poly_region: List[Polygon], poly_opts: dict) -> None:
        """
        Renders the heatmap data into something visual
        :param data: the heatmap data
        :param poly_region: optional polygonal regions
        :param poly_opts: poly region options
        """

        self._map = folium.Map(
            location=self.center or [0, 0],
            zoom_start=self.zoom,
            tiles=self.tiles
        )
        for unit in data:
            value = unit['value']
            if value is None:
                continue
            label = self.label_func(unit)
            fill = self.color_scale_func(value)
            folium.Polygon(
                locations=[(y, x) for x, y in unit['poly']],
                popup=label,
                weight=0,
                fill=value is not None,
                fill_color=fill,
                fill_opacity=self.opacity,
            ).add_to(self._layers['heatmap'])
        self._layers['heatmap'].add_to(self._map)
        if poly_region:
            self._render_poly_region(poly_region, poly_opts)
        folium.LayerControl(collapsed=False).add_to(self._map)

    def _render_poly_region(self, poly_region: List[Polygon], poly_opts: dict):
        for poly in poly_region:
            self.add_polygon(poly, **poly_opts)

    def save_to_file(self, filename: str) -> None:
        """
        Saves the rendered heatmap into a file
        :param filename: the filename
        :return:
        """
        if self._map is None:
            raise ValueError('Not rendered')
        self._map.save(filename)

    def add_marker(self, point: Coord, label: str = None, layer_name: str = 'heatmap') -> None:
        """
        Add a marker to the map
        :param point: coordinates of the marker
        :param label: label of the marker
        :param layer_name: name of the layer. Currently broken, do not override :)
        :return: nothing
        """
        if self._map is None:
            raise ValueError('Not rendered')
        if layer_name not in self._layers:
            self._layers[layer_name] = folium.FeatureGroup(name=layer_name)
            self._layers[layer_name].add_to(self._map)

        folium.Marker(point, popup=label).add_to(self._layers[layer_name])

    def add_circle(self, point, label=None, radius: int = 10, layer_name: str = 'heatmap', **opts) -> None:
        """
        Add a circle to the map
        :param point: coordinates of the center of the circle
        :param label: label of the circle
        :param radius: the circle radius in meters
        :param layer_name: name of the layer. Currently broken, do not override :)
        :return: nothing
        """
        if self._map is None:
            raise ValueError('Not rendered')
        if layer_name not in self._layers:
            self._layers[layer_name] = folium.FeatureGroup(name=layer_name)
            self._layers[layer_name].add_to(self._map)

        folium.Circle(point, radius, popup=label, **opts).add_to(self._layers[layer_name])

    def add_polygon(self, poly: Polygon, label=None, layer_name: str = 'heatmap', **opts) -> None:
        """
        Add a circle to the map
        :param poly: polygon object
        :param label: label of the circle
        :param layer_name: name of the layer. Currently broken, do not override :)
        :return: nothing
        """
        if self._map is None:
            raise ValueError('Not rendered')
        if layer_name not in self._layers:
            self._layers[layer_name] = folium.FeatureGroup(name=layer_name)
            self._layers[layer_name].add_to(self._map)
        coords = [[pt[1], pt[0]] for pt in list(poly.exterior.coords)]
        folium.Polygon(coords, popup=label, **opts).add_to(self._layers[layer_name])
