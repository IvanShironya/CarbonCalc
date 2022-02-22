import json
import numpy as np
from calculatorToolsCLI import arr_to_raster, arr_age_recoding, arr_diametr_decoding
from inputDataCLI import arr_from_shp, get_config_section
from allometricEquationCLI import arr_predict
import math


def data_sampling(polygon_name, shp_path):
    """Формирует массивы полученные из пересечения растров с шейпфайлом + параметры растра с породами (эталон)"""

    # открываем json-файл
    f = open('Polygons/%s/%s.json' % (polygon_name, polygon_name))

    # json в словарь python
    data = json.load(f)
    f.close()

    def arr_for_calc(dict_for):
        """Метод возвращает массив numpy для зоны шейпфайла конкретного растра
        :param dict_for: словарь конкретного растра"""

        # формируем numpy массив запасов из словаря
        arr = np.array(dict_for['array'])

        # если сформированный массив 2d его необходимо преобразовать в 3d
        if arr.ndim == 2:
            arr = arr.reshape((1, arr.shape[0], arr.shape[1]))

        # геометрия для растра из словаря
        geometry = dict_for['geometry']

        # проекция для растра из словаря
        projection = dict_for['projection']

        # 3d массив в растр
        raster = arr_to_raster(arr, geometry, projection)

        # разрешение растра из словаря
        res_x = geometry[1]
        res_y = geometry[5]

        # значение для "нет данных" из словаря
        no_data = dict_for['noData']

        # массив из пересечения шейпфайла с растром
        arr_calc = arr_from_shp(raster, shp_path, res_x, res_y, no_data)

        return arr_calc

    # не меняющиеся и обязательные массивы для всех сценариев
    arr_bonitet = arr_for_calc(data[polygon_name]['bonitet'])
    arr_zapas = arr_for_calc(data[polygon_name]['zapas'])
    arr_soil = arr_for_calc(data[polygon_name]['soil'])
    arr_weather = arr_for_calc(data[polygon_name]['weather'])

    # справочник для калькулятора, чтобы закодировать массив с абс.возрастами в группы возрастов
    vozrast_to_gr_path = 'Polygons/%s/age_group_codes.cfg' % polygon_name
    vozrast_to_gr_dict = get_config_section(vozrast_to_gr_path)

    # справочник кодов диаметров
    code_diametr_path = 'Polygons/%s/diameter_codes.cfg' % polygon_name
    code_diametr_dict = get_config_section(code_diametr_path)

    # справочник моделей прогноза возраста древостоя по диаметру
    models_vozrast_path = 'Polygons/%s/models_vozrast.cfg' % polygon_name
    models_vozrast_dict = get_config_section(models_vozrast_path)

    # пустой список для сформированных массивов под сценарий данных для полигона
    sample_list = list()

    # ####################### СЦЕНАРИЙ 1 (ПРЕОБЛАДАЮЩИЕ И ДОПОЛНИТЕЛЬНЫЕ ПОРОДЫ) ######################################

    if data[polygon_name]['porody_proportion']['geometry'] and data[polygon_name]['abs_vozrast']['geometry']:

        arr_porody_proportion = arr_for_calc(data[polygon_name]['porody_proportion'])

        # массив с основными породами для зоны шейпфайла
        arr_main_species = arr_porody_proportion[0, :, :]

        # массив с дополнительными породами для зоны шейпфайла
        arr_additional_species = arr_porody_proportion[2, :, :]

        arr_abs_vozrast = arr_for_calc(data[polygon_name]['abs_vozrast'])

        # в 1м слое возраст преобладающих пород
        arr_vozrast_main = arr_abs_vozrast[0, :, :]

        # во 2м слое возраст дополнительных пород
        arr_vozrast_additional = arr_abs_vozrast[1, :, :]

        # массив с запасами преобладающих пород для зоны шейпфайла
        arr_zapas_main = arr_zapas * (arr_porody_proportion[1, :, :] / 10)

        # массив с запасами дополнительных пород для зоны шейпфайла
        arr_zapas_additional = arr_zapas * (arr_porody_proportion[3, :, :] / 10)

        # по справочнику закодируем его в необходимый для калькулятора растр с группами возраста
        # для преобладающих пород
        arr_gr_vozrast_main = arr_age_recoding(arr_main_species, arr_vozrast_main, vozrast_to_gr_dict)

        # для дополнительных пород
        arr_gr_vozrast_additional = arr_age_recoding(arr_additional_species, arr_vozrast_additional,
                                                     vozrast_to_gr_dict)

        # разрешение растра с породами для кортежа
        geometry = data[polygon_name]['porody_proportion']['geometry']
        res_x = geometry[1]
        res_y = geometry[5]

        # проекция растра для кортежа
        projection = data[polygon_name]['porody_proportion']['projection']

        # порядок массивов в sample_list для сценариев с долевым участием пород древостоя:
        # 1й массив: преобладающие породы
        # 2й массив: дополнительные породы
        # 3й массив: возраст (абсолютные значения) преобладающих пород
        # 4й массив: возраст (абсолютные значения) дополнительных пород
        # 5й массив: группы возрастов для преобладающих пород
        # 6й массив: группы возрастов для дополнительных пород
        # 7й массив: бонитеты
        # 8й массив: запасы преобладающих пород
        # 9й массив: запасы дополнительных пород
        # 10й массив: типы почв
        # 11й массив: климатические характеристики
        # 12й элемент кортежа: разрешение растра с породами древостоя по X
        # 13й элемент кортежа: разрешение растра с породами древостоя по Y
        # 14й элемент кортежа: геометрия растра с породами древостоя
        # 15й элемент кортежа: проекция растра с породами древостоя
        sample_list.extend([arr_main_species, arr_additional_species, arr_vozrast_main, arr_vozrast_additional,
                            arr_gr_vozrast_main, arr_gr_vozrast_additional, arr_bonitet, arr_zapas_main,
                            arr_zapas_additional, arr_soil, arr_weather, res_x, res_y, geometry, projection])

    # нет растра с абс. возрастом древостоя, но есть растр с кодами диаметров или диаметрами
    elif data[polygon_name]['porody_proportion']['geometry'] and not data[polygon_name]['abs_vozrast']['geometry']:

        arr_porody_proportion = arr_for_calc(data[polygon_name]['porody_proportion'])

        # массив с основными породами для зоны шейпфайла
        arr_main_species = arr_porody_proportion[0, :, :]

        # массив с дополнительными породами для зоны шейпфайла
        arr_additional_species = arr_porody_proportion[2, :, :]

        # есть tif с кодами диаметров
        if data[polygon_name]['code_diametr']['geometry']:

            arr_code_diametr = arr_for_calc(data[polygon_name]['code_diametr'])

            # коды диаметров в диаметры по справочнику кодов
            arr_diametr = arr_diametr_decoding(arr_code_diametr, code_diametr_dict)

        # в противном случае должен быть tif с диаметрами
        else:

            arr_diametr = arr_for_calc(data[polygon_name]['diametr'])

        # прогнозирование абс. возрастов по диаметрам
        arr_vozrast_main = np.round(arr_predict(arr_main_species, arr_bonitet, arr_diametr, models_vozrast_dict,
                                                polygon_name))
        arr_vozrast_additional = np.round(arr_predict(arr_additional_species, arr_bonitet, arr_diametr,
                                                      models_vozrast_dict, polygon_name))

        # массив с запасами преобладающих пород для зоны шейпфайла
        arr_zapas_main = arr_zapas * (arr_porody_proportion[1, :, :] / 10)

        # массив с запасами дополнительных пород для зоны шейпфайла
        arr_zapas_additional = arr_zapas * (arr_porody_proportion[3, :, :] / 10)

        # по справочнику закодируем его в необходимый для калькулятора растр с группами возраста
        # для преобладающих пород
        arr_gr_vozrast_main = arr_age_recoding(arr_main_species, arr_vozrast_main, vozrast_to_gr_dict)

        # для дополнительных пород
        arr_gr_vozrast_additional = arr_age_recoding(arr_additional_species, arr_vozrast_additional,
                                                     vozrast_to_gr_dict)

        # разрешение растра с породами для кортежа
        geometry = data[polygon_name]['porody_proportion']['geometry']
        res_x = geometry[1]
        res_y = geometry[5]

        # проекция растра для кортежа
        projection = data[polygon_name]['porody_proportion']['projection']

        # sample_list для сценариев с долевым участием пород древостоя:
        sample_list.extend([arr_main_species, arr_additional_species, arr_vozrast_main, arr_vozrast_additional,
                            arr_gr_vozrast_main, arr_gr_vozrast_additional, arr_bonitet, arr_zapas_main,
                            arr_zapas_additional, arr_soil, arr_weather, res_x, res_y, geometry, projection])

    # ####################### СЦЕНАРИЙ 2 (ТОЛЬКО ПРЕОБЛАДАЮЩИЕ ПОРОДЫ И ГРУППЫ ВОЗРАСТА) ##############################

    elif data[polygon_name]['porody']['geometry'] and data[polygon_name]['gr_vozrast']['geometry']:

        arr_porody = arr_for_calc(data[polygon_name]['porody'])
        arr_gr_vozrast = arr_for_calc(data[polygon_name]['gr_vozrast'])

        # есть tif с кодами диаметров
        if data[polygon_name]['code_diametr']['geometry']:

            arr_code_diametr = arr_for_calc(data[polygon_name]['code_diametr'])

            # коды диаметров в диаметры по справочнику кодов
            arr_diametr = arr_diametr_decoding(arr_code_diametr, code_diametr_dict)

        # в противном случае должен быть tif с диаметрами
        else:

            arr_diametr = arr_for_calc(data[polygon_name]['diametr'])

        # прогнозирование абс. возрастов по диаметрам
        arr_vozrast = np.round(arr_predict(arr_porody, arr_bonitet, arr_diametr, models_vozrast_dict, polygon_name))

        # разрешение растра с породами для кортежа
        geometry = data[polygon_name]['porody']['geometry']
        res_x = geometry[1]
        res_y = geometry[5]

        # проекция растра для кортежа
        projection = data[polygon_name]['porody']['projection']

        # порядок массивов в sample_list для сценариев только с преобладающей породой древостоя:
        # 1й массив: преобладающие породы
        # 2й массив: возраст (абсолютные значения) преобладающих пород
        # 3й массив: группы возрастов для преобладающих пород
        # 4й массив: бонитеты
        # 5й массив: запасы преобладающих пород
        # 6й массив: типы почв
        # 7й массив: климатические характеристики
        # 8й элемент кортежа: разрешение растра с породами древостоя по X
        # 9й элемент кортежа: разрешение растра с породами древостоя по Y
        # 10й элемент кортежа: геометрия растра с породами древостоя
        # 11й элемент кортежа: проекция растра с породами древостоя
        sample_list.extend([arr_porody, arr_vozrast, arr_gr_vozrast, arr_bonitet, arr_zapas, arr_soil,
                            arr_weather, res_x, res_y, geometry, projection])

    # нет растра с группами возраста древостоя, но есть растр с кодами диаметров или диаметрами
    elif data[polygon_name]['porody']['geometry'] and not data[polygon_name]['gr_vozrast']['geometry']:

        arr_porody = arr_for_calc(data[polygon_name]['porody'])

        # есть tif с кодами диаметров
        if data[polygon_name]['code_diametr']['geometry']:

            arr_code_diametr = arr_for_calc(data[polygon_name]['code_diametr'])

            # коды диаметров в диаметры по справочнику кодов
            arr_diametr = arr_diametr_decoding(arr_code_diametr, code_diametr_dict)

        # в противном случае должен быть tif с диаметрами
        else:

            arr_diametr = arr_for_calc(data[polygon_name]['diametr'])

        # прогнозирование абс. возрастов по диаметрам
        arr_vozrast = np.round(arr_predict(arr_porody, arr_bonitet, arr_diametr, models_vozrast_dict, polygon_name))

        # возраст перекодируется в группу возраста
        arr_gr_vozrast = arr_age_recoding(arr_porody, arr_vozrast, vozrast_to_gr_dict)

        # разрешение растра с породами для кортежа
        geometry = data[polygon_name]['porody']['geometry']
        res_x = geometry[1]
        res_y = geometry[5]

        # проекция растра для кортежа
        projection = data[polygon_name]['porody']['projection']

        sample_list.extend([arr_porody, arr_vozrast, arr_gr_vozrast, arr_bonitet, arr_zapas, arr_soil,
                            arr_weather, res_x, res_y, geometry, projection])

    # кортеж сформированных массивов под сценарий данных для полигона
    sample_data = tuple(sample_list)

    return sample_data


