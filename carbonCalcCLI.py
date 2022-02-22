from sys import exit, stdout
import argparse
import logging
# import os
from carbonClassCLI import ValidationException, CarbonCalc
import itertools
import time
import threading

# Расположение proj.db
# os.environ['PROJ_LIB'] = 'proj/'
# Расположение GDAL
# os.environ['GDAL_DATA'] = 'data/'


def main():
    parser = argparse.ArgumentParser(description="Generates carbon GeoTIFF by shapefile and polygon with "
                                                 "characteristics")
    parser.add_argument("-p", "--polygon", type=str, help="The name of the polygon with the corresponding name "
                                                          "of the directory where the JSON-file, models and "
                                                          "reference books is located", required=True)
    parser.add_argument("-b", "--begin", type=int, help="Beginning of period, in YYYY format from 2021 to 2040",
                        required=True)
    parser.add_argument("-e", "--end", type=int, help="End of period, in YYYY format from 2021 to 2040",
                        required=True)
    parser.add_argument("-i", "--intensive", action='store_true', help="Intensive forest management",
                        required=False)
    parser.add_argument("-s", "--shapefile", type=str, help="Shapefile path", required=True)
    parser.add_argument("-o", "--out", type=str, help="Output file name without extension. After calculations, "
                                                      "the output GeoTIFF file will be located in /out folder "
                                                      "of the polygon", required=True)
    args = parser.parse_args()

    # формат для отображения ошибок (сообщений)
    logging.basicConfig(format='%(levelname)s: %(message)s')

    if 2021 <= args.begin <= 2040 and 2021 <= args.end <= 2040 and args.begin <= args.end:

        # задействуем класс для расчета углерода по параметрам от пользователя и полигону
        cli = CarbonCalc(args.polygon, args.begin, args.end, args.intensive, args.shapefile, args.out)

        # проверка шейпфайла
        cli.add_shp()

        # анимация для процесса вычисления (статус)
        process_done = False

        def process_animation():
            """Простая анимация для процесса вычисления в консоли"""

            for c in itertools.cycle(['|', '/', '-', '\\']):
                if process_done:
                    break
                stdout.write('\rCalculation ' + c)
                stdout.flush()
                time.sleep(0.1)
            stdout.write('\rDone! ')

        # запускаем анимацию процесса вычисления, которая будет выполняться в отдельном потоке
        t = threading.Thread(target=process_animation)
        t.start()

        # считаем углерод (длительный процесс)
        cli.calc_carbon()

        process_done = True

    else:
        logging.error("Available period: from 2021 to 2040 years! The beginning of the period cannot be greater "
                      "than the end of the period for calculation!")
        exit(2)


if __name__ == "__main__":
    try:
        main()
    except ValidationException as e:
        logging.error(e)
    except Exception as e:
        logging.exception(e)
