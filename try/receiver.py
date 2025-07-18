import serial
from ymodem.Socket import ModemSocket
import time
import os


def create_serial_port(port, baudrate, timeout=1):
    """
    创建并配置串口对象。
    """
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        print(f"成功打开串口: {port} @ {baudrate} bps")
        return ser
    except serial.SerialException as e:
        print(f"错误: 无法打开串口 {port} - {e}")
        return None


def main():
    # 固定配置参数
    PORT = "COM7"  # 接收端使用COM7
    BAUDRATE = 1728000  # 使用172800波特率
    DEST_DIR = "./received_files"  # 接收文件保存目录

    print(f"YMODEM文件接收器 - 固定配置")
    print(f"串口: {PORT}")
    print(f"波特率: {BAUDRATE}")
    print(f"保存目录: {DEST_DIR}")
    print("-" * 50)

    # 确保目标目录存在
    if not os.path.isdir(DEST_DIR):
        try:
            os.makedirs(DEST_DIR)
            print(f"创建目标目录: {DEST_DIR}")
        except OSError as e:
            print(f"错误: 无法创建目标目录 {DEST_DIR} - {e}")
            return

    ser = create_serial_port(PORT, BAUDRATE)
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

    print(f"准备在 {PORT} 监听文件接收...")
    try:
        start_time = time.time()
        # 记录上次回调的时间和字节数，用于速率计算
        last = {'time': start_time, 'bytes': 0}
        def progress_callback(task_index, filename, total_bytes, received_bytes):
            now = time.time()
            elapsed = now - last['time']
            delta_bytes = received_bytes - last['bytes']
            speed = (delta_bytes / 1024 / 1024) / elapsed if elapsed > 0 else 0
            print(
                f"\r接收中: {filename} - "
                f"({received_bytes / (1024**2):.2f} MB / {total_bytes / (1024**2):.2f} MB) "
                f"速率: {speed:.2f} MB/s",
                end="",
            )
            last['time'] = now
            last['bytes'] = received_bytes

        received_filenames = modem.recv(
            DEST_DIR,
            callback=progress_callback,
        )
        end_time = time.time()

        # 类型安全处理返回值
        if isinstance(received_filenames, list) and received_filenames:
            received_file_path = os.path.join(DEST_DIR, received_filenames[0])
            file_size_bytes = os.path.getsize(received_file_path)

            transfer_time = end_time - start_time
            transfer_speed = (
                (file_size_bytes / (1024 * 1024)) / transfer_time
                if transfer_time > 0
                else 0
            )
            print(
                f"\n文件 {received_filenames[0]} 接收成功！ 耗时: {transfer_time:.2f} 秒, 传输速度: {transfer_speed:.2f} MB/s"
            )
        elif received_filenames is True:
            print("\n文件接收成功！（未返回文件名）")
        else:
            print("\n文件接收失败。")
    except Exception as e:
        print(f"接收过程中发生错误: {e}")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("串口已关闭。")


if __name__ == "__main__":
    main()
