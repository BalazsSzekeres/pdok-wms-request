
import io
import requests
import numpy as np
import matplotlib.pyplot as plt
from pyproj import Transformer
from PIL import Image


# Website to get bbox values: http://bboxfinder.com/#51.997908,4.340329,52.022765,4.390283


def get_aspect_ratio(x_1, y_1, x_2, y_2):
    a, b = get_edges_distance(x_1, y_1, x_2, y_2)
    return a / b


def get_edges_distance(x_1, y_1, x_2, y_2):
    a = abs(x_2 - x_1)
    b = abs(y_2 - y_1)
    return a, b


class AerialMap:
    def __init__(self, resolution=None):
        self.resolution = resolution    # in m/pixel

        # Define transformers for local and global coordinate systems
        self.transformer_nl_global = Transformer.from_crs("epsg:4326", "epsg:28992", always_xy=True)
        self.transformer_global_nl = Transformer.from_crs("epsg:28992", "epsg:4326", always_xy=True)

    def t_nl_global(self, lon, lat):
        return self.transformer_nl_global.transform(lon, lat)

    def t_global_nl(self, lon, lat):
        return self.transformer_global_nl.transform(lon, lat)

    def _get_pixels_from_resolution(self, bbox, resolution):
        if resolution is None:
            if self.resolution is None:
                raise ValueError('Resolution unspecified.')

            resolution = self.resolution

        edges_m = get_edges_distance(*[coord for coords in bbox for coord in coords])
        edges_pixels = [edge_m / resolution for edge_m in edges_m]
        return edges_pixels

    def _get_pixels(self, bbox, x_pixels, y_pixels, resolution):
        aspect_ratio = get_aspect_ratio(*[coord for coords in bbox for coord in coords])
        if x_pixels is None and y_pixels is None:
            x_pixels, y_pixels = self._get_pixels_from_resolution(bbox, resolution) 
        elif x_pixels is None:
            x_pixels = y_pixels * aspect_ratio
        elif y_pixels is None:
            y_pixels = x_pixels / aspect_ratio 

        return x_pixels, y_pixels

    def get_picture_from_centre(self, centre, width, height, x_pixels=None, y_pixels=None, resolution=None):
        bbox = [[centre[0] - width/2, centre[1] - height/2],
                [centre[0] + width/2, centre[1] + height/2]]
        
        return self.get_picture_from_corners(bbox, x_pixels, y_pixels, resolution)

    def get_picture_from_corners(self, bbox, x_pixels=None, y_pixels=None, resolution=None):
        bbox_nl = [self.t_nl_global(*coords) for coords in bbox]

        if x_pixels is None or y_pixels is None:
            x_pixels, y_pixels = self._get_pixels(bbox_nl, x_pixels, y_pixels, resolution)

        bbox_array = np.array(bbox_nl)
        params = {'WIDTH': x_pixels, 'HEIGHT': y_pixels,
                  'BBOX': f'{bbox_array[0,0]},'
                          f'{bbox_array[0,1]},'
                          f'{bbox_array[1,0]},'
                          f'{bbox_array[1,1]}'}

        response = requests.get(
            "https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
            "&FORMAT=image/png&TRANSPARENT=true&LAYERS=2019_ortho25&STYLES=&CRS=EPSG:28992",
            params)

        response.raise_for_status()
        with io.BytesIO(response.content) as f:
            return np.array(Image.open(f))

    def get_coordinate_from_pixel(self, x, y):
        raise NotImplementedError

    def get_pixel_from_coordinate(self, lat, lng):
        raise NotImplementedError


if __name__ == "__main__":
    bbox_1_lon, bbox_1_lat = 4.340329, 51.997908
    bbox_2_lon, bbox_2_lat = 4.390283, 52.022765
    bbox = [[bbox_1_lon, bbox_1_lat],
            [bbox_2_lon, bbox_2_lat]]

    width, height = get_edges_distance(bbox_1_lon, bbox_1_lat, bbox_2_lon, bbox_2_lat)
    centre = [bbox_1_lon + width/2, bbox_1_lat + height/2]
    #y_length = 1000
    #y_length = 3000
    #y_length = None 
    resolution = 1
    #resolution = 2 

    map_ = AerialMap(resolution)

    from_corners = map_.get_picture_from_corners(bbox)
    #plt.imshow(from_corners)
    #plt.show()
    from_centre = map_.get_picture_from_centre(centre, width, height)
    #plt.imshow(from_centre)
    #plt.show()

    #assert np.all(from_corners == from_centre)

