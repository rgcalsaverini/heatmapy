import json
from datetime import datetime
from math import log2

from heatmap import HeatMap, DefaultRenderer
from heatmap.extractors import MVGExtractor

home = (48.128446, 11.650027)
mvg_key = 'YOUR MVG KEY'  # Replace with your own key

mvg = MVGExtractor(mvg_key)


def color(value: float) -> str:
    """ A blue-to-red color scale """
    pct = 1 - max(0, min(1, value))
    hue = 210.0 * pct
    return 'hsl(%.2f, 75%%, 50%%)' % hue


def label(unit):
    """ Show travel time on the label """
    time = int(unit.get("time"))
    return f'<div style="font-size: 20px; width: 120px;text-align: center;">{time} min</div>'


with open('./geo/muenchen.json', 'r') as fp:
    geo_json = json.load(fp)


def calc_time(pt1, pt2):
    """ Calculate the time to get somewhere by UBahn """
    t_ubahn = mvg.average_time_between(pt1, pt2, datetime.now())
    if not t_ubahn:
        return None
    value = int(t_ubahn / 60.0)
    # Since the value will be normalized, we save it also on a separate key to show it on the label
    return {'value': value, 'time': value}


renderer = DefaultRenderer(center=home, zoom=12, color_scale=color, label=label)
h_map = HeatMap(home, geo_json, square_size=250, filename='mvg', load_intermediate_results=True)
h_map.generate(calc_time)
# Normalize on a log2 scale
h_map.normalize(lambda v, _1, _2: log2(v))
# Then again on a 0 to 1 range
h_map.normalize()
h_map.render(renderer)
