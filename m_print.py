import datetime
import inspect
import sys

def e_print(*args: object, **kwargs: object) -> object:
    """
    红色错误打印信息
    """
    color = '\033[31m'
    now = datetime.datetime.now()
    milliseconds = now.microsecond // 1000  # 截断为三位微秒（毫秒）
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.{:03d}".format(milliseconds))
    caller_frame = inspect.stack()[1]  # 获取调用函数的栈帧
    caller_module = inspect.getmodule(caller_frame[0])
    func_name = caller_frame[3]
    line = caller_frame[2]
    message = ' '.join(map(str, args))  # 将参数转换为字符串并拼接
    # print(f'[{current_time}] {message} {caller_module.__name__}.{func_name}():{line}]', **kwargs)
    print(f'{color}[{current_time}] {message} [{caller_module.__name__}.{func_name}():{line}]', **kwargs)


def d_print(*args: object, **kwargs: object) -> object:
    """
    常规错误打印信息
    """
    color = '\033[0m'
    now = datetime.datetime.now()
    milliseconds = now.microsecond // 1000  # 截断为三位微秒（毫秒）
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.{:03d}".format(milliseconds))
    caller_frame = inspect.stack()[1]  # 获取调用函数的栈帧
    caller_module = inspect.getmodule(caller_frame[0])
    func_name = caller_frame[3]
    line = caller_frame[2]
    message = ' '.join(map(str, args))  # 将参数转换为字符串并拼接
    # print(f'[{current_time}] {message} {caller_module.__name__}.{func_name}():{line}]', **kwargs)
    print(f'{color}[{current_time}] {message} [{caller_module.__name__}.{func_name}():{line}]', **kwargs)


def calc_crc16_modbus(arr_data):
    """
    CRC16计算-modbus
    :param arr_data: bytes
    :return: 2字节小端，crc值
    """
    crc = 0xFFFF
    polynomial = 0xA001

    for byte in arr_data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ polynomial
            else:
                crc >>= 1
    return crc


def progress_bar(progress, rate=0):
    """
    进度条显示
    :param rate: 速率
    :param progress: 进度比例
    """
    color = '\033[0m'
    now = datetime.datetime.now()
    milliseconds = now.microsecond // 1000  # 截断为三位微秒（毫秒）
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.{:03d}".format(milliseconds))

    sys.stdout.write('\r')
    sys.stdout.write(f'{color}[{current_time}]Progress: [{progress:.2f}%][{rate:.2f}k/s]')
    sys.stdout.flush()