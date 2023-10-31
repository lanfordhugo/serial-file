import serial
import struct
import time
from frame_handle import read_frame, make_pack
from m_print import d_print, e_print, progress_bar
import frame_handle
import os



class Receiver:
    def __init__(self, serial_port: serial.Serial, recv_path=None, signle_max_length=256):

        self.recv_path = recv_path
        self.file_size = 0  # 文件总大小
        self.serial_port = serial_port
        self.signle_max_length = signle_max_length  # 单次传输的最大数据长度
        self.file_data = b''
        self.recv_size = 0
        
    def init_params(self, recv_path):
        self.recv_path = recv_path
        self.file_size = 0  # 文件总大小
        self.file_data = b''
        self.recv_size = 0
        
    def send_file_size_request(self):
        # 主动向发送者发送文件信息请求，请求获取文件大小
        request_cmd = struct.pack('<B', frame_handle.VAL_REQUEST_FILE)
        pack_data = make_pack(frame_handle.CMD_REQUEST_FILE_SIZE, request_cmd)
        # d_print('file_size_request:', pack_data)
        self.serial_port.write(pack_data)
    
    def send_file_name_request(self):
        # 主动向发送者发送文件名请求，请求获取文件名
        request_cmd = struct.pack('<B', frame_handle.VAL_REQUEST_FILE)
        pack_data = make_pack(frame_handle.CMD_REQUEST_FILE_NAME, request_cmd)
        # d_print('file_name_request:', pack_data)
        self.serial_port.write(pack_data)

    def receive_file_size(self):
        # 接收发送者返回的文件大小信息
        cmd, data = read_frame(self.serial_port, frame_handle.format_size + 4)
        if data is None or cmd is None:
            return None
        if cmd != frame_handle.CMD_REPLY_FILE_SIZE:
            e_print("cmd ERROR:", cmd)
            return None

        # 获取文件大小
        self.file_size = int.from_bytes(data, byteorder='little')
        d_print(f'file_size:{(self.file_size / 1024):.2f}kb')
    
    def receive_file_name(self):
        # 接收发送者返回的文件名信息
        cmd, data = read_frame(self.serial_port, frame_handle.format_size + frame_handle.MAX_FILE_NAME_LENGTH)
        if data is None or cmd is None:
            return None
        if cmd != frame_handle.CMD_REPLY_FILE_NAME:
            e_print("cmd ERROR:", cmd)
            return None
        # 去除文件名后面的0
        data = data.rstrip(b'\x00')
        # 获取文件名
        file_name = data.decode('utf-8')
        d_print(f'file_name:[{file_name}]')
        return file_name

    def send_data_request(self, addr, length):
        # 根据自身能力，在一定数据长度范围内定义一个周期，周期性地向发送者请求数据包
        # d_print(f'request addr:{addr}, len:{length}')
        request_data = struct.pack('<IH', addr, length)
        pack_data = make_pack(frame_handle.CMD_REQUEST_DATA, request_data)
        self.serial_port.write(pack_data)

    def receive_data_package(self):
        # 接收发送者发送的数据包和附带的CRC校验值
        while True:
            cmd, data = read_frame(self.serial_port, frame_handle.format_size + self.signle_max_length)
            if data is None or cmd is None:
                return False
            if cmd != frame_handle.CMD_SEND_DATA:
                e_print("cmd ERROR:", cmd)
                return False

            # 保存接收到数据
            self.recv_size += len(data)
            self.file_data += data
            return True

    def start_receiving(self):

        # 等待发送者发送文件信息
        while True:
            self.send_file_size_request()
            self.receive_file_size()
            if self.file_size is not None and self.file_size > 0:
                break

        # 接收文件
        start_time = time.time()
        while True:
            # 发送请求获取数据包
            if self.recv_size != self.file_size:
                remain_len = self.file_size - self.recv_size
                if remain_len > self.signle_max_length:
                    request_len = self.signle_max_length
                else:
                    request_len = remain_len
                self.send_data_request(self.recv_size, request_len)

            # 接收数据包
            recv_done = self.receive_data_package()
            if recv_done is False:  # 接收数据报失败需要重新接收
                continue

            # 显示进度条
            progress = self.recv_size / self.file_size * 100  # 计算进度百分比
            end_time = time.time()
            recv_rate = self.recv_size / (end_time - start_time) / 1024  # k/s
            progress_bar(progress, recv_rate)

            # 接收完了数据保存数据到文件
            if self.recv_size == self.file_size:
                print()
                file_name = os.path.basename(self.recv_path)

                # 保存文件,终止循环
                with open(self.recv_path, 'wb') as file:
                    file.write(self.file_data)
                    d_print(f'save [{file_name}] success! recv time:{(end_time - start_time):.2f}s')
                    break
