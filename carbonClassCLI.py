from inputDataCLI import open_shp
from carbonStockCalcCLI import data_sampling, growth_stock_calc, carbon_stock_period, carbon_soil
from inputDataCLI import get_config_section
import numpy as np
from osgeo import gdal


class ValidationException(Exception):
    pass


class CarbonCalc:
    """Класс для расчета углерода по периоду и шейпфайлу для полигона с хар-ками"""

    def __init__(self, polygon_name, begin_period, end_period, intensive, shp_path, outfile):

        # наименование полигона
        self.polygon_name = polygon_name

        # начало периода для расчета (год)
        self.begin_period = begin_period

        # конец периода для расчета (год)
        self.end_period = end_period

        # переменная для интенсивного лесопользования
        self.intensive = intensive

        # путь до шейпфайла
        self.shp_path = shp_path

        # имя файла вывода
        self.outfile = outfile

        # переменная для площади шейпфайла
        self.area = 0

    def add_shp(self):
        """Шейпфайл. Проверка на пересечение с полигоном. Площадь шейпфайла в Га"""

        self.area = open_shp(self.polygon_name, self.shp_path)

    def calc_carbon(self):
        """Расчет углерода для шейпфайла по полигону"""

        # возвращаем кортеж с массивами полигона для расчетов
        data_sample = data_sampling(self.polygon_name, self.shp_path)

        # справочник кодов пород и конверсионных коэффициентов для них по гр. возраста
        conv_path = 'Polygons/%s/conversion_rates.cfg' % self.polygon_name
        conv_dict = get_config_section(conv_path)

        # словарь моделей прогноза прироста запаса древостоя по его возрасту
        models_zapas_path = 'Polygons/%s/models_zapas.cfg' % self.polygon_name
        models_zapas_dict = get_config_section(models_zapas_path)

        # справочник для калькулятора, чтобы закодировать массив с возрастами в группы возрастов
        coding_vozrast_path = 'Polygons/%s/age_group_codes.cfg' % self.polygon_name
        coding_vozrast_dict = get_config_section(coding_vozrast_path)

        # справочник с почвенными моделями по типу леса (хвойный или лиственный)
        models_soil_path = 'Polygons/%s/soil_models.cfg' % self.polygon_name
        models_soil_dict = get_config_section(models_soil_path)

        # ########################### (ДЛЯ ПОРОД С ДОЛЕВЫМ УЧАСТИЕМ) ##########################################

        # для сценариев с долевым участием пород длина кортежа с необходимыми массивами и данными равна 13
        if len(data_sample) == 15:

            # проверка на включение условия интенсивного лесопользования
            if self.intensive:

                # увеличиваем исходные бонитеты на 1 для всех кроме 1го
                arr_bonitet = np.where(data_sample[6] > 1, data_sample[6] - 1, data_sample[6])

            else:

                # если галка интенсивного лесопользования не стоит, бонитеты остаются исходными
                arr_bonitet = data_sample[6]

            # накопленный углерод за указанный пользователем период

            # ввод расчетного периода и формирование массивов (для преобладающих и дополнительных пород)
            # с прогнозами запасов (м.куб на Га)
            # в 3D массиве чётный слой - возраст, нечётный слой - запас идут последовательно друг за другом
            # с начала расчетного периода и до его конца (нумерация слоев с нуля)

            # для преобладающих пород
            arr_growth_stock_main = growth_stock_calc(data_sample[0], arr_bonitet, data_sample[2],
                                                      data_sample[7], models_zapas_dict,
                                                      self.polygon_name, self.begin_period,
                                                      self.end_period)

            # для дополнительных пород
            arr_growth_stock_additional = growth_stock_calc(data_sample[1], arr_bonitet, data_sample[3],
                                                            data_sample[8], models_zapas_dict,
                                                            self.polygon_name, self.begin_period,
                                                            self.end_period)

            # расчёт накопленного углерода на каждый вегетационный год расчетного периода
            # для преобладающих пород
            arr_c_main = carbon_stock_period(arr_growth_stock_main, data_sample[0], coding_vozrast_dict,
                                             conv_dict, data_sample[11], -data_sample[12])

            # для дополнительных пород
            arr_c_additional = carbon_stock_period(arr_growth_stock_additional, data_sample[1],
                                                   coding_vozrast_dict, conv_dict, data_sample[11],
                                                   -data_sample[12])

            # углерод в почвах + климатические характеристики
            arr_c_soil = carbon_soil(data_sample[0], data_sample[9], data_sample[10], models_soil_dict,
                                     self.polygon_name, data_sample[11], -data_sample[12])

            # общий запас углерода на конец периода
            stored_carbon = np.sum((arr_c_main[:, :, -1] + arr_c_additional[:, :, -1]) - arr_c_soil)

            # вывод в консоль
            print('\r%.6f tons per %.2f hectare shapefile area'
                  % (float(stored_carbon), self.area / 10000))

            # собираем в GEOTIFF рассчитанный массив запаса углерода для расчетного периода
            f_path = 'Polygons/%s/out/%s.tif' % (self.polygon_name, self.outfile)

            if f_path:
                cols = arr_c_main.shape[1]
                rows = arr_c_main.shape[0]
                bands = arr_c_main.shape[-1]
                driver = gdal.GetDriverByName("gtiff")
                outdata = driver.Create(f_path, cols, rows, bands, gdal.GDT_Float32)
                outdata.SetGeoTransform(data_sample[13])
                outdata.SetProjection(data_sample[14])
                for band in range(bands):
                    outdata.GetRasterBand(band + 1).WriteArray((arr_c_main[:, :, band]
                                                                + arr_c_additional[:, :, band]) - arr_c_soil)
                outdata.FlushCache()

        # ########################### (ТОЛЬКО ПРЕОБЛАДАЮЩАЯ ПОПРОДА) ##########################################

        # для сценариев с одной породой в пикселе (однослойный tif с породами)
        elif len(data_sample) == 11:

            # проверка на включение условия интенсивного лесопользования
            if self.intensive:

                # увеличиваем исходные бонитеты на 1 для всех кроме 1го
                arr_bonitet = np.where(data_sample[3] > 1, data_sample[3] - 1, data_sample[3])
            else:

                # если галка интенсивного лесопользования не стоит, бонитеты остаются исходными
                arr_bonitet = data_sample[3]

            # накопленный углерод за указанный пользователем период

            # ввод расчетного периода и формирование массива для преобладающих пород
            # с прогнозами запасов (м.куб на Га)
            # в 3D массиве чётный слой - возраст, нечётный слой - запас идут последовательно друг за другом
            # с начала расчетного периода и до его конца (нумерация слоев с нуля)

            # для преобладающих пород
            arr_growth_stock = growth_stock_calc(data_sample[0], arr_bonitet, data_sample[1],
                                                 data_sample[4], models_zapas_dict,
                                                 self.polygon_name, self.begin_period,
                                                 self.end_period)

            # расчёт накопленного углерода на каждый вегетационный год расчетного периода
            # для преобладающих пород
            arr_c = carbon_stock_period(arr_growth_stock, data_sample[0], coding_vozrast_dict,
                                        conv_dict, data_sample[7], -data_sample[8])

            # углерод в почвах + климатические характеристики
            arr_c_soil = carbon_soil(data_sample[0], data_sample[5], data_sample[6], models_soil_dict,
                                     self.polygon_name, data_sample[7], -data_sample[8])

            # общий запас углерода на конец периода
            stored_carbon = np.sum(arr_c[:, :, -1] - arr_c_soil)

            # вывод в консоль
            print('\r%.2f tons per %.2f hectare shapefile area'
                  % (float(stored_carbon), self.area / 10000))

            # собираем в GEOTIFF рассчитанный массив запаса углерода для расчетного периода
            f_path = 'Polygons/%s/out/%s.tif' % (self.polygon_name, self.outfile)

            if f_path:
                cols = arr_c.shape[1]
                rows = arr_c.shape[0]
                bands = arr_c.shape[-1]
                driver = gdal.GetDriverByName("gtiff")
                outdata = driver.Create(f_path, cols, rows, bands, gdal.GDT_Float32)
                outdata.SetGeoTransform(data_sample[9])
                outdata.SetProjection(data_sample[10])
                for band in range(bands):
                    outdata.GetRasterBand(band + 1).WriteArray(arr_c[:, :, band] - arr_c_soil)
                outdata.FlushCache()
