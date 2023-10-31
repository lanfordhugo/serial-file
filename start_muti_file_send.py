from serial.tools import list_ports
import serial
from file_manager import SenderFileManager
from sender import Sender

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

        
com = input('填写串口号，按回车键继续:\n')
file_path= input('填写需要发送的文件夹路径，按回车键继续:\n')
# com = 'com15'
# file_path = './'


# 设置串口参数  1843200,2188800,2649600
send_port = serial.Serial(
    port=com,  # 串口号
    baudrate=1728000,  # 波特率
    bytesize=serial.EIGHTBITS,  # 数据位
    parity=serial.PARITY_NONE,  # 校验位
    stopbits=serial.STOPBITS_ONE,  # 停止位
    timeout=0.5
)

sender = Sender(send_port)
file_sender = SenderFileManager(file_path, sender)
file_sender.start_send()

input('按回车键退出\n')