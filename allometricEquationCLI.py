import joblib
import numpy as np


def load_model(polygon_name, model_name):
    """Функция загрузки полиномиальной модели для прогноза
        :param polygon_name: наименование полигона
        :param model_name: имя файла модели с кодом породы и кодом бонитета
        :return: модель"""

    model = joblib.load('Polygons/%s/models/%s' % (polygon_name, model_name))
    return model


def model_prediction(polygon_name, model_name, val):
    """Функция прогноза по модели
    :param polygon_name: наименование полигона
    :param model_name: имя файла модели с кодом породы и кодом бонитета из справочника моделей (конфигфайл)
    :param val: значение для прогноза
    :return: прогноз по модели"""

    model = load_model(polygon_name, model_name)
    prediction = model(val)
    return prediction


def arr_predict(arr_porody, arr_bonitet, arr_val, models_dict, polygon_name):
    """Функция формирования массива по прогнозам из моделей (аллометрические уравнения)
    :param arr_porody: массив с породами древостоя
    :param arr_bonitet: массив с бонитетами древостоя
    :param arr_val: массив с значениями для прогноза (например, диаметры или возраст древостоя)
    :param models_dict: словарь (справочник) моделей
    :param polygon_name: наименование полигона
    :return: возращает массив с прогнозами"""

    # нулевой массив для прогнозов
    arr_predictions = np.zeros((arr_porody.shape[0], arr_porody.shape[1]), dtype=float)

    # счетчик бонитетов для которых нет кодов в справочнике
    err_bonitet_counter = 0

    # заполняем массив прогнозами из модели по коду породы и бонитету древостоя (для каждого пикселя)
    for i in range(len(arr_porody)):
        for j in range(len(arr_porody[i])):

            key_porody = str(int(arr_porody[i, j]))
            key_bonitet = str(int(arr_bonitet[i, j]))

            if key_porody == '0' and key_bonitet == '0':
                arr_predictions[i, j] = 0.
            elif models_dict.get(key_porody) is None:
                arr_predictions[i, j] = 0.
            elif models_dict.get(key_porody, {}).get(key_bonitet) is None:
                err_bonitet_counter += 1
                arr_predictions[i, j] = 0.
            else:
                arr_predictions[i, j] = model_prediction(polygon_name, models_dict[key_porody][key_bonitet],
                                                         arr_val[i, j])

    return arr_predictions