def growth_stock_calc(arr_porody, arr_bonitet, arr_age, arr_zapas, zapas_dict, polygon_name,
                      begin_period, end_period):
    """Функция выводит 3D массив возрастов и запасов на каждый вегетационный год заданного пользователем
    расчетного периода
    :param arr_porody: массив с породами
    :param arr_bonitet: массив с бонитетами
    :param arr_age: массив с возрастами (на начало периода)
    :param arr_zapas: массив с запасами (на начало периода)
    :param zapas_dict: словарь моделей для прогнозирования прироста запаса
    :param polygon_name: наименование полигона
    :param begin_period: начало расчетного периода
    :param end_period: конец расчетного периода
    :return: 3D массив запасов и возрастов, где четные слои - абс.возраст, и нечетные - запасы"""

    # пустой список для будущих массивов с возрастом и запасом
    list_arrays = list()

    # временный массив для возраста
    arr_age_temp = np.empty((arr_age.shape[0], arr_age.shape[1]))
    arr_age_temp[:] = np.copy(arr_age)
    del arr_age

    mask_for_age = np.where(arr_age_temp == 0, arr_age_temp, 1)

    # 1 этап: считаем корректировочный коэфф. по текущему запасу и прогнозу запасов по текущему возрасту насаждений
    # прогноз запасов для текущего возраста насаждений
    arr_zapas_current = arr_predict(arr_porody, arr_bonitet, arr_age_temp, zapas_dict, polygon_name)

    # корректировочный коэффициент для прогнозируемых запасов
    arr_coeff = np.divide(arr_zapas, arr_zapas_current, out=np.zeros_like(arr_zapas), where=arr_zapas_current != 0)

    # 2й этап: для каждого года в расчетном периоде добавляем в список массивов новый массив возраста и запаса
    # для соотв. вегетационного года

    # переменная для начала периода (с какого возраста древостоя начинать выполнять прогноз запасов)
    start_age = begin_period - 2021
    arr_age_temp = arr_age_temp + (mask_for_age * start_age)

    for i in range((end_period - begin_period) + 1):

        # спрогнозируем массив запасов для новых восзрастов древостоя
        arr_growth_stock = arr_predict(arr_porody, arr_bonitet, arr_age_temp, zapas_dict, polygon_name)

        # корректируем спрогнозированный массив запасов
        arr_growth_stock = arr_growth_stock * arr_coeff

        # массивы с возрастом и запасом в список
        list_arrays.append(arr_age_temp.copy())
        list_arrays.append(arr_growth_stock.copy())

        arr_age_temp += mask_for_age

    # список в кортеж
    arrays = tuple(list_arrays)

    # кортеж в массив
    arr_zapas_range = np.dstack(arrays)

    return arr_zapas_range


