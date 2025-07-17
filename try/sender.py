import argparse
import serial
from ymodem.Socket import ModemSocket
import time
import os  # 导入 os 模块


def create_serial_port(port, baudrate, timeout=1):
    """
    创建并配置串口对象。
    """
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout, write_timeout=timeout)
        print(f"成功打开串口: {port} @ {baudrate} bps")
        return ser
    except serial.SerialException as e:
        print(f"错误: 无法打开串口 {port} - {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="使用 YMODEM 协议通过串口发送文件。")
    parser.add_argument(
        "-p", "--port", required=True, help="串口名称，例如 COM1 或 /dev/ttyUSB0"
    )
    parser.add_argument(
        "-b", "--baudrate", type=int, default=1728000, help="波特率 (默认: 1728000)"
    )
    parser.add_argument("-f", "--file", required=True, help="要发送的文件路径")

    args = parser.parse_args()

    ser = create_serial_port(args.port, args.baudrate)
    if not ser:
        return

    def getc(size: int, timeout: float | None = None) -> bytes | None:
        # 从串口读取指定字节数，超时为timeout秒
        return ser.read(size) or None

    def putc(data: bytes | bytearray, timeout: float | None = None) -> int:
        # 向串口写入数据，并返回写入的字节数
        result = ser.write(data)
        return result if result is not None else 0

    modem = ModemSocket(getc, putc)

    file_path = args.file
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件未找到: {file_path}")

        print(f"准备发送文件: {file_path}")
        start_time = time.time()

        # 记录上次回调的时间和字节数，用于速率计算
        last = {'time': start_time, 'bytes': 0}
        def progress_callback(task_index, filepath, total_bytes, sent_bytes):
            now = time.time()
            elapsed = now - last['time']
            delta_bytes = sent_bytes - last['bytes']
            speed = (delta_bytes / 1024 / 1024) / elapsed if elapsed > 0 else 0
            print(
                f"\r发送中: {os.path.basename(filepath)} - "
                f"({sent_bytes / (1024**2):.2f} MB / {total_bytes / (1024**2):.2f} MB) "
                f"速率: {speed:.2f} MB/s",
                end="",
            )
            last['time'] = now
            last['bytes'] = sent_bytes

        result = modem.send(
            [file_path],
            callback=progress_callback,
        )
        end_time = time.time()

        if result:
            file_size_bytes = os.path.getsize(file_path)
            transfer_time = end_time - start_time
            transfer_speed = (
                (file_size_bytes / (1024 * 1024)) / transfer_time
                if transfer_time > 0
                else 0
            )
            print(
                f"\n文件 {file_path} 发送成功！ 耗时: {transfer_time:.2f} 秒, 传输速度: {transfer_speed:.2f} MB/s"
            )
        else:
            print(f"\n文件 {file_path} 发送失败。")

    except FileNotFoundError as e:
        print(f"错误: {e}")
    except Exception as e:
        print(f"发送过程中发生错误: {e}")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("串口已关闭。")


if __name__ == "__main__":
    main()
