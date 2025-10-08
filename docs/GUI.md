# GUI 架构文档

## 架构概述

GUI 采用模块化设计，从单文件（1583行）重构为7个独立模块，实现高内聚低耦合。

### 设计原则

- **KISS**: 保持简单，不过度抽象
- **单一职责**: 每个模块职责清晰
- **组件复用**: LogPanel 等组件可复用
- **易于维护**: 文件大小可控（150-550行）

---

## 模块结构

```
src/serial_file_transfer/gui/
├── app.py                    # 主应用类 (167行)
├── theme.py                  # 主题管理 (106行)
├── mode_selection_view.py    # 模式选择 (152行)
├── send_panel.py             # 发送面板 (550行)
├── receive_panel.py          # 接收面板 (530行)
└── log_panel.py              # 可复用日志组件 (344行)

gui_main.py                   # 纯入口文件 (29行)
```

**总代码**: 约1889行（与重构前相当，但结构更清晰）

---

## 核心模块详解

### 1. app.py - 主应用类

**职责**: 应用生命周期管理、视图切换、状态管理

**核心功能**:
```python
class SerialTransferApp:
    def __init__(self, root: tk.Tk):
        # 初始化窗口、主题、日志系统
        pass
    
    def show_mode_selection(self):
        # 显示模式选择视图
        pass
    
    def show_send_panel(self):
        # 显示发送面板
        pass
    
    def show_receive_panel(self):
        # 显示接收面板
        pass
    
    def clear_current_view(self):
        # 清空当前视图
        pass
```

**关键特性**:
- ✅ 集中管理视图切换
- ✅ 维护全局配置状态
- ✅ 日志队列管理

---

### 2. theme.py - 主题管理

**职责**: 统一管理 UI 主题、颜色、样式

**核心设计**:
```python
@dataclass
class ThemeColors:
    """主题颜色配置"""
    bg_color: str = "#ffffff"
    primary_color: str = "#3b82f6"
    success_color: str = "#10b981"
    error_color: str = "#ef4444"
    # ...

class ThemeManager:
    """主题管理器"""
    def setup_ttk_styles(self):
        # 配置 TTK 样式
        pass
    
    def apply_to_root(self, root):
        # 应用主题到根窗口
        pass
```

**优势**:
- ✅ 主题配置集中
- ✅ 易于更换主题
- ✅ 样式统一管理

---

### 3. mode_selection_view.py - 模式选择视图

**职责**: 创建和管理模式选择界面

**核心设计**:
```python
class ModeSelectionView:
    def __init__(
        self, 
        parent: tk.Tk, 
        theme: ThemeManager,
        on_send_clicked: Callable,
        on_receive_clicked: Callable
    ):
        # 创建界面
        self._create_ui()
    
    def _create_ui(self):
        # 标题、按钮、版本信息
        pass
    
    def destroy(self):
        # 销毁视图
        pass
```

**界面特点**:
- 两个大按钮（发送/接收）
- 悬停效果
- 版本信息显示

---

### 4. log_panel.py - 可复用日志组件 ⭐

**职责**: 提供可复用的日志显示和控制组件

**核心设计**:
```python
class LogPanel:
    """日志面板组件（可复用）"""
    
    def __init__(
        self,
        parent: tk.Frame,
        theme: ThemeManager,
        log_queue: queue.Queue,
        on_start: callable,
        start_button_text: str = "开始传输"
    ):
        self._create_ui(start_button_text)
        self._start_log_updates()
    
    def update_progress(self, current: int, total: int):
        """更新进度"""
        pass
    
    def append_log(self, message: str, level: str = "INFO"):
        """添加日志"""
        pass
```

**组件包含**:
- 日志文本框（滚动显示）
- 进度条（百分比、速度、状态）
- 开始按钮
- 清空日志按钮

**复用优势**:
- ✅ 发送和接收面板共享
- ✅ 统一的进度显示
- ✅ 统一的日志格式

---

### 5. send_panel.py - 发送面板

**职责**: 发送界面 UI + 发送逻辑

**核心设计**:
```python
class SendPanel:
    def __init__(
        self,
        parent: tk.Tk,
        theme: ThemeManager,
        saved_config: Dict[str, Any],
        log_queue: queue.Queue,
        on_back: callable
    ):
        self._create_ui()
    
    def _create_ui(self):
        # 头部、配置区、文件选择区、日志区
        self._create_header()
        self._create_config_section()
        self._create_file_section()
        
        # 使用 LogPanel 组件
        self.log_panel = LogPanel(...)
    
    def _start_transfer(self):
        # 启动传输线程
        pass
    
    def _transfer_worker(self):
        # 传输工作线程
        pass
```

**界面包含**:
- 返回按钮 + 标题
- 串口配置（波特率、串口号、测试）
- 文件选择（文件/文件夹）
- 日志和进度显示（LogPanel）

---

### 6. receive_panel.py - 接收面板

**职责**: 接收界面 UI + 接收逻辑

**核心设计**:
```python
class ReceivePanel:
    def __init__(
        self,
        parent: tk.Tk,
        theme: ThemeManager,
        saved_config: Dict[str, Any],
        log_queue: queue.Queue,
        on_back: callable
    ):
        self._create_ui()
    
    def _create_ui(self):
        # 头部、配置区、保存目录区、日志区
        self._create_header()
        self._create_config_section()
        self._create_dir_section()
        
        # 使用 LogPanel 组件
        self.log_panel = LogPanel(...)
    
    def _start_monitoring(self):
        # 启动监听线程
        pass
    
    def _receive_monitor_worker(self):
        # 接收工作线程
        pass
```