def carbon_stock_calc(arr_porody, arr_grvozr, arr_zapas, conv_dict, x, y):
    """Функция расчета запаса углерода в биомассе древостоя
    :param arr_porody: массив с породами древостоя
    :param arr_grvozr: массив с группами возраста древостоя
    :param arr_zapas: массив с запасами древостоя (м куб на Га)
    :param conv_dict: словарь конфигфайла с конверсионными коэффициентами
    :param x: разрешение по X растра с породами
    :param y: разрешение по Y растра с породами
    :return: возращает массив с накопленным углеродом в биомассе древостоя
    """

    # преобразование массива с запасами под разрешение растра с породами древостоя
    arr_zapas = arr_zapas * ((x * y) / 10000)

    # нулевой массив конверсионных коэффициентов
    arr_conv = np.zeros((arr_porody.shape[0], arr_porody.shape[1]), dtype=float)

    # счетчик пород для которых нет кодов в справочнике
    err_porody_counter = 0

    # счетчик гр. возраста для которых нет кодов
    err_grvozr_counter = 0

    # заполняем массив конверсионных коэффициентов по коду породы и группе возраста древостоя (для каждого пикселя)
    for i in range(len(arr_porody)):
        for j in range(len(arr_porody[i])):

            key_porody = str(int(arr_porody[i, j]))
            key_grvozr = str(int(arr_grvozr[i, j]))

            if key_porody == '0' and key_grvozr == '0':
                arr_conv[i, j] = 0.
            elif conv_dict.get(key_porody) is None:
                err_porody_counter += 1
                arr_conv[i, j] = 0.
            elif conv_dict.get(key_porody, {}).get(key_grvozr) is None:
                err_grvozr_counter += 1
                arr_conv[i, j] = 0.
            else:
                arr_conv[i, j] = conv_dict[key_porody][key_grvozr]

    # расчет запаса углерода
    arr_c = arr_zapas * arr_conv

    return arr_c


