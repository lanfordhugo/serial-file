import threading
import time
import sys
from pathlib import Path

# 动态添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

import serial
import serial.tools.list_ports

# --- 真实串口配置 ---
# 使用真实串口 COM5 和 COM7
SENDER_PORT = "COM5"    # 发送端串口
RECEIVER_PORT = "COM7"  # 接收端串口


def check_ports_available():
    """检查指定串口是否可用"""
    available_ports = [port.device for port in serial.tools.list_ports.comports()]
    print(f"系统可用串口: {available_ports}")
    
    missing_ports = []
    if SENDER_PORT not in available_ports:
        missing_ports.append(SENDER_PORT)
    if RECEIVER_PORT not in available_ports:
        missing_ports.append(RECEIVER_PORT)
    
    if missing_ports:
        print(f"❌ 以下串口不可用: {missing_ports}")
        print("请确保:")
        print(f"1. {SENDER_PORT} 和 {RECEIVER_PORT} 串口设备已连接")
        print("2. 串口驱动已正确安装")
        print("3. 串口未被其他程序占用")
        return False
    
    print(f"✅ 串口检查通过: {SENDER_PORT}, {RECEIVER_PORT}")
    return True


# --- 导入项目模块 ---
from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.transfer.receiver import FileReceiver
from serial_file_transfer.config.settings import SerialConfig, TransferConfig

# --- 准备测试文件 ---
def create_test_files():
    """创建不同大小的测试文件"""
    test_files = {}
    
    # 创建100KB测试文件
    file_100k = Path("test_files/test_100k.txt")
    file_100k.parent.mkdir(parents=True, exist_ok=True)
    content_100k = "这是100KB测试文件的内容。" * 35  # 约100KB
    file_100k.write_text(content_100k, encoding="utf-8")
    test_files["100K"] = {
        "path": file_100k,
        "size": file_100k.stat().st_size,
        "desc": "100KB文件"
    }
    
    # 创建1MB测试文件
    file_1m = Path("test_files/test_1m.txt")
    content_1m = "这是1MB测试文件的内容，包含更多数据用于传输测试。" * 3500  # 约1MB
    file_1m.write_text(content_1m, encoding="utf-8")
    test_files["1M"] = {
        "path": file_1m,
        "size": file_1m.stat().st_size,
        "desc": "1MB文件"
    }
    
    return test_files

# 创建测试文件
TEST_FILES = create_test_files()
RECEIVED_DIR = Path("received_files")
RECEIVED_DIR.mkdir(parents=True, exist_ok=True)

# 测试配置 - 针对真实串口和大文件优化
BAUDRATES = [115200, 230400]  # 提高波特率以处理大文件
TEST_CONFIGS = [
    {"max_data_length": 4096, "desc": "中等块大小(4KB)"},
    {"max_data_length": 8192, "desc": "大块大小(8KB)"},
]

# 测试组合：文件大小 x 波特率 x 块大小
FILE_SIZES = ["100K", "1M"]


def receiver_task(
    baudrate: int, transfer_config: TransferConfig, results: dict, test_id: str, 
    file_info: dict, file_size_key: str
):
    """接收器任务"""
    try:
        # 使用真实串口COM7作为接收端，增加超时时间
        serial_cfg_receiver = SerialConfig(port=RECEIVER_PORT, baudrate=baudrate, timeout=1.0)
        
        # 设置接收文件路径
        received_file = RECEIVED_DIR / f"received_{file_size_key}_{test_id}.txt"
        
        with SerialManager(serial_cfg_receiver) as sm:
            receiver = FileReceiver(sm, save_path=received_file, config=transfer_config)
            results[f"{test_id}_receiver"] = receiver.start_transfer()
            results[f"{test_id}_received_file"] = received_file
    except Exception as e:
        results[f"{test_id}_receiver"] = e


def sender_task(
    baudrate: int, transfer_config: TransferConfig, results: dict, test_id: str,
    file_info: dict
):
    """发送器任务"""
    try:
        # 确保接收端先启动
        time.sleep(1.0)  # 增加等待时间，确保真实串口连接稳定
        # 使用真实串口COM5作为发送端，增加超时时间
        serial_cfg_sender = SerialConfig(port=SENDER_PORT, baudrate=baudrate, timeout=1.0)
        with SerialManager(serial_cfg_sender) as sm:
            sender = FileSender(sm, file_path=file_info["path"], config=transfer_config)
            results[f"{test_id}_sender"] = sender.start_transfer()
    except Exception as e:
        results[f"{test_id}_sender"] = e


