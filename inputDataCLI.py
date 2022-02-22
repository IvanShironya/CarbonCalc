import json
from sys import exit
import logging
from osgeo import ogr, gdal, gdal_array
import os
import configparser


def open_shp(polygon_name, shpfile_path):
    """"""

    # открываем json-файл полигона
    try:

        f = open('Polygons/%s/%s.json' % (polygon_name, polygon_name))

        # json в словарь python
        data = json.load(f)
        f.close()

        # в данных по полигону возможны только 2 вида данных по породам древостоя
        porody_proportion_geometry = data[polygon_name]['porody_proportion']['geometry']
        porody_geometry = data[polygon_name]['porody']['geometry']

        # когда tif с породами древостоя с долевым участием
        if porody_geometry is None and porody_proportion_geometry:

            # получаем из json его геометрию
            list_geometry_tif = list(data[polygon_name]['porody_proportion']['geometry'])

            # получаем из json его ширину
            width_tif = data[polygon_name]['porody_proportion']['width']

            # получаем из json его высоту
            height_tif = data[polygon_name]['porody_proportion']['height']

        # когда tif с породами древостоя с породой в пикселе (однослойный)
        else:
            list_geometry_tif = list(data[polygon_name]['porody']['geometry'])
            width_tif = data[polygon_name]['porody']['width']
            height_tif = data[polygon_name]['porody']['height']

        # определяем ограничивающую рамку растра с породами и создаем геометрию на ее основе
        xRight = list_geometry_tif[0] + width_tif * list_geometry_tif[1]
        yRight = list_geometry_tif[3] + height_tif * list_geometry_tif[5]
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(list_geometry_tif[0], list_geometry_tif[3])
        ring.AddPoint(list_geometry_tif[0], yRight)
        ring.AddPoint(xRight, yRight)
        ring.AddPoint(xRight, list_geometry_tif[3])
        ring.AddPoint(list_geometry_tif[0], list_geometry_tif[3])
        rasterGeometry = ogr.Geometry(ogr.wkbPolygon)
        rasterGeometry.AddGeometry(ring)

        while True:

            # переменная для площади полигонов шейпфайла
            area = 0

            try:
                shp_path = shpfile_path

                if not os.path.isfile(shp_path):
                    logging.error("Shapefile not found in path!")
                    exit(2)

                shp = ogr.Open(shp_path)
                layer = shp.GetLayer()

                # общая площадь всех полигонов шейпфайла
                for feature in layer:
                    geom = feature.GetGeometryRef()
                    area_shp = geom.GetArea()
                    area += area_shp

                featureCount = layer.GetFeatureCount()

                # пустой список статусов пересечений полигонов с растром (TRUE/FALSE)
                status_intersect_shp = []

                # определяем геометрию векторного многоугольника
                for i in range(featureCount):
                    polygon = layer.GetFeature(i)
                    vectorGeometry = polygon.GetGeometryRef()
                    status_intersect_shp.append(rasterGeometry.Intersect(vectorGeometry))

                next(elt for elt in status_intersect_shp if elt)
                break

            except StopIteration:

                logging.error("Shapefile does not intersect with the polygon!")
                exit(2)

        return area
    except FileNotFoundError:
        logging.error("No polygon with specified name or polygon JSON-file not found in polygon folder!")
        exit(2)

    except KeyError:
        logging.error("No polygon with specified name or the polygon name does not match the polygon "
                      "name in the JSON-file!")
        exit(2)


def arr_from_shp(raster, shapefile_path, res_x, res_y, no_data):
    """Полигоны шейпфайла в массив с информацией из пикселей растра
    :param raster: растер
    :param shapefile_path: путь до шейпфайла
    :param res_x: разрешение по X
    :param res_y:  разрешение по Y
    :param no_data: значение для "нет данных"
    :return массив с информацией из пикселей, которые пересекаются с растром"""

    # Вырезаем зону для расчета из растра по шейпфайлу
    ds = gdal.Warp('', raster, format='MEM', xRes=res_x, yRes=res_y, outputType=gdal.GDT_Float32,
                   workingType=gdal.GDT_Float32, cutlineDSName=shapefile_path, srcNodata=no_data, dstNodata=0)

    # Вырезанный фрагмент из растра в массив
    arr = gdal_array.DatasetReadAsArray(ds, 0, 0, ds.RasterXSize, ds.RasterYSize)

    return arr


def get_config_section(file_conf_path):
    """Функция чтения конфиг-файла (справочника) в словарь
    :param file_conf_path: путь к справочнику с именем файла
    :return: возращает словарь"""

    config = configparser.RawConfigParser()
    config.read(file_conf_path)
    config_dict = {section: dict(config.items(section)) for section in config.sections()}
    return config_dict
