"""

"""
import json
from datetime import datetime
from math import log2

from heatmap import HeatMap, DefaultRenderer
from heatmap.extractors import MVGExtractor, GoogleBike

mvg_key = 'YOUR MVG KEY'
google_key = 'YOUR GOOGLE KEY'

home = (48.128446, 11.650027)

mvg = MVGExtractor(mvg_key)
bike = GoogleBike(google_key)


def calc_time(pt1, pt2):
    t_ubahn = mvg.average_time_between(pt1, pt2, datetime.now())
    t_bike = bike.average_time_between(pt1, pt2)
    if not t_bike or not t_ubahn:
        return None
    value = (t_ubahn / t_bike) if t_ubahn > t_bike else -(t_bike / t_ubahn)
    return {
        'bike_val': t_bike / 60.0,
        'ubahn_val': t_ubahn / 60.0,
        'value': value,
    }


def custom_color_scale(value):
    pct = 1 - max(0, min(1, value))
    hue = 240 if pct < 0.5 else 0
    sat = abs(0.5 - pct)
    return 'hsla(%.2f, %.2f%%, 50%%, %.2f)' % (hue, 75, sat * 2)


# Load the polygon surrounding Munich
with open('./geo/muenchen.json', 'r') as fp:
    geo_json = json.load(fp)


def normalize_log2_scale(val, _1, _2):
    if val > 0:
        return 0.5 + log2(val) / 3
    return 0.5 - log2(abs(val)) / 2


def make_label(obj):
    width = 300.0
    margin = 1.6
    pct_bar = 100.0 - 2.0 * 3.6113
    pct = min(1, max(0, 1.0 - obj.get('value')))
    left = margin + pct_bar * pct
    bike_time = round(obj.get('bike_val'))
    ubahn_time = round(obj.get('ubahn_val'))
    contents = '<div style="position: relative">'
    contents += f'<img src="docs/gauge.svg" style="width:{width}px;margin-bottom: 20px">'
    contents += f'<img src="docs/pointer.svg" style="width:15px;position:absolute;left:{left}%;bottom:5px">'
    contents += '</div>'
    contents += '<div style="width: 100%; display: flex; flex-direction: row;justify-content: space-between;">'
    contents += '<div style="font-weight: bold;padding-right: 5px">Bike:</div>'
    contents += f'<div style="">{bike_time} min</div>'
    contents += '<div style="font-weight: bold;padding-right: 5px">Public transport:</div>'
    contents += f'<div style="">{ubahn_time} min</div>'
    contents += '</div>'
    return contents


def bikable_zone(unit):
    if 'original_value' not in unit or unit.get('original_value') is None:
        return False
    return unit.get('original_value') > 1.5 and unit.get('bike_val') < 25


renderer = DefaultRenderer(center=home, zoom=12, opacity=0.5, label=make_label, color_scale=custom_color_scale)
h_map = HeatMap(home, geo_json, filename='bike_vs_ubahn', square_size=800, num_threads=100,
                load_intermediate_results=True)
h_map.generate(calc_time)
h_map.normalize(normalize_log2_scale)
h_map.generate_polygon(bikable_zone, color='#0012b3', opacity=0.6, weight=5, dash_array=[1, 6])
h_map.render(renderer, before_saving=lambda r, _: r.add_circle(home, color='#0012b3', radius=20))
