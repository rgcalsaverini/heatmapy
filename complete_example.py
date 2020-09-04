"""
This is a complete example showcasing most of the features available so far.

It will plot a custom heatmap showing the distances from any point in Munich to a public toilet.
Public toilets will be marked as small circles on the map, and a region will be drawn representing areas
that are 1km or closer to public toilets.
"""
import json
from math import sqrt, e as euler_num

from geopy.distance import distance

from heatmap import HeatMap, DefaultRenderer
from heatmap.extractors import CSVExtractor

marienplatz = (48.1373629, 11.5748808)
inv_euler = (1.0 / euler_num)


def custom_color_scale(value):
    """
    Our custom color scale
    """
    pct = (1 - max(0, min(1, value))) ** 1.5
    opacity = 1 if pct > 0.75 else pct / 0.75
    return 'hsla(180, 75%%, 50%%, %.3f)' % opacity


class ToiletExtractor(CSVExtractor):
    delimiter = '\t'

    @staticmethod
    def _euclidian_distance(p1, p2):
        """ Calculates the euclidian distance between two points """
        return sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

    def get_value(self, _, point):
        """
        Returns the distance between a point and the closes public toilet
        """
        # Because it is so much cheaper the calculate, and for such a small distance not all that different,
        # first we get the 15-closest toilets by using euclidian distance
        by_euclidian_dist = {i: self._euclidian_distance(self.get_loc(p), point) for i, p in enumerate(self.data)}
        closest = sorted(by_euclidian_dist.items(), key=lambda v: v[1])[0:15]
        min_dist = None
        # Then we iterate over this 15 to get the actual geodesic distance
        for idx, _ in closest:
            toilet_dist = distance().measure(self.get_loc(self.data[idx]), point)
            min_dist = min(min_dist or toilet_dist, toilet_dist)

        # We want the distance in log scale
        return {'value': min_dist ** inv_euler, 'lin_value': min_dist}

    def add_markers(self, rend: DefaultRenderer, _):
        """ Add circles around public toilets """
        for toilet in self.data:
            toilet_loc = self.get_loc(toilet)
            if not toilet_loc:
                continue
            rend.add_circle(toilet_loc,
                            label=self.get_label(toilet),
                            radius=10,
                            fill_color='#0ef',
                            fill_opacity=1,
                            opacity=0,
                            weight=10)

    @staticmethod
    def get_label(toilet: dict):
        title = toilet.get('bezeichnung', '?')
        opening_hours = toilet.get('service_oeffnungszeiten', 'unknown')
        title_el = f'<h4>{title}</h4>'
        opening_hours_el = f'<div style="font-weight: bold">Opening hours:</div>\n<div style="margin-left: 5px">{opening_hours}</div>'
        return f'<div style="min-width: 300px;">{title_el}{opening_hours_el}</div>'.replace('`', "'")


# Load the polygon surrounding Munich
with open('./geo/muenchen.json', 'r') as fp:
    geo_json = json.load(fp)

# The extractor gets the data
toilet_extr = ToiletExtractor('./data/oeffentlichetoilettenmuenchen2016-06-28.csv', 'latitude', 'longitude')

# The renderer deals with visual aspects of the map
renderer = DefaultRenderer(center=marienplatz,
                           zoom=12,
                           opacity=0.35,
                           color_scale=custom_color_scale,
                           tiles='cartodbdark_matter')

# Create a new heatmap
h_map = HeatMap(None, geo_json, filename='toilet', square_size=500, num_threads=100, load_intermediate_results=True)
h_map.generate(toilet_extr.get_value)
h_map.normalize()
# Generate the polygon areas within 1km of a public toilet
h_map.generate_polygon(lambda v: v.get('lin_value', 999) < 1.0, dash_array=[5, 5], color='#0ef', opacity=0.5, weight=2)
# Render and save
h_map.render(renderer, before_saving=toilet_extr.add_markers)
