"""
探测协商功能测试
==============

测试智能探测协商管理器的能力协商和波特率切换功能。
"""

import pytest
from unittest.mock import Mock, patch
from src.serial_file_transfer.core.probe_manager import ProbeManager
from src.serial_file_transfer.core.serial_manager import SerialManager
from src.serial_file_transfer.core.probe_structures import (
    CapabilityNegoData,
    CapabilityAckData,
    SwitchBaudrateData,
    SwitchAckData
)
from src.serial_file_transfer.config.constants import ProbeCommand


class TestProbeCapability:
    """测试探测协商能力功能"""
    
    @pytest.fixture
    def mock_serial_manager(self):
        """创建模拟串口管理器"""
        mock_manager = Mock(spec=SerialManager)
        mock_manager.write.return_value = True
        mock_manager.read.return_value = b''
        return mock_manager
    
    @pytest.fixture
    def probe_manager(self, mock_serial_manager):
        """创建探测管理器实例"""
        return ProbeManager(mock_serial_manager)
    
    def test_negotiate_capability_success(self, probe_manager):
        """测试成功的能力协商"""
        # 设置支持的波特率
        supported_baudrates = [115200, 921600, 1728000]
        
        # 模拟ACK响应
        test_session_id = 0x12345678
        ack_data = CapabilityAckData(test_session_id, 1)  # 接受
        
        with patch.object(probe_manager, '_send_probe_frame') as mock_send:
            with patch.object(probe_manager, '_receive_probe_frame') as mock_receive:
                with patch.object(probe_manager, '_generate_session_id', return_value=test_session_id):
                    mock_send.return_value = True
                    mock_receive.return_value = ack_data.pack()
                    
                    result = probe_manager.negotiate_capability(
                        file_count=3,
                        total_size=1024*1024,
                        supported_baudrates=supported_baudrates
                    )
                    
                    # 验证结果
                    assert result == 1728000  # 最高波特率
                    assert probe_manager.session_id == test_session_id
                    assert probe_manager.target_baudrate == 1728000
                    
                    # 验证调用
                    mock_send.assert_called_once()
                    mock_receive.assert_called_once()
    
    def test_negotiate_capability_no_common_baudrate(self, probe_manager):
        """测试没有公共波特率的情况"""
        # 不支持的波特率
        supported_baudrates = [9600, 19200]
        
        result = probe_manager.negotiate_capability(
            file_count=1,
            total_size=1024,
            supported_baudrates=supported_baudrates
        )
        
        assert result is None
    
    def test_negotiate_capability_rejected(self, probe_manager):
        """测试能力协商被拒绝"""
        supported_baudrates = [115200, 921600]
        test_session_id = 0x12345678
        
        # 模拟拒绝响应
        ack_data = CapabilityAckData(test_session_id, 0)  # 拒绝
        
        with patch.object(probe_manager, '_send_probe_frame') as mock_send:
            with patch.object(probe_manager, '_receive_probe_frame') as mock_receive:
                with patch.object(probe_manager, '_generate_session_id', return_value=test_session_id):
                    mock_send.return_value = True
                    mock_receive.return_value = ack_data.pack()
                    
                    result = probe_manager.negotiate_capability(
                        file_count=1,
                        total_size=1024,
                        supported_baudrates=supported_baudrates
                    )
                    
                    assert result is None
    
    def test_negotiate_capability_timeout(self, probe_manager):
        """测试能力协商超时"""
        supported_baudrates = [115200, 921600]
        
        with patch.object(probe_manager, '_send_probe_frame') as mock_send:
            with patch.object(probe_manager, '_receive_probe_frame') as mock_receive:
                mock_send.return_value = True
                mock_receive.return_value = None  # 超时
                
                result = probe_manager.negotiate_capability(
                    file_count=1,
                    total_size=1024,
                    supported_baudrates=supported_baudrates
                )
                
                assert result is None
    
    def test_handle_capability_nego_accept(self, probe_manager):
        """测试处理能力协商 - 接受"""
        # 创建协商数据
        capability = CapabilityNegoData(
            session_id=0x12345678,
            transfer_mode=1,
            file_count=1,
            total_size=1024,
            selected_baudrate=921600
        )
        
        with patch.object(probe_manager, '_send_probe_frame') as mock_send:
            mock_send.return_value = True
            
            result = probe_manager.handle_capability_nego(capability.pack())
            
            assert result is True
            assert probe_manager.session_id == 0x12345678
            assert probe_manager.target_baudrate == 921600
            
            # 验证发送了接受确认
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == ProbeCommand.CAPABILITY_ACK
    
    def test_handle_capability_nego_reject(self, probe_manager):
        """测试处理能力协商 - 拒绝不支持的波特率"""
        # 创建不支持的波特率协商
        capability = CapabilityNegoData(
            session_id=0x12345678,
            transfer_mode=1,
            file_count=1,
            total_size=1024,
            selected_baudrate=9600  # 不支持的波特率
        )
        
        with patch.object(probe_manager, '_send_probe_frame') as mock_send:
            mock_send.return_value = True
            
            result = probe_manager.handle_capability_nego(capability.pack())
            
            assert result is False
            # 验证发送了拒绝确认
            mock_send.assert_called_once()
    
    def test_handle_capability_nego_invalid_data(self, probe_manager):
        """测试处理无效的协商数据"""
        invalid_data = b'\x01\x02\x03'
        
        result = probe_manager.handle_capability_nego(invalid_data)
        assert result is False
    
    def test_switch_baudrate_success(self, probe_manager):
        """测试成功的波特率切换"""
        # 设置会话信息
        probe_manager.session_id = 0x12345678
        probe_manager.target_baudrate = 921600
        
        # 模拟切换ACK
        ack_data = SwitchAckData(0x12345678)
        
        with patch.object(probe_manager, '_send_probe_frame') as mock_send:
            with patch.object(probe_manager, '_receive_probe_frame') as mock_receive:
                with patch.object(probe_manager, '_execute_baudrate_switch') as mock_execute:
                    mock_send.return_value = True
                    mock_receive.return_value = ack_data.pack()
                    mock_execute.return_value = True
                    
                    result = probe_manager.switch_baudrate()
                    
                    assert result is True
                    mock_send.assert_called_once()
                    mock_receive.assert_called_once()
                    mock_execute.assert_called_once_with(921600, 100)
    
    def test_switch_baudrate_no_session(self, probe_manager):
        """测试没有会话信息时的波特率切换"""
        # 不设置会话信息
        result = probe_manager.switch_baudrate()
        assert result is False
    
    def test_switch_baudrate_timeout(self, probe_manager):
        """测试波特率切换超时"""
        probe_manager.session_id = 0x12345678
        probe_manager.target_baudrate = 921600
        
        with patch.object(probe_manager, '_send_probe_frame') as mock_send:
            with patch.object(probe_manager, '_receive_probe_frame') as mock_receive:
                mock_send.return_value = True
                mock_receive.return_value = None  # 超时
                
                result = probe_manager.switch_baudrate()
                assert result is False
    
    def test_handle_baudrate_switch_success(self, probe_manager):
        """测试处理波特率切换指令"""
        # 设置会话信息
        probe_manager.session_id = 0x12345678
        probe_manager.target_baudrate = 921600
        
        # 创建切换数据
        switch_data = SwitchBaudrateData(
            session_id=0x12345678,
            new_baudrate=921600,
            switch_delay_ms=100
        )
        
        with patch.object(probe_manager, '_send_probe_frame') as mock_send:
            with patch.object(probe_manager, '_execute_baudrate_switch') as mock_execute:
                mock_send.return_value = True
                mock_execute.return_value = True
                
                result = probe_manager.handle_baudrate_switch(switch_data.pack())
                
                assert result is True
                mock_send.assert_called_once()
                mock_execute.assert_called_once_with(921600, 100)
    
    def test_handle_baudrate_switch_session_mismatch(self, probe_manager):
        """测试处理波特率切换 - 会话ID不匹配"""
        probe_manager.session_id = 0x12345678
        probe_manager.target_baudrate = 921600
        
        # 创建不匹配的切换数据
        switch_data = SwitchBaudrateData(
            session_id=0x87654321,  # 不匹配的会话ID
            new_baudrate=921600,
            switch_delay_ms=100
        )
        
        result = probe_manager.handle_baudrate_switch(switch_data.pack())
        assert result is False
    
    def test_handle_baudrate_switch_baudrate_mismatch(self, probe_manager):
        """测试处理波特率切换 - 波特率不匹配"""
        probe_manager.session_id = 0x12345678
        probe_manager.target_baudrate = 921600
        
        # 创建不匹配的切换数据
        switch_data = SwitchBaudrateData(
            session_id=0x12345678,
            new_baudrate=115200,  # 不匹配的波特率
            switch_delay_ms=100
        )
        
        result = probe_manager.handle_baudrate_switch(switch_data.pack())
        assert result is False
    
    def test_execute_baudrate_switch(self, probe_manager):
        """测试执行波特率切换"""
        with patch('time.sleep') as mock_sleep:
            result = probe_manager._execute_baudrate_switch(921600, 100)
            
            # 由于SerialManager没有switch_baudrate方法，会返回True
            assert result is True
            mock_sleep.assert_called_once_with(0.1)  # 100ms = 0.1s 