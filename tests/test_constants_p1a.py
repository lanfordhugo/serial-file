"""
P1-A 块大小协商功能测试
=====================

测试动态块大小计算和协商函数。
"""

import pytest
from src.serial_file_transfer.config.constants import (
    calculate_recommended_chunk_size,
    negotiate_chunk_size,
    MIN_CHUNK_SIZE,
    MAX_CHUNK_SIZE,
    BAUDRATE_CHUNK_SIZE_MAP,
)


class TestP1AChunkSizeCalculation:
    """测试P1-A块大小计算函数"""

    def test_calculate_recommended_chunk_size_exact_match(self):
        """测试精确匹配的波特率"""
        for baudrate, expected_size in BAUDRATE_CHUNK_SIZE_MAP.items():
            result = calculate_recommended_chunk_size(baudrate)
            assert (
                result == expected_size
            ), f"波特率{baudrate}的推荐块大小应为{expected_size}, 实际为{result}"

    def test_calculate_recommended_chunk_size_higher_baudrate(self):
        """测试高于映射表中最高波特率的情况"""
        # 测试超高波特率，应该使用最大值
        # 注意：3000000已在映射表中，所以直接返回映射值8192
        result = calculate_recommended_chunk_size(3000000)  # 3Mbps
        expected = 8192  # 直接从映射表获取
        assert result == expected

        # 测试真正超出映射表的波特率
        result = calculate_recommended_chunk_size(7000000)  # 7Mbps，超出映射表
        # 最接近的是6000000(8192)，由于7000000更高，所以翻倍但不超过最大值
        expected = min(8192 * 2, MAX_CHUNK_SIZE)  # min(16384, 16384) = 16384
        assert result == expected

    def test_calculate_recommended_chunk_size_intermediate_baudrate(self):
        """测试介于两个映射值之间的波特率"""
        # 测试 500000 bps，最接近的是460800，但500000更高，所以会翻倍
        result = calculate_recommended_chunk_size(500000)
        expected = min(
            BAUDRATE_CHUNK_SIZE_MAP[460800] * 2, MAX_CHUNK_SIZE
        )  # 1024 * 2 = 2048
        assert result == expected

        # 测试 400000 bps，最接近的是460800，但400000更低，所以使用原值
        result = calculate_recommended_chunk_size(400000)
        assert result == BAUDRATE_CHUNK_SIZE_MAP[460800]  # 1024

        # 测试 1000000 bps，已在映射表中
        result = calculate_recommended_chunk_size(1000000)
        assert result == BAUDRATE_CHUNK_SIZE_MAP[1000000]

    def test_calculate_recommended_chunk_size_boundaries(self):
        """测试边界值"""
        # 测试最低波特率
        result = calculate_recommended_chunk_size(9600)
        assert result >= MIN_CHUNK_SIZE

        # 测试极高波特率
        result = calculate_recommended_chunk_size(10000000)  # 10Mbps
        assert result <= MAX_CHUNK_SIZE

    def test_negotiate_chunk_size_normal_cases(self):
        """测试正常的块大小协商"""
        # 发送端推荐值小于接收端最大值
        result = negotiate_chunk_size(1024, 2048)
        assert result == 1024

        # 发送端推荐值大于接收端最大值
        result = negotiate_chunk_size(2048, 1024)
        assert result == 1024

        # 发送端推荐值等于接收端最大值
        result = negotiate_chunk_size(1024, 1024)
        assert result == 1024

    def test_negotiate_chunk_size_boundaries(self):
        """测试协商边界情况"""
        # 协商结果不能小于最小值
        result = negotiate_chunk_size(100, 200)  # 都小于MIN_CHUNK_SIZE
        assert result == MIN_CHUNK_SIZE

        # 协商结果不能大于最大值
        result = negotiate_chunk_size(20000, 30000)  # 都大于MAX_CHUNK_SIZE
        assert result == MAX_CHUNK_SIZE

        # 一个值在范围内，一个值超出范围
        result = negotiate_chunk_size(MAX_CHUNK_SIZE + 1000, 1024)
        assert result == 1024

    @pytest.mark.parametrize(
        "sender_rec,receiver_max,expected",
        [
            (512, 1024, 512),  # 正常情况：发送端小
            (2048, 1024, 1024),  # 正常情况：接收端小
            (1024, 1024, 1024),  # 相等情况
            (100, 200, 512),  # 都太小，取最小值
            (20000, 30000, 16384),  # 都太大，取最大值
            (512, 20000, 512),  # 发送端正常，接收端太大
            (20000, 1024, 1024),  # 发送端太大，接收端正常
        ],
    )
    def test_negotiate_chunk_size_parametrized(
        self, sender_rec, receiver_max, expected
    ):
        """参数化测试块大小协商"""
        result = negotiate_chunk_size(sender_rec, receiver_max)
        assert result == expected

    def test_calculate_recommended_chunk_size_specific_rates(self):
        """测试特定波特率的推荐块大小"""
        # 测试TODO文档中提到的特定波特率
        assert calculate_recommended_chunk_size(460800) == 1024  # 460800bps→1K
        assert calculate_recommended_chunk_size(1728000) == 8192  # 1728000bps→8K

        # 测试一些常见波特率
        assert calculate_recommended_chunk_size(115200) == 1024
        assert calculate_recommended_chunk_size(921600) == 2048


class TestP1AIntegration:
    """测试P1-A功能集成"""

    def test_baudrate_to_chunk_size_workflow(self):
        """测试从波特率到块大小的完整工作流"""
        # 模拟发送端根据波特率计算推荐值
        baudrate = 1728000
        sender_recommended = calculate_recommended_chunk_size(baudrate)
        assert sender_recommended == 8192

        # 模拟接收端有自己的最大值限制
        receiver_max = 4096

        # 协商最终值
        final_chunk_size = negotiate_chunk_size(sender_recommended, receiver_max)
        assert final_chunk_size == 4096  # 取较小值

        # 验证最终值在有效范围内
        assert MIN_CHUNK_SIZE <= final_chunk_size <= MAX_CHUNK_SIZE


# 如果直接运行这个文件，执行所有测试
if __name__ == "__main__":
    pytest.main([__file__])
