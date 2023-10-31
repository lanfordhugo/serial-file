from serial.tools import list_ports
import serial
from recver import Receiver

file_path = None
# 获取所有可用的串口

# 获取可用的串口号
available_ports = list(list_ports.comports())

print("可用的串口：")
if len(available_ports) == 0:
    print("没有找到可用的串口。")
else:
    for port in available_ports:
        print(port.device)

# 保存路径和com口
com = input('填写串口号，按回车键继续:\n')
save_path = input('填写需要保存的文件路径(带文件名)，按回车键继续:\n')
# com = 'com16'
# save_path = './recv_temp/recv.txt'


# 可用的 波特率 115200、230400、460800、921600,1728000
recv_port = serial.Serial(
    port=com,  # 串口号
    baudrate=1728000,  # 波特率
    bytesize=serial.EIGHTBITS,  # 数据位
    parity=serial.PARITY_NONE,  # 校验位
    stopbits=serial.STOPBITS_ONE,  # 停止位
    timeout=0.05
)

# 单次传输的最大数据长度
MAX_DATA_LENGTH = 1024 * 10

recver = Receiver(recv_port, save_path, MAX_DATA_LENGTH)
recver.start_receiving()

input('按回车键退出\n')