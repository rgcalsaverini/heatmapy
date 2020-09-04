from abc import ABC, abstractmethod
from typing import Callable, List, Optional

from shapely.geometry import Polygon


def _no_label(*_):
    """ Default label generator, that produces no label """
    return None


class BaseRenderer(ABC):
    def __init__(self, color_scale: Callable[[float], any], label: Callable[[dict], Optional[str]] = _no_label):
        """
        Abstract renderer.
        Renderers are responsible for spiting out a visual representation of the heatmap
        :param color_scale: A function that, given a value, returns a color
        :param label: A function that, given an entry, returns a label
        """
        self.color_scale_func = color_scale
        self.label_func = label

    @abstractmethod
    def render(self, data: List[dict], poly_region: List[Polygon], poly_opts: dict) -> None:
        """
        Renders the heatmap data into something visual
        :param data: the heatmap data
        :param poly_region: optional polygonal regions
        :param poly_opts: poly region options
        """
        raise NotImplementedError

    @abstractmethod
    def save_to_file(self, filename: str) -> None:
        """
        Saves the rendered heatmap into a file
        :param filename: the filename
        :return:
        """
        raise NotImplementedError