def run_single_test(baudrate: int, config_info: dict, file_size_key: str, test_id: str) -> bool:
    """运行单个测试"""
    file_info = TEST_FILES[file_size_key]
    file_size_mb = file_info["size"] / (1024 * 1024)
    
    print(f"\n{'='*70}")
    print(f"测试 {test_id}: {file_info['desc']} ({file_size_mb:.2f}MB)")
    print(f"波特率: {baudrate}, {config_info['desc']}")
    print(f"{'='*70}")

    # 创建传输配置 - 启用进度显示
    transfer_config = TransferConfig(
        max_data_length=config_info["max_data_length"], 
        show_progress=True  # 启用进度显示
    )

    results = {}

    # 启动接收和发送线程
    t_recv = threading.Thread(
        target=receiver_task,
        args=(baudrate, transfer_config, results, test_id, file_info, file_size_key),
        name=f"ReceiverThread-{test_id}",
    )
    t_send = threading.Thread(
        target=sender_task,
        args=(baudrate, transfer_config, results, test_id, file_info),
        name=f"SenderThread-{test_id}",
    )

    t_recv.start()
    t_send.start()

    t_recv.join()
    t_send.join()

    print(f"\n传输结果: {results}")

    # 检查传输结果
    sender_success = results.get(f"{test_id}_sender", False)
    receiver_success = results.get(f"{test_id}_receiver", False)
    received_file = results.get(f"{test_id}_received_file")

    if sender_success and receiver_success and received_file:
        # 文件内容校验
        if received_file.exists():
            original_content = file_info["path"].read_bytes()
            received_content = received_file.read_bytes()
            content_match = original_content == received_content
            received_size_mb = received_file.stat().st_size / (1024 * 1024)
            print(f"✅ 完整性校验: {content_match}")
            print(f"📏 文件大小: 原始 {file_size_mb:.2f}MB → 接收 {received_size_mb:.2f}MB")
            return content_match
        else:
            print("❌ 接收文件不存在")
            return False
    else:
        print("❌ 传输失败，详见 results")
        return False


if __name__ == "__main__":
    print("=== 串口文件传输集成测试 - 真实串口大文件测试 ===")
    print(f"发送端串口: {SENDER_PORT}")
    print(f"接收端串口: {RECEIVER_PORT}")
    
    # 显示测试文件信息
    print(f"\n📁 测试文件信息:")
    for key, file_info in TEST_FILES.items():
        size_mb = file_info["size"] / (1024 * 1024)
        print(f"  {key}: {file_info['desc']} ({size_mb:.2f}MB) - {file_info['path']}")
    
    # 检查串口可用性
    if not check_ports_available():
        print("❌ 串口检查失败，无法进行测试")
        sys.exit(1)
    
    print(f"\n🔧 测试配置:")
    print(f"  波特率: {BAUDRATES}")
    print(f"  数据块大小: {[cfg['desc'] for cfg in TEST_CONFIGS]}")
    print(f"  文件大小: {FILE_SIZES}")
    total_tests = len(BAUDRATES) * len(TEST_CONFIGS) * len(FILE_SIZES)
    print(f"  总测试数: {total_tests}")
    
    print("\n⚠️  注意事项:")
    print("1. 请确保COM5和COM7已正确连接（使用串口线或USB转串口）")
    print("2. 如果使用USB转串口，请确保两个设备之间的TX-RX正确交叉连接")
    print("3. 测试期间请勿断开串口连接")
    print("4. 大文件传输会显示实时进度")
    
    input("\n按回车键开始测试...")

    all_tests_passed = True
    test_results = []

    # 循环测试不同波特率和配置组合
    for i, baudrate in enumerate(BAUDRATES):
        for j, config_info in enumerate(TEST_CONFIGS):
            for k, file_size_key in enumerate(FILE_SIZES):
                test_id = f"T{i+1}.{j+1}.{k+1}"
                success = run_single_test(baudrate, config_info, file_size_key, test_id)
                test_results.append(
                    {
                        "test_id": test_id,
                        "baudrate": baudrate,
                        "config": config_info["desc"],
                        "file_size": file_size_key,
                        "success": success,
                    }
                )
                all_tests_passed = all_tests_passed and success

                # 测试间隔，让真实串口完全释放和重新初始化
                if i < len(BAUDRATES) - 1 or j < len(TEST_CONFIGS) - 1 or k < len(FILE_SIZES) - 1:
                    print(f"等待串口释放...")
                    time.sleep(2.0)

    # 输出总结
    print(f"\n{'='*60}")
    print("测试总结:")
    print(f"{'='*60}")
    for result in test_results:
        status = "✅ 通过" if result["success"] else "❌ 失败"
        print(
            f"{result['test_id']}: 波特率{result['baudrate']}, {result['config']}, 文件大小: {result['file_size']} - {status}"
        )

    print(f"{'='*60}")
    if all_tests_passed:
        print("🎉 所有测试通过！真实串口文件传输验证成功！")
        print(f"串口 {SENDER_PORT} ↔ {RECEIVER_PORT} 通信正常")
        sys.exit(0)
    else:
        print("❌ 部分测试失败，请检查:")
        print("1. 串口连接是否正常")
        print("2. 波特率设置是否支持")
        print("3. 串口驱动是否正确")
        sys.exit(1)
