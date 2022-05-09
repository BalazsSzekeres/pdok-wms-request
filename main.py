from pyproj import Transformer
import requests
from PIL import Image
import io


# Website to get bbox values: http://bboxfinder.com/#51.997908,4.340329,52.022765,4.390283

def t_nl_global(lng, lat):
    transformer = Transformer.from_crs("epsg:4326", "epsg:28992", always_xy=True)
    return transformer.transform(lng, lat)


def t_gloabl_nl(lng, lat):
    transformer = Transformer.from_crs("epsg:28992", "epsg:4326", always_xy=True)
    return transformer.transform(lng, lat)


def get_aspect_ratio(x_1, y_1, x_2, y_2):
    a = abs(x_2 - x_1)
    b = abs(y_2 - y_1)
    return a / b


box_coordinate_1_world_lng, box_coordinate_1_world_lat = 4.340329, 51.997908
box_coordinate_2_world_lng, box_coordinate_2_world_lat = 4.390283, 52.022765
y_length = 1000


class AerialMap:
    def __init__(self,
                 box_coordinate_1_world_lng,
                 box_coordinate_1_world_lat,
                 box_coordinate_2_world_lng,
                 box_coordinate_2_world_lat,
                 y_length):
        self.box_coordinate_1_world_lng = box_coordinate_1_world_lng
        self.box_coordinate_1_world_lat = box_coordinate_1_world_lat
        self.box_coordinate_2_world_lng = box_coordinate_2_world_lng
        self.box_coordinate_2_world_lat = box_coordinate_2_world_lat

        self.box_coordinate_1_nl_lng, self.box_coordinate_1_nl_lat = t_nl_global(self.box_coordinate_1_world_lng,
                                                                                 self.box_coordinate_1_world_lat)
        self.box_coordinate_2_nl_lng, self.box_coordinate_2_nl_lat = t_nl_global(self.box_coordinate_2_world_lng,
                                                                                 self.box_coordinate_2_world_lat)

        self.aspect_ratio = get_aspect_ratio(self.box_coordinate_1_nl_lng,
                                             self.box_coordinate_1_nl_lat,
                                             self.box_coordinate_2_nl_lng,
                                             self.box_coordinate_2_nl_lat)

        self.y_length = y_length
        self.x_length = self.y_length * self.aspect_ratio

    def get_picture(self):
        params = {'WIDTH': self.x_length, 'HEIGHT': self.y_length,
                  'BBOX': f'{self.box_coordinate_1_nl_lng},'
                          f' {self.box_coordinate_1_nl_lat},'
                          f'{self.box_coordinate_2_nl_lng},'
                          f'{self.box_coordinate_2_nl_lat}'}

        response = requests.get(
            "https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
            "&FORMAT=image/png&TRANSPARENT=true&LAYERS=2019_ortho25&STYLES=&CRS=EPSG:28992",
            params)

        response.raise_for_status()
        with io.BytesIO(response.content) as f:
            with Image.open(f) as img:
                img.show()

    def get_coordinate_from_pixel(self, x, y):
        raise NotImplementedError

    def get_pixel_from_coordinate(self, lat, lng):
        raise NotImplementedError


if __name__ == "__main__":
    box_coordinate_1_world_lng, box_coordinate_1_world_lat = 4.340329, 51.997908
    box_coordinate_2_world_lng, box_coordinate_2_world_lat = 4.390283, 52.022765
    y_length = 1000

    map = AerialMap(box_coordinate_1_world_lng,
                    box_coordinate_1_world_lat,
                    box_coordinate_2_world_lng,
                    box_coordinate_2_world_lat,
                    y_length)

    map.get_picture()
