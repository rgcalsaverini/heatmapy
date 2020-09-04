import csv
from abc import ABC, abstractmethod
from typing import TextIO, List

from heatmap.common import Coord


class CSVExtractor(ABC):
    delimiter = '\t'

    def __init__(self, file_path: str, lat_key: str, lon_key: str):
        """
        Abstract extractor to retrieve data from a static CSV file.
        Extend it by implementing the get_value method

        :param file_path: the csv file complete path
        :param lat_key: name of the column containing latitude
        :param lon_key: name of the column containing longitude
        """
        self.lat_key = lat_key
        self.lon_key = lon_key
        with open(file_path, 'r') as csv_file:
            self.data = load_csv(csv_file, self.delimiter)

    def get_loc(self, item: dict) -> Coord:
        """
        Get the location of one row
        :param item: The dict representing a row on the CSV
        :return: The coordinates as a tuple of 2 floats
        """
        lat = item.get(self.lat_key)
        lon = item.get(self.lon_key)
        if not lat or not lon:
            return None
        return float(lat), float(lon)

    @abstractmethod
    def get_value(self, origin: Coord, point: Coord) -> float:
        """
        Get the value for two coordinates
        :param origin: the origin coordinate
        :param point: the currently examined coordinate
        :return: float
        """
        raise NotImplementedError()


def load_csv(stream: TextIO, delimiter: str) -> List[dict]:
    """
    Loads a CSV into a list of dictionaries.
    First row representing the key names
    :param stream: file IO
    :param delimiter: CSV delimiter
    :return: the contents as a list of dicts.
    """
    columns = []
    first_row = True
    data = list()
    csv_reader = csv.reader(stream, delimiter=delimiter)
    for row in csv_reader:
        if first_row:
            columns = row
            first_row = False
        else:
            entry = dict()
            for idx, value in enumerate(row):
                entry[columns[idx]] = value
            data.append(entry)
    return data
