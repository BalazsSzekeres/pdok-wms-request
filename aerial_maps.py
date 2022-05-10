
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


def centre_to_bbox_coords(centre, width, height):
    return [[centre[0] - width/2, centre[1] - height/2],
            [centre[0] + width/2, centre[1] + height/2]] 


def bbox_to_centre_coords(bbox):
    width, height = get_edges_distance(*[coord for coords in bbox for coord in coords])
    centre = [bbox[0][0] + width/2, bbox[0][1] + height/2]
    return centre, width, height


def is_coord_in_bbox(coord, bbox):
    #print(coord)
    #print(bbox)
    #exit()
    bbox_array = np.array(bbox)
    lon_valid = coord[0] >= bbox_array[0,0] and coord[0] < bbox_array[1,0]
    lat_valid = coord[1] >= bbox_array[0,1] and coord[1] < bbox_array[1,1]

    return lon_valid and lat_valid


class CoordTransformer:
    def __init__(self):
        # Define transformers for local and global coordinate systems
        self.transformer_nl_global = Transformer.from_crs("epsg:4326", "epsg:28992", always_xy=True)
        self.transformer_global_nl = Transformer.from_crs("epsg:28992", "epsg:4326", always_xy=True)

    def t_nl_global(self, lon, lat):
        return self.transformer_nl_global.transform(lon, lat)

    def t_global_nl(self, lon, lat):
        return self.transformer_global_nl.transform(lon, lat)


class AerialMap:
    def __init__(self, map_, bbox, resolution):
        self.map_ = map_ 
        self.bbox = bbox
        self.centre, self.width, self.height = bbox_to_centre_coords(bbox)
        self.resolution = resolution    # in m/pixel
        self.transformer = CoordTransformer()

    @property
    def bbox_global(self):
        return [list(self.transformer.t_nl_global(*coords)) for coords in self.bbox]

    def get_coordinate_from_pixel(self, x, y):
        if not isinstance(x, int) or not isinstance(y, int):
            raise TypeError('Pixel coordinates must be of type int')

        if not is_coord_in_bbox((x, y), [[0,0], self.map_.shape[:2]]):
            raise ValueError('Pixel does not lie in map image')

        coord_lon = (self.resolution * x) + self.bbox_global[0][0]
        coord_lat = (self.resolution * y) + self.bbox_global[0][1] 

        return self.transformer.t_global_nl(coord_lon, coord_lat)

    def get_pixel_from_coordinate(self, lon, lat):
        lon_global, lat_global = self.transformer.t_nl_global(lon, lat)
        if not is_coord_in_bbox((lon_global, lat_global), self.bbox_global):
            raise ValueError('Coordinates do not lie in bounding box')

        bbox_1_lon, bbox_1_lat = self.bbox_global[0] 
        pixel_x = int((lon_global - bbox_1_lon) / self.resolution)
        pixel_y = int((lat_global - bbox_1_lat) / self.resolution)

        return pixel_x, pixel_y

    def show(self):
        plt.imshow(self.map_)
        plt.show()


class AerialMapRetriever:
    def __init__(self, resolution=None):
        self.resolution = resolution    # in m/pixel
        self.transformer = CoordTransformer()

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

    def get_map_from_centre(self, centre, width, height, x_pixels=None, y_pixels=None, resolution=None):
        bbox = [[centre[0] - width/2, centre[1] - height/2],
                [centre[0] + width/2, centre[1] + height/2]]
        
        return self.get_picture_from_corners(bbox, x_pixels, y_pixels, resolution)

    def get_map_from_corners(self, bbox, x_pixels=None, y_pixels=None, resolution=None):
        bbox_global = [list(self.transformer.t_nl_global(*coords)) for coords in bbox]

        if x_pixels is None or y_pixels is None:
            x_pixels, y_pixels = self._get_pixels(bbox_global, x_pixels, y_pixels, resolution)

        bbox_1_lon = bbox_global[0][0]
        bbox_1_lat = bbox_global[0][1]
        bbox_2_lon = bbox_global[1][0]
        bbox_2_lat = bbox_global[1][1]
        params = {'WIDTH': x_pixels, 'HEIGHT': y_pixels,
                  'BBOX': f'{bbox_1_lon},'
                          f'{bbox_1_lat},'
                          f'{bbox_2_lon},'
                          f'{bbox_2_lat}'}

        response = requests.get(
            "https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
            "&FORMAT=image/png&TRANSPARENT=true&LAYERS=2019_ortho25&STYLES=&CRS=EPSG:28992",
            params)

        response.raise_for_status()
        with io.BytesIO(response.content) as f:
            map_array = np.array(Image.open(f))

        width, _ = get_edges_distance(bbox_1_lon, bbox_1_lat, bbox_2_lon, bbox_2_lat)
        res = width / x_pixels 
        return AerialMap(map_array, bbox, res)


if __name__ == "__main__":
    bbox_1_lon, bbox_1_lat = 4.340329, 51.997908
    bbox_2_lon, bbox_2_lat = 4.390283, 52.022765
    bbox = [[bbox_1_lon, bbox_1_lat],
            [bbox_2_lon, bbox_2_lat]]

    print(bbox)
    width, height = get_edges_distance(bbox_1_lon, bbox_1_lat, bbox_2_lon, bbox_2_lat)
    centre = [bbox_1_lon + width/2, bbox_1_lat + height/2]
    #y_length = 1000
    #y_length = 3000
    #y_length = None 
    resolution = 1
    #resolution = 2 

    map_retriever = AerialMapRetriever(resolution)

    map_from_corners = map_retriever.get_map_from_corners(bbox)
    #map_from_corners.show()
    pixel = map_from_corners.get_pixel_from_coordinate(bbox_1_lon, bbox_1_lat)
    #pixel = np.array(map_from_corners.get_pixel_from_coordinate(bbox_2_lon - 1e-8, bbox_2_lat - 1e-8)) - 1
    coords = map_from_corners.get_coordinate_from_pixel(*pixel)
    #print(bbox_1_lon, bbox_1_lat)
    #print(pixel)
    #print(coords)
    assert np.allclose(coords, (bbox_1_lon, bbox_1_lat))

    map_array = map_from_corners.map_
    #print(map_array[pixel[1], pixel[0]])
    #print(pixel)
    #map_array[pixel[1], pixel[0]] = [255, 0, 0]
    plt.imshow(map_array)
    plt.show()
    #map_from_centre = map_retriever.get_map_from_centre(centre, width, height)
    #map_from_centre.show()

    #assert np.all(from_corners == from_centre)

