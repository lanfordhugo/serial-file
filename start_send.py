from serial.tools import list_ports
import serial
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
file_path = input('填写需要发送的文件路径，按回车键继续:\n')

# com = 'com15'
# file_path = './test.txt'


# 设置串口参数
send_port = serial.Serial(
    port=com,  # 串口号
    baudrate=1728000,  # 波特率
    bytesize=serial.EIGHTBITS,  # 数据位
    parity=serial.PARITY_NONE,  # 校验位
    stopbits=serial.STOPBITS_ONE,  # 停止位
    timeout=0.5
)



# 检查文件是否存在
try:
    f = open(file_path, 'rb')
    f.close()
except FileNotFoundError:
    print('文件不存在，请检查文件路径是否正确')
    exit()

sender = Sender(send_port, file_path)
sender.start_file_sending()

input('按回车键退出\n')