def carbon_stock_period(arr_growth_stock, arr_porody, recoding_dict, conv_dict, res_x, res_y):
    """Метод возвращает 3d массив с накопленным углеродом за период указанный пользователем, где
    каждый слой массива равен вегетационному периоду от его начала и до конца
    :param arr_growth_stock: массив возрастов и запасов за каждый вегетационный период (четные слои - абс. возраст,
    нечетные слои - запас
    :param arr_porody: массив с породами древостоя
    :param recoding_dict: словарь для перекодировки возраста древостоя в группу возраста
    :param conv_dict: словарь конверсионных коэффициентов для пород и их групп возраста
    :param res_x: разрешение эталонного растра по X
    :param res_y: разрешение эталонного растра по Y
    """

    # пустой список для будущего массива с накопленным углеродом за период
    list_arr = list()

    # расчёт накопленного углерода на каждый вегетационный год расчетного периода
    for i in range(0, arr_growth_stock.shape[-1], 2):
        # возраст перекодируется в группу возраста
        # для преобладающих пород
        gr_vozrast = arr_age_recoding(arr_porody, arr_growth_stock[:, :, i], recoding_dict)

        # накопленный углерод для 1го вегетационного года из расчетного периода
        # для преобладающей породы
        arr_c_temp = carbon_stock_calc(arr_porody, gr_vozrast, arr_growth_stock[:, :, i + 1],
                                       conv_dict, res_x, res_y)

        # добавляем в список
        list_arr.append(arr_c_temp.copy())

    # список в кортеж
    arrays = tuple(list_arr)

    # кортеж в массив, каждый слой которого равен вег. году из расчетного периода
    arr_c = np.dstack(arrays)

    return arr_c