**界面包含**:
- 返回按钮 + 标题
- 串口配置（波特率、串口号、测试）
- 保存目录选择
- 日志和进度显示（LogPanel）

---

## 视图切换流程

```
┌──────────────────────┐
│   gui_main.py        │
│   (创建Tk窗口)        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  SerialTransferApp   │
│  (初始化主题、日志)   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ ModeSelectionView    │
│  (显示两个按钮)       │
└─────┬─────────┬──────┘
      │         │
  发送 │         │ 接收
      ▼         ▼
┌──────────┐  ┌──────────┐
│SendPanel │  │ReceivePanel│
│+ LogPanel│  │+ LogPanel │
└──────────┘  └──────────┘
```

**切换逻辑**:
1. 清空当前视图（`clear_current_view()`）
2. 创建新视图并传递回调函数
3. 新视图显示

---

## 线程管理

### 发送线程
```python
# SendPanel 中
def _start_transfer(self):
    self.transfer_thread = threading.Thread(
        target=self._transfer_worker,
        daemon=True
    )
    self.transfer_thread.start()

def _transfer_worker(self):
    # 使用 SenderFileManager 执行传输
    # 通过回调更新进度
    pass
```

### 接收线程
```python
# ReceivePanel 中
def _start_monitoring(self):
    self.monitor_thread = threading.Thread(
        target=self._receive_monitor_worker,
        daemon=True
    )
    self.monitor_thread.start()

def _receive_monitor_worker(self):
    # 使用 ReceiverFileManager 执行接收
    # 通过回调更新进度
    pass
```

---

## 日志系统

### 日志队列
```python
# app.py 中
self.log_queue = queue.Queue()

# 日志处理线程
def _process_log_queue(self):
    while True:
        try:
            record = self.log_queue.get(timeout=0.1)
            # 处理日志记录
        except queue.Empty:
            pass
```

### 日志更新
```python
# LogPanel 中
def _update_log_text(self):
    """定时从队列读取日志并显示"""
    try:
        while True:
            message = self.log_queue.get_nowait()
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
    except queue.Empty:
        pass
    finally:
        self.parent.after(100, self._update_log_text)
```

---

## 进度回调

### 发送端进度
```python
def progress_callback(current: int, total: int):
    """进度回调函数"""
    self.log_panel.update_progress(current, total)
```

### 接收端进度
```python
def progress_callback(current: int, total: int):
    """进度回调函数"""
    self.log_panel.update_progress(current, total)
```

---

## 错误处理

### 串口错误
```python
from serial_file_transfer.utils.error_handler import format_serial_error

try:
    # 串口操作
    pass
except Exception as e:
    error_msg = format_serial_error(e)
    messagebox.showerror("串口错误", error_msg)
```

### 传输错误
```python
try:
    # 传输操作
    pass
except Exception as e:
    logger.error(f"传输失败: {e}")
    messagebox.showerror("传输失败", str(e))
finally:
    # 清理资源
    self._reset_ui()
```

---

## 工具函数复用

### 格式化工具
```python
from serial_file_transfer.utils.format_utils import (
    format_transfer_speed,
    format_progress_text,
    calculate_transfer_speed
)

# 在 LogPanel 中使用
speed_text = format_transfer_speed(speed_bytes_per_sec)
display_text = format_progress_text(current, total)
```

### 串口测试
```python
from serial_file_transfer.core.serial_manager import SerialManager

# 测试串口可用性
available, error_msg = SerialManager.test_port_availability(
    port, baudrate, timeout=1.0
)
```

---

## 优化与改进

### 已实现优化
- ✅ 模块化架构（7个文件）
- ✅ 组件复用（LogPanel）
- ✅ 工具函数复用（error_handler、format_utils）
- ✅ 主题统一管理
- ✅ 线程安全的日志系统

### 代码质量
- ✅ PEP 8 合规
- ✅ 完整类型提示
- ✅ 完整文档字符串
- ✅ 中文注释

### 性能优化
- ✅ 异步日志更新（100ms间隔）
- ✅ 守护线程避免阻塞
- ✅ 队列通信避免竞态

---

## 使用指南

### 启动应用
```bash
python gui_main.py
```

### 修改主题
```python
# 在 theme.py 中修改
colors = ThemeColors(
    primary_color="#FF5722",  # 修改主色
    # ...
)
```

### 添加新视图
```python
# 1. 创建视图类
class NewView:
    def __init__(self, parent, theme, on_back):
        # ...
    
    def destroy(self):
        # ...

# 2. 在 app.py 中添加切换方法
def show_new_view(self):
    self.clear_current_view()
    self.current_view = NewView(...)
```

---

## 架构优势

### 可维护性
- 修改发送逻辑：只需编辑 `send_panel.py`
- 修改接收逻辑：只需编辑 `receive_panel.py`
- 更换主题：只需修改 `theme.py`
- 调整日志显示：修改 `log_panel.py`，所有面板自动更新

### 可测试性
- 每个模块可独立单元测试
- UI 组件和业务逻辑分离
- 依赖注入（通过构造函数）

### 可扩展性
- 易于添加新视图
- 易于添加新主题
- 易于添加新功能

---

**最后更新**: 2025-10-08

