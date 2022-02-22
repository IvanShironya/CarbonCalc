from osgeo import gdal
import numpy as np


def arr_to_raster(arr, geometry, projection):
    """Метод конвертирует 3D массив в растер в памяти
    :param arr: 3D массив вида (band, width, height)
    :param geometry: геометрия растра-эталона
    :param projection: проекция растра-эталона
    :return возращает растр в памяти"""

    # массив в растр (в памяти)
    cols = arr.shape[2]
    rows = arr.shape[1]
    bands = arr.shape[0]
    driver = gdal.GetDriverByName("MEM")
    raster = driver.Create('', cols, rows, bands, gdal.GDT_Float32)
    raster.SetGeoTransform(geometry)
    raster.SetProjection(projection)
    for band in range(bands):
        raster.GetRasterBand(band + 1).WriteArray(arr[band, :, :])

    return raster


def arr_age_recoding(arr_porody, arr_age, gr_age_dict):
    """Функция кодирует массив с возрастами древостоя в массив групп возрастов по справочнику
    :param arr_porody: массив с кодами пород
    :param arr_age: массив с возрастами
    :param gr_age_dict: словарь соответствия кода порода+группа возраста и их диапазон возрастов
    :return: массив с кодами групп возраста по породе древостоя"""

    # нулевой массив
    arr_gr_age = np.zeros((arr_porody.shape[0], arr_porody.shape[1]), dtype=float)

    # заполняем массив по коду породы и возрасту древостоя (для каждого пикселя)
    for i in range(len(arr_porody)):
        for j in range(len(arr_porody[i])):

            key_porody = str(int(arr_porody[i, j]))
            val_grvozr = int(arr_age[i, j])

            if key_porody == '0' or val_grvozr == 0:
                arr_gr_age[i, j] = 0.
            elif gr_age_dict.get(key_porody) is None:
                arr_gr_age[i, j] = 0.
            else:
                dict_code = gr_age_dict.get(key_porody)
                for key, val in dict_code.items():
                    if int(val_grvozr) < int(val):
                        arr_gr_age[i, j] = float(key)
                        break

    return arr_gr_age


def arr_diametr_decoding(arr_diametr, decoding_dict):
    """Функция расшифровывает массив с закодированными диаметрами древостоя в массив диаметров по справочнику
    :param arr_diametr: массив с кодами диаметров
    :param decoding_dict: словарь соответствия кода диаметра и его диапазона значений
    :return: массив с диаметрами древостоя"""

    # нулевой массив
    arr_decoding = np.zeros((arr_diametr.shape[0], arr_diametr.shape[1]), dtype=float)

    # счетчик отсутствующих кодов в справочнике
    err = 0

    # словарь кодов пород и их значений
    dict_diametr = decoding_dict.get('code&value')

    # заполняем массив по кодам и их диапазонам значений из справочника (для каждого пикселя)
    for i in range(len(arr_diametr)):
        for j in range(len(arr_diametr[i])):

            key_diametr = str(int(arr_diametr[i, j]))

            if key_diametr == '0':
                arr_decoding[i, j] = 0.
            elif dict_diametr.get(key_diametr) is None:
                arr_decoding[i, j] = 0.
                err += 1
            else:
                arr_decoding[i, j] = float(dict_diametr.get(key_diametr))

    return arr_decoding