def carbon_soil(arr_porody, arr_soil, arr_weather, dict_soil_models, polygon_name, x, y):
    """Расчет углерода в почвах по моделям
    :param arr_porody: массив с породами древостоя
    :param arr_soil: массив с типами почв
    :param arr_weather: массив с климатическим характеристиками
    :param dict_soil_models: словарь с почвенными моделями для типа леса (хвойное или лиственное)
    :param polygon_name: наименование полигона
    :param x: разрешение по X растра с породами
    :param y: разрешение по Y растра с породами
    :return: возращает массив с накопленным углеродом в почвах"""

    # нулевой массив с накопленным в почвах углеродом
    arr_carbon_soil = np.zeros((arr_porody.shape[0], arr_porody.shape[1]), dtype=float)

    # счетчик ошибок (отсутствующие климатические хар-ки)
    err_weather_counter = 0

    # счетчик ошибок (отсутствующие типы почв)
    err_soil_counter = 0

    for i in range(len(arr_porody)):
        for j in range(len(arr_porody[i])):

            key_porody = str(int(arr_porody[i, j]))
            key_soil = str(int(arr_soil[i, j]))

            if key_porody == '0' or key_soil == '0':
                arr_carbon_soil[i, j] = 0.

            elif dict_soil_models.get(key_porody) is None:
                arr_carbon_soil[i, j] = 0.

            elif dict_soil_models.get(key_porody, {}).get(key_soil) is None:
                err_soil_counter += 1
                arr_carbon_soil[i, j] = 0.

            else:
                model_name = dict_soil_models[key_porody][key_soil]
                temp_dict_path = 'Polygons/%s/models/%s' % (polygon_name, model_name)
                temp_dict = get_config_section(temp_dict_path)
                test_val = arr_weather[:, i, j].tolist()
                test_val.append(1.)
                if sum(test_val) != 1.:
                    fgp_list = list()
                    for value in temp_dict['CF Coefficients'].values():
                        temp_list = [float(item) for item in value.split(',')]
                        temp_fgp = sum([a * b for a, b in zip(test_val, temp_list)])
                        fgp_list.append(temp_fgp)

                    sum_fgp = sum([math.exp(item - max(fgp_list)) for item in fgp_list])

                    prob_list = [math.exp(item - max(fgp_list)) / sum_fgp for item in fgp_list]

                    values_list = [float(value) for value in temp_dict['Mean Values for Group'].values()]

                    # по модели считается углерод в г на кв. метр, поэтому результат переводим
                    # в тонны на разрешение пикселя
                    arr_carbon_soil[i, j] = (sum([a * b for a, b in zip(prob_list, values_list)]) / 1000000) * (x * y)

                else:
                    arr_carbon_soil[i, j] = 0
                    err_weather_counter += 1

    return arr_carbon_soil
