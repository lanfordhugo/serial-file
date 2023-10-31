import serial
import struct
import os
import time
from m_print import d_print, e_print, progress_bar


header_format = "<BH"
header_size = struct.calcsize(header_format)
crc_format = "<H"
crc_size = struct.calcsize(crc_format)
format_size = header_size + crc_size

# 报文枚举值
CMD_REQUEST_FILE_SIZE = 0x61  # a
CMD_REPLY_FILE_SIZE = 0x62  # b
CMD_REQUEST_DATA = 0x63  # · c
CMD_SEND_DATA = 0x64  # d

CMD_REQUEST_FILE_NAME = 0x51  # Q
CMD_REPLY_FILE_NAME = 0x52  # R


# 指令枚举值,实际没有什么用，占位，方便函数统一处理
VAL_REQUEST_FILE = 0xAA

# 文件名长度
MAX_FILE_NAME_LENGTH = 128


def calc_checksum(arr_data):
    """
    校验和计算
    :param arr_data: bytes
    :return: 2字节，校验和值
    """
    checksum = 0
    for byte in arr_data:
        checksum += byte
    return checksum & 0xFFFF

def make_pack(cmd, data: bytes):
    """
    打包数据为二进制流
    :param cmd: cmd
    :param data: bytes data
    :return: 二进制流
    """
    if data is None:
        e_print("data is None, no crc")
        return None

    crc = calc_checksum(data)

    data_len = len(data)
    packed_data = struct.pack(header_format, cmd, data_len) + data + struct.pack(crc_format, crc)

    return packed_data


def unpack_data(packed_data):
    """
    解包二进制流为原始数据
    :param packed_data: 二进制流
    :return: cmd, data_len, data, crc
    """
    # d_print(packed_data)
    # 数据长度不足一帧
    if len(packed_data) < 6:
        d_print('data length less：', len(packed_data))
        return None

    # 解析数据头    
    header = packed_data[:header_size]
    # d_print(header)
    cmd, data_len = struct.unpack(header_format, header)

    # 解析数据
    real_data_size = len(packed_data) - header_size - 2
    if data_len != real_data_size:
        e_print(f'data length error：data_len={data_len},real_data_len={real_data_size}')
        return None

    data_start = header_size
    data_end = data_start + data_len
    data = packed_data[data_start:data_end]

    # 解析crc
    crc_start = data_end
    crc = struct.unpack(crc_format, packed_data[crc_start:crc_start + crc_size])[0]
    cal_crc = calc_checksum(data)
    if crc != cal_crc:
        e_print('crc error,recv_crc:{},cal_crc:{}'.format(hex(crc), hex(cal_crc)))
        return None

    return cmd, data_len, data, crc


def read_frame(port: serial.Serial, size) -> None:
    """
    按字节数读取一帧
    :param port: 串口号
    :param size: 数据个数
    :return: cmd,data
    """
    read_data = port.read(size)
    if len(read_data) == 0:
        return None, None

    un_data = unpack_data(read_data)
    if un_data is None:
        return None, None

    return un_data[0], un_data[2]


