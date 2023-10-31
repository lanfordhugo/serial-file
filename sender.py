import serial
from serial.tools import list_ports
import os
import struct
import time
from m_print import d_print, e_print, progress_bar
from frame_handle import read_frame, make_pack
import frame_handle


class Sender:
    """处理发送单个文件的逻辑
    """

    def __init__(self, serial_port: serial.Serial, file_path=None):
        self.serial_port = serial_port
        
        self.send_size = 0  # 已发送的数据大小
        self.send_state = 0

        if file_path is not None:
            self.file_size = os.path.getsize(file_path)  # 文件总大小
            with open(file_path, 'rb') as file:
                self.file_data = file.read()
            
    def init_params(self, file_path):
        self.send_size = 0
        self.send_state = 0
        self.file_size = os.path.getsize(file_path)
        
        with open(file_path, 'rb') as file:
            self.file_data = file.read()

    def get_file_data(self, addr, length):
        # 根据地址和长度获取文件数据
        return self.file_data[addr:addr + length]

    def wait_for_receiver_request_filesize(self):
        # 等待接收者请求文件信息
        d_print('wait for receiver request file_size')
        while True:
            cmd, data = read_frame(self.serial_port, frame_handle.format_size + 1)
            if data is None or cmd is None:
                continue
            if cmd != frame_handle.CMD_REQUEST_FILE_SIZE:
                e_print("cmd ERROR:", cmd)
                continue

            # 接收到请求文件信息的命令
            if int.from_bytes(data, byteorder='little') == frame_handle.VAL_REQUEST_FILE:
                d_print('receive request file size')
                self.send_file_size()
                break
    

    def wait_for_receiver_request_filename(self):
        # 等待接收者请求文件名信息
        start_time = time.time()
        d_print('wait for receiver request file_name')
        while True:
            # 等待计时，等待最多5分钟，5分钟超过退出
            if time.time() - start_time > 300:
                e_print("wait for receiver request timeout:300")
                return False

            cmd, data = read_frame(self.serial_port, frame_handle.format_size + 1)
            if data is None or cmd is None:
                continue
            if cmd != frame_handle.CMD_REQUEST_FILE_NAME:
                e_print("cmd ERROR:", hex(cmd))
                continue

            # 接收到请求文件信息的命令
            d_print('receive request file name')
            return True
        
    def send_file_name(self, file_name):
        # 向接收端回复文件名
        b_file_name = file_name.encode('utf-8')
        # 不足最大文件名长度的补0
        b_file_name += b'\x00' * (frame_handle.MAX_FILE_NAME_LENGTH - len(b_file_name))
        packed_data = make_pack(frame_handle.CMD_REPLY_FILE_NAME, b_file_name)
        # d_print('file_bytes:', packed_data)
        # d_print('file_name:', file_name)
        self.serial_port.write(packed_data)
    
    def send_file_size(self):
        # 将文件大小发送给接收者
        b_file_size = struct.pack('<I', self.file_size)
        d_print(f'file size:{(self.file_size / 1024):.2f}kb')
        packed_data = make_pack(frame_handle.CMD_REPLY_FILE_SIZE, b_file_size)
        # d_print('file_bytes:', packed_data)
        self.serial_port.write(packed_data)

    def send_data_package(self, addr, length):
        # 根据接收者的请求，发送一个数据包给接收者
        send_data = self.get_file_data(addr, length)
        packed_data = make_pack(frame_handle.CMD_SEND_DATA, send_data)
        self.serial_port.write(packed_data)

    def wait_request_file_data(self):
        # 等待接收者请求数据
        while True:
            cmd, data = read_frame(self.serial_port, frame_handle.format_size + 4 + 2)  # 4个字节的地址，2个字节的长度
            if data is None or cmd is None:
                continue
            if cmd != frame_handle.CMD_REQUEST_DATA:
                d_print("cmd ERROR:", cmd)
                continue

            # 接收到请求数据的命令
            addr, length = struct.unpack('<IH', data)

            # 检查数据有效性
            if addr + length > self.file_size:
                if addr > self.file_size:
                    e_print(f'addr error, addr:{addr}, file_size:{self.file_size}')
                    break
                else:
                    e_print(f'addr + length > file_size:{addr + length}>{self.file_size}')
                    length = self.file_size - addr

            self.send_data_package(addr, length)
            self.send_size = addr + length
            break

    def start_file_sending(self):
        """开始发送单个文件
        """
        self.wait_for_receiver_request_filesize()
        start_time = time.time()
        while True:
            # 接收接收者的请求
            self.wait_request_file_data()
            end_time = time.time()
            send_rate = self.send_size / (end_time - start_time) / 1024

            # 显示进度条
            progress = self.send_size / self.file_size * 100  # 计算进度百分比
            progress_bar(progress, send_rate)

            if self.file_size == self.send_size:
                print()
                d_print('send file success')
                # self.serial_port.close()
                break

        d_print(f'send time:{(end_time - start_time):.2f}s')
        # if 接收到结束文件传输:
