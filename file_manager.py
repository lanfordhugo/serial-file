import os
from m_print import e_print, d_print
import time
from frame_handle import read_frame, make_pack
import frame_handle
from sender import Sender
from recver import Receiver


class SenderFileManager:
    """管理批量文件发送
    """

    def __init__(self, folder_path, sender: Sender):
        self.folder_path = folder_path
        self.sender = sender
        self.file_list = []
        self.scan_files()

    def scan_files(self):
    # 扫描文件夹下的所有文件，并将文件名保存到列表中
        for file_name in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, file_name)
            if os.path.isfile(file_path):
                self.file_list.append(file_name)


        # 在列表最后添加一个空文件名，表示发送完毕
        self.file_list.append("")
        d_print(f"file_list: {self.file_list}")

    def get_next_file(self):
        # 返回下一个文件名
        if self.file_list:
            return self.file_list.pop(0)
        else:
            return None

    def send_file(self, file_name):
        # 发送文件内容
        file_path = os.path.join(self.folder_path, file_name)
        # 发送文件内容的具体操作，如通过网络传输发送

    def start_send(self):
        # 开始发送文件
        while True:
            # 从文件管理器中获取下一个文件名,然后等待接收端请求文件名
            file_name = self.get_next_file()
            d_print(f"ready send file name: [{file_name}]")
            if self.sender.wait_for_receiver_request_filename():
                self.sender.send_file_name(file_name)
                
                # 文件名问空，表示发送完毕
                if file_name == '':
                    d_print("send all file done")
                    break

                # 回复完文件名后，等待接收端请求文件内容
                file_path = os.path.join(self.folder_path, file_name)
                self.sender.init_params(file_path)
                self.sender.start_file_sending()
            else:
                e_print("wait for receiver request timeout:300s")
                break


class ReceiverFileManager:
    """管理批量文件接收
    """

    def __init__(self, folder_path, receiver: Receiver):
        self.receiver = receiver
        self.folder_path = folder_path
        self.create_folder()

    def create_folder(self):
        # 创建接收文件夹
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)

    def create_file(self, file_name):
        # 根据文件名创建文件
        file_path = os.path.join(self.folder_path, file_name)
        with open(file_path, "wb") as f:
            pass  # 可以写入一些初始化内容，如文件头信息等

    def receive_file(self, file_name):
        # 接收文件内容并保存
        file_path = os.path.join(self.folder_path, file_name)
        # 接收文件内容的具体操作，如通过网络传输接收

    def start_receive(self):
        # 开始接收文件
        start_time = time.time()
        while True:
            # 请求文件名并接收
            self.receiver.send_file_name_request()
            time.sleep(0.1)  # 等待发送端回复文件名
            file_name = self.receiver.receive_file_name()
            if file_name is not None:
                if file_name == '':
                    # 文件名为空，表示发送完毕
                    d_print("receive all file done")
                    break
                else:
                    # 接收文件内容
                    recv_path = os.path.join(self.folder_path, file_name)
                    self.receiver.init_params(recv_path)
                    self.receiver.start_receiving()
            else:
                # time.sleep(5)
                end_time = time.time()
                if end_time - start_time > 300:
                    e_print("request file name timeout:300s")
                    break
                else:
                    continue


if __name__ == '__main__':
    import serial

    # 设置串口参数
    send_port = serial.Serial(
        port='com17',  # 串口号
        baudrate=115200,  # 波特率
        bytesize=serial.EIGHTBITS,  # 数据位
        parity=serial.PARITY_NONE,  # 校验位
        stopbits=serial.STOPBITS_ONE,  # 停止位
        timeout=0.1
    )

    # 示例用法
    # folder_path = "./"
    # sender = Sender(send_port)
    # sender_file_manager = SenderFileManager(folder_path, sender)
    # sender_file_manager.start_send()

    recv_path = "./recv/"
    receiver = Receiver(send_port)
    receiver_file_manager = ReceiverFileManager(recv_path, receiver)
    receiver_file_manager.start_receive()
