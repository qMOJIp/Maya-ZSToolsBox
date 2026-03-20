# -*- coding: utf-8 -*-
"""
Maya脚本管理器 - 兼容Maya 2021-2026
支持PySide2和PySide6
"""
import os
import sys
import re
import json
import shutil
import time
import traceback
from datetime import datetime
from functools import partial
import uuid
import copy  # 用于深度复制

# 尝试为Maya 2021-2026添加Qt兼容性
try:
    # 首先尝试从Maya导入PySide2
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    import maya.cmds as cmds
    import maya.mel as mel
    qt_version = "PySide2"
except ImportError:
    try:
        # 如果PySide2导入失败，尝试导入PySide6（Maya 2024+）
        from PySide6.QtCore import *
        from PySide6.QtGui import *
        from PySide6.QtWidgets import *
        import maya.cmds as cmds
        import maya.mel as mel
        qt_version = "PySide6"
    except ImportError:
        # 如果都失败了，可能不在Maya中运行
        print("未能导入PySide，此脚本需要在Maya中运行")
        sys.exit()

# 获取Maya版本
def get_maya_version():
    """获取Maya版本号"""
    maya_version = cmds.about(version=True)
    # 提取年份
    try:
        version_year = int(maya_version.split()[0])
        return version_year
    except:
        return 2023  # 默认版本

# 设置全局Maya版本变量
MAYA_VERSION = get_maya_version()

def get_version_info():
    """获取版本信息用于调试"""
    return {
        "maya_version": MAYA_VERSION,
        "qt_version": qt_version,
        "python_version": sys.version,
        "os_platform": sys.platform
    }

# Maya主窗口获取函数
def maya_main_window():
    """获取Maya主窗口作为父窗口"""
    # 使用更可靠的方法获取Maya主窗口
    if qt_version == "PySide2":
        for obj in QApplication.topLevelWidgets():
            if obj.objectName() == 'MayaWindow':
                return obj
    else:  # PySide6
        for obj in QApplication.allWidgets():
            if obj.objectName() == 'MayaWindow':
                return obj
    # 如果上面的方法失败，尝试通过窗口标题查找
    for obj in QApplication.topLevelWidgets():
        if 'Maya' in obj.windowTitle():
            return obj
    # 如果还找不到，返回None
    return None

# 脚本编辑器类 - 用于编辑和创建脚本
class ScriptEditor(QDialog):
    """脚本编辑器窗口"""
    def __init__(self, parent=None, script_content="", script_type="python", script_name="", edit_mode=False, callback=None, tooltip=""):
        super(ScriptEditor, self).__init__(parent)
        
        # 设置窗口属性
        self.setWindowTitle("脚本编辑器")
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)
        
        # 设置拖放支持
        self.setAcceptDrops(True)
        
        # 保存脚本类型、名称和编辑模式
        self.script_type = script_type
        self.script_name = script_name
        self.edit_mode = edit_mode
        self.callback = callback  # 保存回调函数
        
        # 创建UI
        self.create_ui()
        
        # 设置初始内容
        if script_content:
            self.editor.setPlainText(script_content)
            
        if script_name:
            self.name_edit.setText(script_name)
            
        # 设置脚本类型
        if script_type == "python":
            self.python_radio.setChecked(True)
        else:
            self.mel_radio.setChecked(True)
            
        # 如果是编辑模式，设置名称不可编辑
        if edit_mode:
            # 名称依然可以编辑，但会给用户提示这是编辑模式
            self.setWindowTitle(f"编辑脚本 - {script_name}")
        
        # 设置提示信息
        if tooltip:
            self.tooltip_edit.setPlainText(tooltip)
        
        # 更新编辑器样式
        self.update_editor_style()
        
    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        """放下事件"""
        if event.mimeData().hasUrls():
            # 获取第一个拖放的文件
            url = event.mimeData().urls()[0]
            file_path = url.toLocalFile()
            
            # 尝试加载文件内容
            self.load_script_from_file(file_path)
            
            event.acceptProposedAction()
            
    def load_script_from_file(self, file_path):
        """从文件加载脚本内容"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "文件不存在", f"找不到文件: {file_path}")
            return False
            
        # 检查文件类型
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # 确定脚本类型
        if ext == '.py':
            self.python_radio.setChecked(True)
            self.script_type = "python"
        elif ext == '.mel':
            self.mel_radio.setChecked(True)
            self.script_type = "mel"
        else:
            # 未知文件类型，尝试检测内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1000)  # 读取前1000个字符以检测类型
                if "maya.cmds" in content or "import cmds" in content or "from maya import cmds" in content:
                    self.python_radio.setChecked(True)
                    self.script_type = "python"
                elif "proc" in content and "{" in content:
                    self.mel_radio.setChecked(True)
                    self.script_type = "mel"
                else:
                    # 默认按Python处理
                    self.python_radio.setChecked(True)
                    self.script_type = "python"
        
        # 尝试不同编码读取文件
        content = ""
        try:
            # 首先尝试UTF-8
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                # 然后尝试GBK（中文Windows常用）
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # 最后使用latin-1（可以读取任何文件但可能有乱码）
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
        
        # 设置编辑器内容
        self.editor.setPlainText(content)
        
        # 尝试从文件名中提取脚本名称
        script_name = os.path.basename(file_path)
        script_name = os.path.splitext(script_name)[0]  # 去除扩展名
        self.name_edit.setText(script_name)
        
        return True
            
    def create_ui(self):
        """创建界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 顶部工具栏
        top_layout = QHBoxLayout()
        
        # 脚本名称
        name_label = QLabel("脚本名称:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入脚本名称...")
        
        # 脚本类型选择
        type_label = QLabel("脚本类型:")
        type_group = QButtonGroup(self)
        self.python_radio = QRadioButton("Python")
        self.mel_radio = QRadioButton("MEL")
        type_group.addButton(self.python_radio)
        type_group.addButton(self.mel_radio)
        self.python_radio.setChecked(True)  # 默认选择Python
        
        # 连接脚本类型变更事件
        self.python_radio.toggled.connect(self.update_editor_style)
        
        # 添加到顶部布局
        top_layout.addWidget(name_label)
        top_layout.addWidget(self.name_edit, 1)
        top_layout.addSpacing(20)
        top_layout.addWidget(type_label)
        top_layout.addWidget(self.python_radio)
        top_layout.addWidget(self.mel_radio)
        
        main_layout.addLayout(top_layout)
        
        # 提示信息编辑区
        tooltip_layout = QHBoxLayout()
        tooltip_label = QLabel("提示信息:")
        self.tooltip_edit = QPlainTextEdit()
        self.tooltip_edit.setMaximumHeight(60)
        self.tooltip_edit.setPlaceholderText("输入工具提示信息（可选）...")
        tooltip_layout.addWidget(tooltip_label)
        tooltip_layout.addWidget(self.tooltip_edit, 1)
        main_layout.addLayout(tooltip_layout)
        
        # 代码编辑器
        self.editor = QPlainTextEdit()
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        
        # 设置等宽字体
        font = QFont("Consolas, Courier New, monospace")
        font.setPointSize(10)
        self.editor.setFont(font)
        
        # 启用Tab键
        self.editor.setTabStopDistance(40)  # 相当于4个空格
        
        # 添加自定义拖放支持
        original_dragEnterEvent = self.editor.dragEnterEvent
        original_dropEvent = self.editor.dropEvent
        
        def editor_dragEnterEvent(event):
            """编辑器拖拽进入事件"""
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            elif hasattr(original_dragEnterEvent, '__call__'):
                original_dragEnterEvent(event)
                
        def editor_dropEvent(event):
            """编辑器放下事件"""
            if event.mimeData().hasUrls():
                url = event.mimeData().urls()[0]
                file_path = url.toLocalFile()
                self.load_script_from_file(file_path)
                event.acceptProposedAction()
            elif hasattr(original_dropEvent, '__call__'):
                original_dropEvent(event)
                
        self.editor.dragEnterEvent = editor_dragEnterEvent
        self.editor.dropEvent = editor_dropEvent
        
        main_layout.addWidget(self.editor, 1)
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        
        # 保存按钮
        save_text = "保存" if self.edit_mode else "保存并创建"
        self.save_button = QPushButton(save_text)
        self.save_button.clicked.connect(self.save_script)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.close)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
        """)
        
        # 状态栏
        self.status_bar = QLabel("")
        self.status_bar.setStyleSheet("color: #999;")
        
        button_layout.addWidget(self.status_bar, 1)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
        
    def update_editor_style(self):
        """根据脚本类型更新编辑器样式"""
        if self.python_radio.isChecked():
            self.script_type = "python"
            self.editor.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #282c34;
                    color: #abb2bf;
                    border: 1px solid #555;
                    border-radius: 3px;
                    selection-background-color: #3e4451;
                    selection-color: #ffffff;
                }
            """)
        else:
            self.script_type = "mel"
            self.editor.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #263238;
                    color: #eeffff;
                    border: 1px solid #555;
                    border-radius: 3px;
                    selection-background-color: #546e7a;
                    selection-color: #ffffff;
                }
            """)
            
    def save_script(self):
        """保存脚本"""
        # 获取脚本内容
        script_content = self.editor.toPlainText().strip()
        if not script_content:
            self.status_bar.setText("脚本内容不能为空")
            self.status_bar.setStyleSheet("color: #FF6666;")
            return
            
        # 获取脚本名称
        script_name = self.name_edit.text().strip()
        if not script_name:
            self.status_bar.setText("脚本名称不能为空")
            self.status_bar.setStyleSheet("color: #FF6666;")
            return
            
        # 获取脚本类型
        script_type = "python" if self.python_radio.isChecked() else "mel"
        
        # 获取提示信息
        tooltip = self.tooltip_edit.toPlainText().strip()
        
        # 调用回调函数
        success = False
        
        if self.callback:
            # 检查父对象是否有配置更新方法
            if hasattr(self.parent(), "create_new_tool") or hasattr(self.parent(), "update_tool"):
                # 创建自定义回调代理函数，添加提示信息参数
                def callback_with_tooltip(name, content, script_type, edit_mode):
                    # 获取当前工具对象
                    for tool in self.parent().config["tools"]:
                        if tool["name"] == name or (edit_mode and tool["filename"] == self.parent().script_editor_filename):
                            # 设置提示信息
                            tool["tooltip"] = tooltip
                            self.parent().save_config()
                            break
                    
                    # 调用原始回调
                    return self.callback(name, content, script_type, edit_mode)
                
                success = callback_with_tooltip(script_name, script_content, script_type, self.edit_mode)
            else:
                success = self.callback(script_name, script_content, script_type, self.edit_mode)
                
            if success:
                self.status_bar.setText(f"脚本已保存: {script_name}")
                self.status_bar.setStyleSheet("color: #66CC66;")
                # 如果是新建模式，在保存后重置编辑器
                if not self.edit_mode:
                    self.editor.clear()
                    self.name_edit.clear()
                    self.tooltip_edit.clear()
                    self.status_bar.setText("新建脚本已保存，请继续编辑或关闭窗口")
            else:
                self.status_bar.setText("保存脚本失败")
                self.status_bar.setStyleSheet("color: #FF6666;")
                
    def run_script(self):
        """运行当前脚本"""
        script_content = self.editor.toPlainText()
        
        if not script_content.strip():
            self.status_bar.setText("没有脚本内容可运行")
            self.status_bar.setStyleSheet("color: #FF6666;")
            return
            
        try:
            # 根据脚本类型执行
            if self.script_type == "python":
                # 执行Python脚本
                exec(script_content)
            else:
                # 执行MEL脚本
                mel.eval(script_content)
                
            self.status_bar.setText("脚本执行成功")
            self.status_bar.setStyleSheet("color: #66CC66;")
        except Exception as e:
            error_msg = str(e)
            self.status_bar.setText(f"执行错误: {error_msg}")
            self.status_bar.setStyleSheet("color: #FF6666;")
            traceback.print_exc()

class ScriptsBox(QDialog):
    def __init__(self, parent=maya_main_window()):
        super(ScriptsBox, self).__init__(parent)
        
        # 记录Qt和Maya版本信息，用于兼容性处理
        self.qt_version = qt_version
        self.maya_version = MAYA_VERSION
        
        # 设置窗口关闭属性
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # 应用兼容性修复
        self.apply_compatibility_fixes()
        
        self.setWindowTitle("Maya 脚本管理器")
        self.setMinimumWidth(800)  # 增加默认宽度
        self.setMinimumHeight(500)  # 增加默认高度
        
        # 设置窗口标志，确保关闭按钮可见
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint | Qt.WindowCloseButtonHint)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QDialog {
                background-color: #333333;
                color: #CCCCCC;
            }
            QLabel {
                color: #CCCCCC;
            }
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
            QLineEdit, QComboBox {
                background-color: #3A3A3A;
                color: #EEEEEE;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # 设置接受拖放
        self.setAcceptDrops(True)
        
        # 添加回收站相关属性
        self.recycle_bin_visible = False
        
        # 配置文件路径
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.tools_dir = os.path.join(self.current_dir, "tool")
        self.config_file = os.path.join(self.current_dir, "config.json")
        
        # 回收站目录
        self.recycle_dir = os.path.join(self.current_dir, "recycle_bin")
        
        # 创建工具目录（如果不存在）
        if not os.path.exists(self.tools_dir):
            os.makedirs(self.tools_dir)
            
        # 创建默认分组目录
        self.default_group_dir = os.path.join(self.tools_dir, "常用工具")
        if not os.path.exists(self.default_group_dir):
            os.makedirs(self.default_group_dir)
            
        # 创建回收站目录（如果不存在）
        if not os.path.exists(self.recycle_dir):
            os.makedirs(self.recycle_dir)
            
        # 初始化配置
        self.config = self.load_config()
        
        # 工具按钮字典，用于存储按钮引用
        self.tool_buttons = {}
        
        # 创建UI
        self.create_ui()
        
        # 加载已有工具
        self.load_tools()
        
        # 脚本编辑器实例
        self.script_editor = None
    
    def apply_compatibility_fixes(self):
        """应用不同版本的兼容性修复"""
        try:
            # Maya 2024+使用PySide6时的特殊处理
            if self.maya_version >= 2024 and self.qt_version == "PySide6":
                # PySide6的某些Qt信号可能需要特殊处理
                pass
                
            # Maya 2021-2023使用PySide2时的特殊处理
            elif 2021 <= self.maya_version <= 2023 and self.qt_version == "PySide2":
                pass
            
            # Maya 2025特殊处理 - 窗口关闭问题修复
            if self.maya_version >= 2025:
                # 确保窗口可以通过叉叉关闭
                self.setAttribute(Qt.WA_DeleteOnClose, True)
                
                # 调整窗口标志，确保关闭按钮可用
                flags = self.windowFlags()
                self.setWindowFlags(flags | Qt.WindowCloseButtonHint)
                
        except Exception as e:
            cmds.warning(f"应用兼容性修复时出错: {str(e)}")
            traceback.print_exc()
    
    def closeEvent(self, event):
        """重写关闭事件处理"""
        try:
            # 清理资源，确保窗口能够正确关闭
            if hasattr(self, 'script_editor') and self.script_editor:
                try:
                    self.script_editor.close()
                    self.script_editor.deleteLater()
                except:
                    pass
            
            # 如果是Maya 2025+，进行特殊处理
            if self.maya_version >= 2025:
                # 记录关闭动作
                cmds.warning(f"正在关闭脚本管理器窗口...")
                
                # 延迟删除自身对象
                self.deleteLater()
            
            # 接受关闭事件
            event.accept()
            
        except Exception as e:
            # 如果出现错误，仍然允许窗口关闭
            cmds.warning(f"关闭窗口时出错: {str(e)}")
            event.accept()
    
    def create_ui(self):
        """创建UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # 左侧导航栏区域
        nav_widget = QWidget()
        nav_widget.setObjectName("navPanel")
        nav_widget.setStyleSheet("""
            #navPanel {
                background-color: #2D2D2D;
                border-radius: 5px;
            }
        """)
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setAlignment(Qt.AlignTop)
        nav_layout.setContentsMargins(5, 10, 5, 10)
        nav_layout.setSpacing(5)
        
        # 导航标题
        nav_title = QLabel("脚本分组")
        nav_title.setStyleSheet("font-weight: bold; font-size: 16px; color: #E0E0E0;")
        nav_title.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(nav_title)
        
        # 添加分组按钮
        add_group_btn = QPushButton("+ 新建分组")
        add_group_btn.clicked.connect(self.add_group)
        add_group_btn.setStyleSheet("""
            QPushButton {
                padding: 5px;
                font-weight: bold;
                font-size: 16px;
                background-color: #3A6EA5;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #4A7EB5;
            }
        """)
        nav_layout.addWidget(add_group_btn)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #555555;")
        nav_layout.addWidget(line)
        
        # 添加回收站按钮
        self.recycle_bin_btn = QPushButton("回收站")
        self.recycle_bin_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px;
                background-color: #444;
                border: none;
                border-radius: 3px;
                margin: 2px;
                font-size: 13px;
                color: #E0E0E0;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #666;
            }
        """)
        self.recycle_bin_btn.clicked.connect(self.show_recycle_bin)
        nav_layout.addWidget(self.recycle_bin_btn)
        
        # 导航栏分组按钮容器
        self.nav_scroll = QScrollArea()
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setFrameShape(QFrame.NoFrame)
        self.nav_scroll.setFixedWidth(180)  # 增加导航栏宽度
        
        self.nav_container = QWidget()
        self.nav_container.setStyleSheet("background-color: transparent;")
        self.nav_buttons_layout = QVBoxLayout(self.nav_container)
        self.nav_buttons_layout.setAlignment(Qt.AlignTop)
        self.nav_buttons_layout.setContentsMargins(2, 2, 2, 2)
        self.nav_buttons_layout.setSpacing(4)
        
        self.nav_scroll.setWidget(self.nav_container)
        nav_layout.addWidget(self.nav_scroll)
        
        # 存储导航按钮
        self.nav_buttons = {}
        self.active_group_id = None
        
        # 右侧主内容区域
        content_widget = QWidget()
        content_widget.setObjectName("contentPanel")
        content_widget.setStyleSheet("""
            #contentPanel {
                background-color: #353535;
                border-radius: 5px;
            }
        """)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # 顶部工具栏 
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        
        # 添加脚本按钮
        add_btn = QPushButton("新建脚本")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A6D4A;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A7D5A;
            }
        """)
        add_btn.clicked.connect(self.open_script_editor)
        toolbar.addWidget(add_btn)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_tools)
        toolbar.addWidget(refresh_btn)
        
        # 设置按钮
        settings_btn = QPushButton("设置")
        settings_btn.clicked.connect(self.show_settings_dialog)
        toolbar.addWidget(settings_btn)
        
        # 伸缩器
        toolbar.addStretch()
        
        # 帮助按钮
        help_btn = QPushButton("?")
        help_btn.setFixedSize(28, 28)
        help_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a6ea5; 
                color: white; 
                font-weight: bold;
                border-radius: 14px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4a7eb5;
            }
        """)
        help_btn.clicked.connect(self.show_help)
        toolbar.addWidget(help_btn)
        
        content_layout.addLayout(toolbar)
        
        # 右侧内容区标题
        self.content_title = QLabel("常用工具")
        self.content_title.setStyleSheet("font-weight: bold; font-size: 16px; padding: 5px; color: #E0E0E0;")
        self.content_title.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.content_title)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #555555;")
        content_layout.addWidget(line)
        
        # 创建滚动区域
        self.tool_scroll = QScrollArea()
        self.tool_scroll.setWidgetResizable(True)
        self.tool_scroll.setFrameShape(QFrame.NoFrame)
        self.tool_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #2A2A2A;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 工具按钮容器 - 使用 QVBoxLayout 作为主容器
        self.tools_container = QWidget()
        self.tools_container.setStyleSheet("background-color: transparent;")
        self.tools_layout = QVBoxLayout(self.tools_container)
        self.tools_layout.setAlignment(Qt.AlignTop)
        self.tools_layout.setContentsMargins(10, 10, 10, 10)
        self.tools_layout.setSpacing(8)
        
        # 用于存储各组的工具面板
        self.group_containers = {}
        
        self.tool_scroll.setWidget(self.tools_container)
        content_layout.addWidget(self.tool_scroll)
        
        # 回收站容器
        self.recycle_bin_container = QWidget()
        self.recycle_bin_container.setStyleSheet("background-color: transparent;")
        self.recycle_bin_layout = QVBoxLayout(self.recycle_bin_container)
        self.recycle_bin_layout.setAlignment(Qt.AlignTop)
        self.recycle_bin_layout.setContentsMargins(10, 10, 10, 10)
        self.recycle_bin_layout.setSpacing(8)
        self.recycle_bin_container.setVisible(False)
        content_layout.addWidget(self.recycle_bin_container)
        
        # 添加左侧导航栏和右侧内容区域到主布局
        main_layout.addWidget(nav_widget)
        main_layout.addWidget(content_widget, 1)  # 内容区域可以伸展
    
    def load_config(self):
        """加载配置文件"""
        default_config = {
            "groups": [
                {"name": "常用工具", "id": "default"}
            ],
            "tools": [],
            "recycle_bin": [],  # 添加回收站列表
            "button_layout": "single"  # 默认单列布局，可选值："single" 或 "double"
        }
        
        # 扫描tools目录，获取基于文件夹结构的分组和工具
        config = self.scan_tools_directory()
        
        # 如果存在config.json，仅读取回收站和按钮布局信息
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    old_config = json.load(f)
                    
                # 仅保留回收站和布局设置，其他信息从文件夹结构获取
                if "recycle_bin" in old_config:
                    config["recycle_bin"] = old_config["recycle_bin"]
                if "button_layout" in old_config:
                    config["button_layout"] = old_config["button_layout"]
            except Exception as e:
                cmds.warning(f"加载配置文件失败: {str(e)}，将使用默认配置")
                
        return config
    
    def scan_tools_directory(self):
        """扫描工具目录，基于文件夹结构获取分组和工具"""
        config = {
            "groups": [],
            "tools": [],
            "recycle_bin": [],
            "button_layout": "single"
        }
        
        # 获取tools目录下的所有子目录作为分组
        try:
            # 确保工具目录存在
            if not os.path.exists(self.tools_dir):
                os.makedirs(self.tools_dir)
                
            # 创建默认分组目录
            default_group_path = os.path.join(self.tools_dir, "常用工具")
            if not os.path.exists(default_group_path):
                os.makedirs(default_group_path)
                
            # 获取所有子目录作为分组
            for item in os.listdir(self.tools_dir):
                item_path = os.path.join(self.tools_dir, item)
                if os.path.isdir(item_path):
                    group_id = f"group_{len(config['groups'])}"
                    if item == "常用工具":
                        group_id = "default"
                        
                    group = {
                        "id": group_id,
                        "name": item
                    }
                    config["groups"].append(group)
                    
                    # 扫描该分组目录中的脚本文件
                    self.scan_group_directory(item_path, group_id, config)
                    
            # 确保至少有一个默认分组
            if not config["groups"]:
                config["groups"].append({"name": "常用工具", "id": "default"})
                
        except Exception as e:
            cmds.warning(f"扫描工具目录失败: {str(e)}")
            # 确保至少有一个默认分组
            config["groups"] = [{"name": "常用工具", "id": "default"}]
            
        return config
    
    def scan_group_directory(self, group_path, group_id, config):
        """扫描分组目录中的脚本文件"""
        try:
            for file_name in os.listdir(group_path):
                file_path = os.path.join(group_path, file_name)
                
                # 只处理文件，跳过子目录
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(file_name)
                    ext = ext.lower()
                    
                    # 仅处理.py和.mel文件
                    if ext in ['.py', '.mel']:
                        script_type = "python" if ext == ".py" else "mel"
                        
                        # 读取文件内容提取脚本名称和提示信息
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                        except:
                            try:
                                with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                                    content = f.read()
                            except:
                                with open(file_path, 'r', encoding='latin-1') as f:
                                    content = f.read()
                        
                        # 从文件内容中提取名称和提示信息
                        script_name = self.extract_name_from_content(content, script_type)
                        tooltip = self.extract_tooltip_from_content(content, script_type)
                        
                        # 如果无法从内容中提取名称，使用文件名
                        if not script_name:
                            script_name = os.path.splitext(file_name)[0]
                            
                        # 创建工具信息
                        tool_info = {
                            "name": script_name,
                            "filename": file_name,
                            "type": script_type,
                            "group": group_id
                        }
                        
                        # 添加提示信息（如果有）
                        if tooltip:
                            tool_info["tooltip"] = tooltip
                            
                        # 添加到工具列表
                        config["tools"].append(tool_info)
        except Exception as e:
            cmds.warning(f"扫描分组目录失败: {group_path}, 错误: {str(e)}")
    
    def save_config(self):
        """保存配置到文件，仅保存必要信息，不保存分组和工具信息"""
        # 仅保存回收站和按钮布局信息
        config_to_save = {
            "recycle_bin": self.config["recycle_bin"],
            "button_layout": self.config["button_layout"]
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_to_save, f, indent=4, ensure_ascii=False)
    
    def load_tools(self):
        """从文件夹结构加载工具按钮，按组分类"""
        # 重新扫描工具目录
        self.config = self.scan_tools_directory()
        
        # 如果存在config.json，读取回收站和按钮布局信息
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    
                # 仅更新回收站和布局设置
                if "recycle_bin" in saved_config:
                    self.config["recycle_bin"] = saved_config["recycle_bin"]
                if "button_layout" in saved_config:
                    self.config["button_layout"] = saved_config["button_layout"]
            except Exception as e:
                cmds.warning(f"加载配置文件失败: {str(e)}")
        
        # 清除现有按钮和组容器
        for i in reversed(range(self.tools_layout.count())):
            widget = self.tools_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 清除导航按钮
        for i in reversed(range(self.nav_buttons_layout.count())):
            widget = self.nav_buttons_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        self.group_containers = {}
        self.nav_buttons = {}
        
        # 确保至少有一个默认组
        if not self.config.get("groups"):
            self.config["groups"] = [{"name": "常用工具", "id": "default"}]
        
        # 首先创建所有组的容器（但不显示）
        for group in self.config["groups"]:
            self.create_group_container(group)
            self.create_nav_button(group)
        
        # 然后添加所有工具到各自的组容器
        for tool in self.config["tools"]:
            # 如果工具没有指定组，添加到默认组
            group_id = tool.get("group", "default")
            
            # 确保组存在，如果不存在，添加到默认组
            if group_id not in self.group_containers:
                group_id = "default"
                tool["group"] = group_id
            
            # 创建按钮并添加到对应的组
            self.create_tool_button(tool, group_id)
        
        # 更新导航按钮的工具计数
        self.update_nav_button_counters()
        
        # 更新回收站按钮文本
        recycle_count = len(self.config.get("recycle_bin", []))
        self.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
        
        # 默认显示第一个组或默认组
        if "default" in self.group_containers:
            self.show_group("default")
        elif self.config["groups"]:
            self.show_group(self.config["groups"][0]["id"])
    
    def create_group_container(self, group):
        """创建组容器"""
        group_id = group["id"]
        group_name = group["name"]
        
        # 创建组容器面板
        group_panel = QWidget()
        group_panel.setVisible(False)  # 初始不可见
        
        # 获取当前布局模式
        layout_mode = self.config.get("button_layout", "single")
        
        # 根据布局模式选择布局类型
        if layout_mode == "double":
            # 双列布局 - 使用QGridLayout
            group_layout = QGridLayout(group_panel)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(3)
            group_layout.setAlignment(Qt.AlignTop)
        else:
            # 单列布局 - 使用QVBoxLayout
            group_layout = QVBoxLayout(group_panel)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(3)
            group_layout.setAlignment(Qt.AlignTop)
        
        # 存储组引用和布局模式
        self.group_containers[group_id] = {
            "panel": group_panel,
            "layout": group_layout,
            "name": group_name,
            "layout_mode": layout_mode
        }
        
        # 设置拖放接受
        group_panel.setAcceptDrops(True)
        
        # 添加自定义拖放事件处理
        original_dragEnterEvent = group_panel.dragEnterEvent
        original_dropEvent = group_panel.dropEvent
        
        def custom_dragEnterEvent(event, gid=group_id):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            elif hasattr(original_dragEnterEvent, '__call__'):
                original_dragEnterEvent(event)
        
        def custom_dropEvent(event, gid=group_id):
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    file_path = url.toLocalFile()
                    self.process_dropped_file(file_path, gid)
                event.acceptProposedAction()
            elif hasattr(original_dropEvent, '__call__'):
                original_dropEvent(event)
        
        group_panel.dragEnterEvent = custom_dragEnterEvent
        group_panel.dropEvent = custom_dropEvent
        
        # 添加到主布局
        self.tools_layout.addWidget(group_panel)
        
        return group_panel
    
    def show_group(self, group_id):
        """显示指定组的内容"""
        # 隐藏回收站
        self.recycle_bin_container.setVisible(False)
        self.recycle_bin_visible = False
        self.recycle_bin_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 10px;
                background-color: #444;
                border: none;
                border-radius: 3px;
                margin: 2px;
                color: #E0E0E0;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #666;
            }
        """)
        
        # 隐藏当前显示的组
        if self.active_group_id and self.active_group_id in self.group_containers:
            self.group_containers[self.active_group_id]["panel"].setVisible(False)
            
            # 重置导航按钮样式
            if self.active_group_id in self.nav_buttons:
                self.nav_buttons[self.active_group_id].setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 8px 10px;
                        background-color: #444;
                        border: none;
                        border-radius: 3px;
                        margin: 2px;
                        color: #E0E0E0;
                    }
                    QPushButton:hover {
                        background-color: #555;
                    }
                    QPushButton:pressed {
                        background-color: #666;
                    }
                """)
        
        # 显示新选择的组
        if group_id in self.group_containers:
            self.group_containers[group_id]["panel"].setVisible(True)
            self.content_title.setText(self.group_containers[group_id]["name"])
            
            # 高亮当前导航按钮
            if group_id in self.nav_buttons:
                self.nav_buttons[group_id].setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 8px 10px;
                        background-color: #3a6ea5;
                        border: none;
                        border-radius: 3px;
                        margin: 2px;
                        color: white;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #4a7eb5;
                    }
                    QPushButton:pressed {
                        background-color: #5a8ec5;
                    }
                """)
            
            # 更新当前活动组ID
            self.active_group_id = group_id
    
    def show_nav_context_menu(self, group, position, button):
        """显示导航按钮的右键菜单"""
        group_id = group["id"]
        
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #333333;
                color: #E0E0E0;
                border: 1px solid #555555;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px 5px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #3a6ea5;
            }
            QMenu::item:disabled {
                color: #777777;
            }
        """)
        
        rename_action = menu.addAction("重命名")
        delete_action = menu.addAction("删除")
        
        # 如果是默认组，不允许删除
        if group_id == "default":
            delete_action.setEnabled(False)
        
        action = menu.exec_(button.mapToGlobal(position))
        
        if action == rename_action:
            self.rename_group(group)
        elif action == delete_action:
            self.delete_group(group)
    
    def rename_group(self, group):
        """重命名组"""
        group_id = group["id"]
        old_name = group["name"]
        
        # 弹出输入对话框
        new_name, ok = QInputDialog.getText(
            self, "重命名分组", "请输入新的分组名称:", 
            QLineEdit.Normal, old_name
        )
        
        if ok and new_name and new_name != old_name:
            # 更新配置
            for g in self.config["groups"]:
                if g["id"] == group_id:
                    g["name"] = new_name
                    break
            
            # 更新UI - 组容器名称
            if group_id in self.group_containers:
                self.group_containers[group_id]["name"] = new_name
                
                # 如果当前显示的是这个组，更新标题
                if self.active_group_id == group_id:
                    self.content_title.setText(new_name)
            
            # 更新UI - 导航按钮
            if group_id in self.nav_buttons:
                # 保留计数部分
                old_text = self.nav_buttons[group_id].text()
                count_match = re.search(r'\((\d+)\)$', old_text)
                count_text = f" ({count_match.group(1)})" if count_match else ""
                
                self.nav_buttons[group_id].setText(f"{new_name}{count_text}")
            
            # 保存配置
            self.save_config()
    
    def delete_group(self, group):
        """删除组"""
        group_id = group["id"]
        group_name = group["name"]
        
        # 确认删除
        reply = QMessageBox.question(
            self, "删除分组", 
            f"确定要删除分组 '{group_name}' 吗？\n该分组中的所有工具将移至默认分组。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 查找该组目录
            group_dir = os.path.join(self.tools_dir, group_name)
            
            # 获取默认组目录
            default_group_dir = os.path.join(self.tools_dir, "常用工具")
            if not os.path.exists(default_group_dir):
                os.makedirs(default_group_dir)
            
            # 移动该组中的工具到默认组
            for tool in self.config["tools"]:
                if tool.get("group") == group_id:
                    # 移动文件
                    source_file = os.path.join(group_dir, tool["filename"])
                    dest_file = os.path.join(default_group_dir, tool["filename"])
                    
                    # 如果目标文件已存在，生成新文件名
                    if os.path.exists(dest_file) and source_file != dest_file:
                        basename, ext = os.path.splitext(tool["filename"])
                        counter = 1
                        new_filename = f"{basename}_{counter}{ext}"
                        while os.path.exists(os.path.join(default_group_dir, new_filename)):
                            counter += 1
                            new_filename = f"{basename}_{counter}{ext}"
                        
                        # 更新目标文件路径和工具文件名
                        dest_file = os.path.join(default_group_dir, new_filename)
                        tool["filename"] = new_filename
                    
                    # 复制文件到默认组
                    try:
                        # 读取源文件
                        with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # 写入目标文件
                        with open(dest_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                    except Exception as e:
                        cmds.warning(f"移动文件失败: {source_file} -> {dest_file}, 错误: {str(e)}")
                    
                    # 更新工具组ID
                    tool["group"] = "default"
            
            # 尝试删除组目录
            try:
                if os.path.exists(group_dir):
                    # 确保目录为空
                    if not os.listdir(group_dir):
                        os.rmdir(group_dir)
                    else:
                        # 如果目录不为空，移动所有剩余文件到默认组
                        for file_name in os.listdir(group_dir):
                            source_file = os.path.join(group_dir, file_name)
                            dest_file = os.path.join(default_group_dir, file_name)
                            
                            # 仅移动文件，不移动子目录
                            if os.path.isfile(source_file):
                                # 处理文件名冲突
                                if os.path.exists(dest_file):
                                    basename, ext = os.path.splitext(file_name)
                                    counter = 1
                                    new_filename = f"{basename}_{counter}{ext}"
                                    while os.path.exists(os.path.join(default_group_dir, new_filename)):
                                        counter += 1
                                        new_filename = f"{basename}_{counter}{ext}"
                                    dest_file = os.path.join(default_group_dir, new_filename)
                                
                                # 复制文件
                                shutil.copy2(source_file, dest_file)
                        
                        # 再次尝试删除目录
                        shutil.rmtree(group_dir, ignore_errors=True)
            except Exception as e:
                cmds.warning(f"删除分组目录失败: {group_dir}, 错误: {str(e)}")
            
            # 从配置中删除组
            self.config["groups"] = [g for g in self.config["groups"] if g["id"] != group_id]
            
            # 重新加载UI
            self.refresh_tools()
            
            # 显示默认组
            self.show_group("default")
    
    def show_recycle_bin(self):
        """显示回收站内容"""
        # 隐藏当前显示的组
        if self.active_group_id and self.active_group_id in self.group_containers:
            self.group_containers[self.active_group_id]["panel"].setVisible(False)
            
            # 重置导航按钮样式
            if self.active_group_id in self.nav_buttons:
                self.nav_buttons[self.active_group_id].setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 8px 10px;
                        background-color: #444;
                        border: none;
                        border-radius: 3px;
                        margin: 2px;
                        color: #E0E0E0;
                    }
                    QPushButton:hover {
                        background-color: #555;
                    }
                    QPushButton:pressed {
                        background-color: #666;
                    }
                """)
        
        # 加载回收站内容
        self.load_recycle_bin()
        
        # 设置回收站可见
        self.recycle_bin_container.setVisible(True)
        self.content_title.setText("回收站")
        self.recycle_bin_visible = True
        
        # 高亮回收站按钮
        self.recycle_bin_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 10px;
                background-color: #3a6ea5;
                border: none;
                border-radius: 3px;
                margin: 2px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a7eb5;
            }
            QPushButton:pressed {
                background-color: #5a8ec5;
            }
        """)
        
        # 更新当前活动组ID为null，表示在回收站中
        self.active_group_id = None
    
    def load_recycle_bin(self):
        """加载回收站内容"""
        # 清除当前回收站UI中的项目
        self.clear_layout(self.recycle_bin_layout)
        
        # 添加回收站顶部操作区域
        header_widget = QWidget()
        header_widget.setObjectName("recycleHeader")
        header_widget.setStyleSheet("""
            #recycleHeader {
                background-color: #2D2D2D;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 15, 15, 15)
        header_layout.setSpacing(10)
        
        # 添加说明文本
        desc_label = QLabel("此处显示已删除的脚本，您可以选择恢复或永久删除它们。")
        desc_label.setStyleSheet("color: #BBBBBB; font-style: italic; padding: 0px;")
        desc_label.setWordWrap(True)
        header_layout.addWidget(desc_label)
        
        # 操作按钮区域
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 5, 0, 5)
        actions_layout.setSpacing(10)
        
        # 清空回收站按钮
        clear_btn = QPushButton("清空回收站")
        clear_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #a83232; 
                color: white;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #b84242;
            }
            QPushButton:pressed {
                background-color: #982222;
            }
        """)
        clear_btn.clicked.connect(self.clear_recycle_bin)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D5578;
                color: white;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3A6EA5;
            }
            QPushButton:pressed {
                background-color: #224466;
            }
        """)
        refresh_btn.clicked.connect(self.load_recycle_bin)
        
        # 添加按钮到布局
        actions_layout.addWidget(refresh_btn)
        actions_layout.addStretch(1)
        actions_layout.addWidget(clear_btn)
        
        header_layout.addLayout(actions_layout)
        self.recycle_bin_layout.addWidget(header_widget)
        
        # 如果回收站为空，显示一个提示信息
        if not self.config.get("recycle_bin"):
            empty_widget = QWidget()
            empty_widget.setObjectName("emptyRecycleBin")
            empty_widget.setStyleSheet("""
                #emptyRecycleBin {
                    background-color: #2D2D2D;
                    border-radius: 5px;
                }
            """)
            empty_layout = QVBoxLayout(empty_widget)
            
            # 添加空回收站图标
            icon_label = QLabel()
            icon_label.setAlignment(Qt.AlignCenter)
            # 获取标准图标并设置大小
            pixmap = self.style().standardIcon(QStyle.SP_TrashIcon).pixmap(64, 64)
            icon_label.setPixmap(pixmap)
            empty_layout.addWidget(icon_label)
            
            # 添加文本
            empty_label = QLabel("回收站为空")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #AAAAAA; font-size: 16px; padding: 10px; font-weight: bold;")
            empty_layout.addWidget(empty_label)
            
            empty_layout.setContentsMargins(20, 30, 20, 30)
            self.recycle_bin_layout.addWidget(empty_widget)
            
            # 添加底部空间
            spacer = QWidget()
            spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.recycle_bin_layout.addWidget(spacer)
            return
        
        # 添加已删除项目的列表容器
        items_container = QWidget()
        items_container.setObjectName("recycleItems")
        items_container.setStyleSheet("""
            #recycleItems {
                background-color: #2D2D2D;
                border-radius: 5px;
            }
        """)
        items_layout = QVBoxLayout(items_container)
        items_layout.setContentsMargins(15, 15, 15, 15)
        items_layout.setSpacing(8)
        
        # 添加标题
        items_count = len(self.config.get("recycle_bin", []))
        title_label = QLabel(f"已删除项目 ({items_count})")
        title_label.setStyleSheet("color: #CCCCCC; font-size: 14px; font-weight: bold;")
        items_layout.addWidget(title_label)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #555555; margin: 5px 0;")
        items_layout.addWidget(line)
        
        # 为每个回收站项目创建一个卡片
        for deleted_item in self.config["recycle_bin"]:
            item_widget = QWidget()
            item_widget.setObjectName("recycleItem")
            item_widget.setStyleSheet("""
                #recycleItem {
                    background-color: #383838;
                    border-radius: 6px;
                    margin: 2px 0;
                }
                #recycleItem:hover {
                    background-color: #404040;
                }
            """)
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(12, 10, 12, 10)
            item_layout.setSpacing(10)
            
            # 脚本类型图标
            icon_label = QLabel()
            if deleted_item['type'] == 'python':
                # 为Python脚本添加图标
                pixmap = self.style().standardIcon(QStyle.SP_FileIcon).pixmap(32, 32)
                icon_label.setPixmap(pixmap)
                icon_label.setStyleSheet("background-color: #4A6D4A; border-radius: 4px; padding: 2px;")
            else:
                # 为MEL脚本添加图标
                pixmap = self.style().standardIcon(QStyle.SP_FileIcon).pixmap(32, 32)
                icon_label.setPixmap(pixmap)
                icon_label.setStyleSheet("background-color: #4D6B8A; border-radius: 4px; padding: 2px;")
            
            icon_label.setFixedSize(36, 36)
            item_layout.addWidget(icon_label)
            
            # 脚本信息区域
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(3)
            
            # 脚本名称
            name_label = QLabel(deleted_item["name"])
            name_label.setStyleSheet("font-weight: bold; color: #E0E0E0; font-size: 13px;")
            info_layout.addWidget(name_label)
            
            # 文件名信息
            filename_label = QLabel(f"文件: {deleted_item.get('filename', '未知')}")
            filename_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
            info_layout.addWidget(filename_label)
            
            # 组合文件类型和删除日期信息
            details_layout = QHBoxLayout()
            details_layout.setContentsMargins(0, 0, 0, 0)
            details_layout.setSpacing(10)
            
            # 脚本类型
            type_badge = "Python" if deleted_item['type'] == 'python' else "MEL"
            type_color = "#4A6D4A" if deleted_item['type'] == 'python' else "#4D6B8A"
            type_label = QLabel(f"<span style='background-color:{type_color}; padding:2px 8px; border-radius:3px; color:white; font-size:11px;'>{type_badge}</span>")
            details_layout.addWidget(type_label)
            
            # 添加删除日期信息
            if "delete_date" in deleted_item:
                date_label = QLabel(f"删除于: {deleted_item['delete_date']}")
                date_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
                details_layout.addWidget(date_label)
            
            # 添加原分组信息
            if "original_group" in deleted_item:
                group_id = deleted_item["original_group"]
                group_name = "默认分组"
                for group in self.config["groups"]:
                    if group["id"] == group_id:
                        group_name = group["name"]
                        break
                original_group_label = QLabel(f"原分组: {group_name}")
                original_group_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
                details_layout.addWidget(original_group_label)
            
            details_layout.addStretch(1)
            info_layout.addLayout(details_layout)
            
            item_layout.addWidget(info_widget, 1)  # 让信息区域占据主要空间
            
            # 操作按钮区域
            buttons_widget = QWidget()
            buttons_layout = QHBoxLayout(buttons_widget)
            buttons_layout.setContentsMargins(0, 0, 0, 0)
            buttons_layout.setSpacing(6)
            
            # 恢复按钮
            restore_btn = QPushButton("恢复")
            restore_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
            restore_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3A6EA5;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #4A7EB5;
                }
                QPushButton:pressed {
                    background-color: #2A5E95;
                }
            """)
            restore_btn.setToolTip("恢复此脚本到原分组")
            restore_btn.clicked.connect(partial(self.restore_from_recycle_bin, deleted_item))
            buttons_layout.addWidget(restore_btn)
            
            # 永久删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogDiscardButton))
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #a83232;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #b84242;
                }
                QPushButton:pressed {
                    background-color: #982222;
                }
            """)
            delete_btn.setToolTip("永久删除此脚本")
            delete_btn.clicked.connect(partial(self.permanently_delete, deleted_item))
            buttons_layout.addWidget(delete_btn)
            
            item_layout.addWidget(buttons_widget)
            
            # 添加到回收站容器
            items_layout.addWidget(item_widget)
        
        self.recycle_bin_layout.addWidget(items_container)
        
        # 添加底部空间
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.recycle_bin_layout.addWidget(spacer)
    
    def clear_layout(self, layout):
        """清除布局中的所有控件"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())
    
    def clear_recycle_bin(self):
        """清空回收站"""
        # 确认对话框
        result = QMessageBox.question(
            self,
            "清空回收站",
            "确定要永久删除回收站中的所有项目吗？此操作无法撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
            
        try:
            # 清空回收站目录中的文件
            for item in self.config.get("recycle_bin", []):
                # 删除脚本文件
                recycle_file = os.path.join(self.recycle_dir, item.get("filename", ""))
                if os.path.exists(recycle_file):
                    os.remove(recycle_file)
            
            # 清空回收站配置
            self.config["recycle_bin"] = []
            
            # 保存配置
            self.save_config()
            
            # 重新加载回收站
            self.load_recycle_bin()
            
            # 更新回收站按钮文本
            self.recycle_bin_btn.setText(f"回收站 (0)")
            
            cmds.inViewMessage(message="回收站已清空", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"清空回收站失败: {str(e)}")
            QMessageBox.critical(self, "操作失败", f"清空回收站失败: {str(e)}")
    
    def restore_from_recycle_bin(self, deleted_item):
        """从回收站恢复项目"""
        try:
            # 获取文件路径
            recycle_file = os.path.join(self.recycle_dir, deleted_item.get("filename", ""))
            
            # 确保文件存在
            if not os.path.exists(recycle_file):
                raise ValueError(f"回收站中的文件不存在: {recycle_file}")
            
            # 确定目标组
            original_group = deleted_item.get("original_group", deleted_item.get("group", "default"))
            
            # 检查组是否存在
            group_name = "常用工具"
            group_exists = False
            for group in self.config["groups"]:
                if group["id"] == original_group:
                    group_name = group["name"]
                    group_exists = True
                    break
            
            # 如果组不存在，使用默认组
            if not group_exists:
                original_group = "default"
                group_name = "常用工具"
            
            # 确保目标组目录存在
            group_dir = os.path.join(self.tools_dir, group_name)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)
            
            # 目标文件路径
            dest_file = os.path.join(group_dir, deleted_item.get("filename", ""))
            
            # 检查目标文件是否存在，如果存在则重命名
            if os.path.exists(dest_file) and recycle_file != dest_file:
                basename, ext = os.path.splitext(deleted_item.get("filename", ""))
                counter = 1
                new_filename = f"{basename}_{counter}{ext}"
                while os.path.exists(os.path.join(group_dir, new_filename)):
                    counter += 1
                    new_filename = f"{basename}_{counter}{ext}"
                
                # 更新目标文件路径和工具文件名
                dest_file = os.path.join(group_dir, new_filename)
                deleted_item["filename"] = new_filename
            
            # 复制文件到目标目录
            shutil.copy2(recycle_file, dest_file)
            
            # 从回收站删除文件
            os.remove(recycle_file)
            
            # 从回收站列表中移除
            self.config["recycle_bin"].remove(deleted_item)
            
            # 重新添加到工具列表
            tool_info = {
                "name": deleted_item.get("name", "未命名工具"),
                "filename": deleted_item.get("filename", ""),
                "type": deleted_item.get("type", "python"),
                "group": original_group,
                "tooltip": deleted_item.get("tooltip", "")
            }
            
            # 保存配置
            self.save_config()
            
            # 刷新工具显示
            self.refresh_tools()
            
            # 更新回收站按钮
            recycle_count = len(self.config.get("recycle_bin", []))
            self.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
            
            # 刷新回收站显示
            self.load_recycle_bin()
            
            cmds.inViewMessage(message=f"已恢复: {tool_info['name']}", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"恢复失败: {str(e)}")
            QMessageBox.critical(self, "恢复失败", f"恢复失败: {str(e)}")
    
    def permanently_delete(self, deleted_item):
        """永久删除回收站中的项目"""
        try:
            # 确认对话框
            result = QMessageBox.question(
                self,
                "永久删除",
                f"确定要永久删除 '{deleted_item.get('name', '未命名工具')}' 吗？此操作无法撤销。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result != QMessageBox.Yes:
                return
                
            # 获取文件路径
            recycle_file = os.path.join(self.recycle_dir, deleted_item.get("filename", ""))
            
            # 删除文件
            if os.path.exists(recycle_file):
                os.remove(recycle_file)
            
            # 从回收站列表中移除
            self.config["recycle_bin"].remove(deleted_item)
            
            # 保存配置
            self.save_config()
            
            # 更新回收站按钮
            recycle_count = len(self.config.get("recycle_bin", []))
            self.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
            
            # 刷新回收站显示
            self.load_recycle_bin()
            
            cmds.inViewMessage(message=f"已永久删除: {deleted_item.get('name', '未命名工具')}", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"删除失败: {str(e)}")
            QMessageBox.critical(self, "删除失败", f"删除失败: {str(e)}")
    
    def delete_tool(self, tool, button):
        """将工具移动到回收站"""
        try:
            # 确认对话框
            result = QMessageBox.question(
                self,
                "删除工具",
                f"确定要将 '{tool['name']}' 移到回收站吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result != QMessageBox.Yes:
                return
                
            # 查找工具所在的组
            group_id = tool.get("group", "default")
            group_name = "常用工具"
            for group in self.config["groups"]:
                if group["id"] == group_id:
                    group_name = group["name"]
                    break
            
            # 获取文件路径
            group_dir = os.path.join(self.tools_dir, group_name)
            tool_file = os.path.join(group_dir, tool.get("filename", ""))
            recycle_file = os.path.join(self.recycle_dir, tool.get("filename", ""))
            
            # 确保文件存在
            if not os.path.exists(tool_file):
                raise ValueError(f"工具文件不存在: {tool_file}")
            
            # 处理文件名冲突
            if os.path.exists(recycle_file) and tool_file != recycle_file:
                basename, ext = os.path.splitext(tool.get("filename", ""))
                counter = 1
                new_filename = f"{basename}_{counter}{ext}"
                while os.path.exists(os.path.join(self.recycle_dir, new_filename)):
                    counter += 1
                    new_filename = f"{basename}_{counter}{ext}"
                
                # 更新回收站文件路径和工具文件名
                recycle_file = os.path.join(self.recycle_dir, new_filename)
                tool["filename"] = new_filename
            
            # 移动文件到回收站目录
            shutil.copy2(tool_file, recycle_file)
            os.remove(tool_file)
            
            # 从工具列表中移除
            self.config["tools"].remove(tool)
            
            # 添加组信息和删除日期到工具信息中
            tool["original_group"] = group_id
            tool["delete_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 添加到回收站列表
            self.config["recycle_bin"].append(tool)
            
            # 保存配置
            self.save_config()
            
            # 删除按钮
            if button in self.tool_buttons:
                button_item = self.tool_buttons[button]
                group_id = button_item.get("group_id")
                
                if group_id in self.group_containers:
                    layout = self.group_containers[group_id]["layout"]
                    
                    # 处理不同的布局类型
                    if isinstance(layout, QVBoxLayout) or isinstance(layout, QHBoxLayout):
                        for i in range(layout.count()):
                            if layout.itemAt(i).widget() == button:
                                layout.removeItem(layout.itemAt(i))
                                break
                    elif isinstance(layout, QGridLayout):
                        for i in range(layout.count()):
                            if layout.itemAt(i).widget() == button:
                                row, col, _, _ = layout.getItemPosition(i)
                                layout.removeItem(layout.itemAt(i))
                                break
                    
                    # 删除按钮
                    button.deleteLater()
                    
                    # 移除引用
                    del self.tool_buttons[button]
            
            # 更新导航按钮计数
            self.update_nav_button_counters()
            
            # 更新回收站按钮
            recycle_count = len(self.config.get("recycle_bin", []))
            self.recycle_bin_btn.setText(f"回收站 ({recycle_count})")
            
            cmds.inViewMessage(message=f"已将 '{tool['name']}' 移动到回收站", pos='midCenter', fade=True)
        except Exception as e:
            cmds.warning(f"删除失败: {str(e)}")
            QMessageBox.critical(self, "删除失败", f"删除失败: {str(e)}")
    
    def create_nav_button(self, group):
        """创建导航栏按钮"""
        group_id = group["id"]
        group_name = group["name"]
        
        # 创建导航按钮
        nav_button = QPushButton(group_name)
        nav_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 10px;
                background-color: #444;
                border: none;
                border-radius: 3px;
                margin: 2px;
                color: #E0E0E0;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #666;
            }
        """)
        
        # 设置上下文菜单策略
        nav_button.setContextMenuPolicy(Qt.CustomContextMenu)
        nav_button.customContextMenuRequested.connect(lambda pos, g=group: self.show_nav_context_menu(g, pos, nav_button))
        
        # 点击导航按钮显示对应组
        nav_button.clicked.connect(lambda: self.show_group(group_id))
        
        # 添加到导航栏布局
        self.nav_buttons_layout.addWidget(nav_button)
        
        # 存储导航按钮引用
        self.nav_buttons[group_id] = nav_button
        
        return nav_button
    
    def update_nav_button_counters(self):
        """更新导航按钮上的工具计数"""
        # 为每个组计算工具数量
        group_counts = {}
        
        # 初始化所有组的计数为0
        for group in self.config["groups"]:
            group_counts[group["id"]] = 0
        
        # 统计每个组的工具数量
        for tool in self.config["tools"]:
            group_id = tool.get("group", "default")
            if group_id in group_counts:
                group_counts[group_id] += 1
        
        # 更新导航按钮文本
        for group_id, count in group_counts.items():
            if group_id in self.nav_buttons:
                # 获取原始组名
                group_name = None
                for group in self.config["groups"]:
                    if group["id"] == group_id:
                        group_name = group["name"]
                        break
                
                if group_name:
                    # 更新按钮文本，添加工具计数
                    button_text = f"{group_name} ({count})"
                    self.nav_buttons[group_id].setText(button_text)
    
    def create_tool_button(self, tool, group_id="default"):
        """创建工具按钮，并添加到指定组"""
        button = QPushButton(tool["name"])
        
        # 设置按钮样式
        if tool["type"] == "mel":
            button.setStyleSheet("""
                QPushButton {
                    text-align: left; 
                    background-color: #4D6B8A; 
                    padding: 10px; 
                    border-radius: 4px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #5D7B9A;
                }
                QPushButton:pressed {
                    background-color: #3D5B7A;
                }
            """)
        else:  # python
            button.setStyleSheet("""
                QPushButton {
                    text-align: left; 
                    background-color: #4A6D4A; 
                    padding: 10px; 
                    border-radius: 4px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #5A7D5A;
                }
                QPushButton:pressed {
                    background-color: #3A5D3A;
                }
            """)
        
        # 连接点击事件
        button.clicked.connect(partial(self.run_tool, tool))
        
        # 添加右键菜单
        button.setContextMenuPolicy(Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(lambda pos, btn=button, t=tool: self.show_context_menu(pos, btn, t))
        
        # 设置提示信息（如果有）
        tooltip_text = ""
        if "tooltip" in tool and tool["tooltip"]:
            tooltip_text = tool["tooltip"]
        else:
            # 尝试从脚本内容中提取提示信息
            try:
                tool_path = os.path.join(self.tools_dir, tool["filename"])
                if os.path.exists(tool_path):
                    # 读取文件内容
                    try:
                        with open(tool_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        try:
                            with open(tool_path, 'r', encoding='gbk') as f:
                                content = f.read()
                        except UnicodeDecodeError:
                            with open(tool_path, 'r', encoding='latin-1') as f:
                                content = f.read()
                    
                    # 从内容提取提示信息
                    tooltip = self.extract_tooltip_from_content(content, tool["type"])
                    if tooltip:
                        tooltip_text = tooltip
                        # 保存提示信息到工具配置中
                        tool["tooltip"] = tooltip
                        self.save_config()
                    else:
                        # 如果没有提示信息，使用脚本名称作为提示
                        tooltip_text = f"运行 {tool['name']} ({tool['type'].upper()})"
            except Exception as e:
                # 出现错误时，使用默认提示
                tooltip_text = f"运行 {tool['name']}"
        
        # 确保提示文本被应用，且有适当的格式
        if tooltip_text:
            # 确定标题部分
            title = tool["name"]
            
            # 确定类型标识的颜色
            type_color = "#4D6B8A" if tool["type"] == "mel" else "#4A6D4A"
            type_label = "MEL" if tool["type"] == "mel" else "Python"
            
            styled_tooltip = f"""
            <div style="
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                font-size: 13px;
                color: #EFEFEF;
                background-color: #2A2A2A;
                padding: 10px;
                border: 1px solid #444444;
                border-radius: 5px;
                max-width: 350px;
                box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.3);
            ">
                <div style="
                    font-weight: bold; 
                    font-size: 14px;
                    border-bottom: 1px solid #444444;
                    padding-bottom: 6px;
                    margin-bottom: 8px;
                    display: flex;
                    justify-content: space-between;
                ">
                    <span>{title}</span>
                    <span style="
                        background-color: {type_color};
                        color: white;
                        font-size: 11px;
                        padding: 2px 6px;
                        border-radius: 3px;
                    ">{type_label}</span>
                </div>
                <div style="
                    white-space: pre-wrap;
                    line-height: 1.4;
                ">{tooltip_text}</div>
            </div>
            """
            button.setToolTip(styled_tooltip)
        
        # 添加到组布局
        if group_id in self.group_containers:
            container = self.group_containers[group_id]
            layout = container["layout"]
            layout_mode = container.get("layout_mode", "single")
            
            # 根据布局类型添加按钮
            if layout_mode == "double" and isinstance(layout, QGridLayout):
                # 获取当前行列计数
                count = layout.count()
                row = count // 2  # 整除得到行号
                col = count % 2   # 余数得到列号
                layout.addWidget(button, row, col)
            else:
                # 单列布局或默认情况
                layout.addWidget(button)
        else:
            # 如果指定的组不存在，添加到默认组
            if "default" in self.group_containers:
                container = self.group_containers["default"]
                layout = container["layout"]
                layout_mode = container.get("layout_mode", "single")
                
                # 根据布局类型添加按钮
                if layout_mode == "double" and isinstance(layout, QGridLayout):
                    count = layout.count()
                    row = count // 2
                    col = count % 2
                    layout.addWidget(button, row, col)
                else:
                    layout.addWidget(button)
                
                # 更新工具的组ID
                tool["group"] = "default"
            else:
                # 如果连默认组都不存在，添加到主布局
                self.tools_layout.addWidget(button)
                
        # 存储按钮引用
        self.tool_buttons[button] = {
            "tool": tool,
            "group_id": group_id
        }
        
        return button
    
    def run_tool(self, tool):
        """运行工具脚本"""
        # 查找工具所在组
        group_id = tool.get("group", "default")
        group_name = "常用工具"
        
        for group in self.config["groups"]:
            if group["id"] == group_id:
                group_name = group["name"]
                break
        
        # 获取组目录
        group_dir = os.path.join(self.tools_dir, group_name)
        tool_path = os.path.join(group_dir, tool["filename"])
        
        # 如果在组目录中找不到文件，尝试在工具根目录查找（兼容旧版本）
        if not os.path.exists(tool_path):
            old_path = os.path.join(self.tools_dir, tool["filename"])
            if os.path.exists(old_path):
                # 找到文件，复制到正确的组目录
                try:
                    # 确保组目录存在
                    if not os.path.exists(group_dir):
                        os.makedirs(group_dir)
                    
                    # 复制文件到正确位置
                    shutil.copy2(old_path, tool_path)
                    cmds.warning(f"文件已从旧位置移动到分组目录: {old_path} -> {tool_path}")
                except Exception as e:
                    cmds.warning(f"移动文件失败: {str(e)}")
                    # 使用旧路径继续操作
                    tool_path = old_path
            else:
                cmds.warning(f"找不到工具文件: {tool_path}")
                cmds.warning(f"尝试在旧位置查找也未找到: {old_path}")
                # 尝试在所有组目录中查找该文件
                found = False
                for search_group in self.config["groups"]:
                    search_group_name = search_group["name"]
                    search_dir = os.path.join(self.tools_dir, search_group_name)
                    search_path = os.path.join(search_dir, tool["filename"])
                    if os.path.exists(search_path):
                        tool_path = search_path
                        cmds.warning(f"在组 '{search_group_name}' 中找到工具文件")
                        # 更新工具所属组
                        tool["group"] = search_group["id"]
                        found = True
                        break
                
                if not found:
                    cmds.warning(f"在所有分组中都找不到工具文件 {tool['filename']}，无法运行")
                    return
        
        if tool["type"] == "mel":
            # 运行MEL脚本
            mel_path = tool_path.replace('\\', '/')
            # 使用Python包装执行MEL，避免语法问题
            py_cmd = f"""
import traceback
try:
    import maya.mel as mel
    mel.eval('source "{mel_path}"')
except Exception as e:
    import maya.cmds as cmds
    error_msg = traceback.format_exc()
    cmds.warning(f"执行MEL脚本出错: {{str(e)}}\\n{{error_msg}}")
"""
            try:
                # 使用evalDeferred确保在Maya主循环中运行
                cmds.evalDeferred(py_cmd)
            except Exception as e:
                cmds.warning(f"运行MEL脚本出错: {str(e)}")
        else:
            # 运行Python脚本
            try:
                # 确保脚本所在目录在路径中
                if self.tools_dir not in sys.path:
                    sys.path.append(self.tools_dir)
                
                # 添加组目录到路径
                script_dir = os.path.dirname(tool_path)
                if script_dir not in sys.path:
                    sys.path.append(script_dir)
                
                # 工具脚本的绝对路径
                abs_script_path = os.path.abspath(tool_path)
                script_dir = os.path.dirname(abs_script_path)
                
                # 创建在Maya主循环中执行的命令
                exec_cmd = f"""
import os
import sys
import traceback

try:
    # 添加脚本目录到路径
    script_dir = r"{script_dir}"
    tools_dir = r"{self.tools_dir}"
    
    # 确保目录在sys.path中
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    
    # 设置工作目录
    original_dir = os.getcwd()
    os.chdir(script_dir)
    
    # 加载脚本
    script_path = r"{abs_script_path}"
    
    # 检查文件是否存在
    if not os.path.exists(script_path):
        import maya.cmds as cmds
        cmds.warning(f"脚本文件不存在: {{script_path}}")
        raise FileNotFoundError(f"脚本文件不存在: {{script_path}}")
    
    # 执行代码
    with open(script_path, 'r', encoding='utf-8') as f:
        code = compile(f.read(), script_path, 'exec')
        exec(code, {{'__file__': script_path, '__name__': '__main__'}})
    
    # 恢复工作目录
    os.chdir(original_dir)
except UnicodeDecodeError:
    # 尝试不同编码
    try:
        with open(r"{abs_script_path}", 'r', encoding='gbk') as f:
            code = compile(f.read(), r"{abs_script_path}", 'exec')
            exec(code, {{'__file__': r"{abs_script_path}", '__name__': '__main__'}})
    except Exception as e:
        import maya.cmds as cmds
        error_msg = traceback.format_exc()
        cmds.warning(f"GBK编码运行脚本出错: {{str(e)}}\\n{{error_msg}}")
except FileNotFoundError as e:
    import maya.cmds as cmds
    cmds.warning(f"文件未找到: {{str(e)}}")
except Exception as e:
    import maya.cmds as cmds
    error_msg = traceback.format_exc()
    cmds.warning(f"运行Python脚本出错: {{str(e)}}\\n{{error_msg}}")
"""
                # 使用evalDeferred执行
                cmds.evalDeferred(exec_cmd)
            except Exception as e:
                cmds.warning(f"准备执行脚本时出错: {str(e)}")
    
    def extract_name_from_content(self, content, script_type):
        """从文件内容中提取名称"""
        # 尝试查找注释中的名称
        if script_type == "python":
            # 查找Python文件中的名称
            name_patterns = [
                r'#\s*名称[:：]\s*(.+)',
                r'#\s*工具名称[:：]\s*(.+)',
                r'#\s*脚本名称[:：]\s*(.+)',
                r'#\s*name[:：]\s*(.+)',
                r'#\s*tool name[:：]\s*(.+)',
                r'"""(.+?)"""'
            ]
        else:
            # 查找MEL文件中的名称
            name_patterns = [
                r'//\s*名称[:：]\s*(.+)',
                r'//\s*工具名称[:：]\s*(.+)',
                r'//\s*脚本名称[:：]\s*(.+)',
                r'//\s*name[:：]\s*(.+)',
                r'//\s*tool name[:：]\s*(.+)'
            ]
        
        # 尝试每个模式
        for pattern in name_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def show_context_menu(self, position, button, tool):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 25px 5px 20px;
                border: 1px solid transparent;
            }
            QMenu::item:selected {
                background-color: #3a3a3a;
                color: #ffffff;
            }
        """)

        # 创建菜单项
        edit_action = QAction("编辑", self)
        edit_tooltip_action = QAction("编辑提示", self)
        move_action = QAction("移动到组", self)
        delete_action = QAction("删除", self)
        settings_action = QAction("设置", self)

        # 添加分隔线和菜单项
        menu.addAction(edit_action)
        menu.addAction(edit_tooltip_action)
        
        # 创建移动到组的子菜单
        move_menu = QMenu("移动到组", self)
        move_menu.setStyleSheet(menu.styleSheet())
        
        # 添加现有组到子菜单
        move_actions = {}
        current_group_id = tool.get("group", "default")
        
        if self.config and "groups" in self.config:
            for group in self.config["groups"]:
                if "id" in group and "name" in group:
                    group_id = group["id"]
                    group_name = group["name"]
                    
                    # 当前所在分组不显示
                    if group_id == current_group_id:
                        continue
                        
                    group_action = QAction(group_name, self)
                    move_menu.addAction(group_action)
                    move_actions[group_action] = group_id
        
        # 添加新建组选项
        move_menu.addSeparator()
        new_group_action = QAction("新建分组", self)
        move_menu.addAction(new_group_action)
        
        # 将移动到组子菜单添加到主菜单
        menu.addMenu(move_menu)
        
        menu.addSeparator()
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(settings_action)

        # 显示菜单
        action = menu.exec_(button.mapToGlobal(position))
        
        # 处理选择
        if action == delete_action:
            self.delete_tool(tool, button)
        elif action == edit_action:
            self.edit_tool(tool)
        elif action == edit_tooltip_action:
            self.edit_tool_tooltip(tool, button)
        elif action == settings_action:
            self.show_settings_dialog()
        elif action == new_group_action:
            self.create_new_group(tool, button)
        elif action in move_actions:
            # 移动工具到选定的分组
            new_group_id = move_actions[action]
            self.move_tool_to_group(tool, button, new_group_id)
    
    def edit_tool_tooltip(self, tool, button):
        """编辑工具的提示信息"""
        # 获取当前提示信息
        current_tooltip = tool.get("tooltip", "")
        
        # 创建输入对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑提示信息")
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #333333;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
            }
            QTextEdit {
                background-color: #2A2A2A;
                color: #E0E0E0;
                border: 1px solid #555555;
                padding: 5px;
            }
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        
        # 布局
        layout = QVBoxLayout(dialog)
        
        # 说明标签
        info_label = QLabel("输入脚本提示信息，当鼠标悬停在按钮上时将显示此信息:", dialog)
        layout.addWidget(info_label)
        
        # 提示输入框
        tooltip_edit = QTextEdit(dialog)
        tooltip_edit.setPlainText(current_tooltip)
        tooltip_edit.setAcceptRichText(False)  # 只接受纯文本
        layout.addWidget(tooltip_edit)
        
        # 说明标签
        comment_pattern_label = QLabel("也可以在脚本中使用注释设置提示，例如：", dialog)
        layout.addWidget(comment_pattern_label)
        
        if tool["type"] == "python":
            comment_example = "# 提示: 这是一个提示信息"
        else:
            comment_example = "// 提示: 这是一个提示信息"
            
        example_label = QLabel(comment_example, dialog)
        example_label.setStyleSheet("color: #8899AA; font-family: monospace;")
        layout.addWidget(example_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 保存按钮
        save_btn = QPushButton("保存", dialog)
        save_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(save_btn)
        
        # 取消按钮
        cancel_btn = QPushButton("取消", dialog)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            # 获取新的提示信息
            new_tooltip = tooltip_edit.toPlainText().strip()
            
            # 更新提示信息
            tool["tooltip"] = new_tooltip
            
            # 保存配置
            self.save_config()
            
            # 更新按钮提示
            if new_tooltip:
                # 确定标题部分
                title = tool["name"]
                
                # 确定类型标识的颜色
                type_color = "#4D6B8A" if tool["type"] == "mel" else "#4A6D4A"
                type_label = "MEL" if tool["type"] == "mel" else "Python"
                
                styled_tooltip = f"""
                <div style="
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    font-size: 13px;
                    color: #EFEFEF;
                    background-color: #2A2A2A;
                    padding: 10px;
                    border: 1px solid #444444;
                    border-radius: 5px;
                    max-width: 350px;
                    box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.3);
                ">
                    <div style="
                        font-weight: bold; 
                        font-size: 14px;
                        border-bottom: 1px solid #444444;
                        padding-bottom: 6px;
                        margin-bottom: 8px;
                        display: flex;
                        justify-content: space-between;
                    ">
                        <span>{title}</span>
                        <span style="
                            background-color: {type_color};
                            color: white;
                            font-size: 11px;
                            padding: 2px 6px;
                            border-radius: 3px;
                        ">{type_label}</span>
                    </div>
                    <div style="
                        white-space: pre-wrap;
                        line-height: 1.4;
                    ">{new_tooltip}</div>
                </div>
                """
                button.setToolTip(styled_tooltip)
            else:
                # 确定标题部分和类型标识
                title = tool["name"]
                type_color = "#4D6B8A" if tool["type"] == "mel" else "#4A6D4A"
                type_label = "MEL" if tool["type"] == "mel" else "Python"
                default_tooltip = f"运行 {tool['name']}"
                
                styled_default_tooltip = f"""
                <div style="
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    font-size: 13px;
                    color: #EFEFEF;
                    background-color: #2A2A2A;
                    padding: 10px;
                    border: 1px solid #444444;
                    border-radius: 5px;
                    max-width: 350px;
                    box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.3);
                ">
                    <div style="
                        font-weight: bold; 
                        font-size: 14px;
                        border-bottom: 1px solid #444444;
                        padding-bottom: 6px;
                        margin-bottom: 8px;
                        display: flex;
                        justify-content: space-between;
                    ">
                        <span>{title}</span>
                        <span style="
                            background-color: {type_color};
                            color: white;
                            font-size: 11px;
                            padding: 2px 6px;
                            border-radius: 3px;
                        ">{type_label}</span>
                    </div>
                    <div style="
                        white-space: pre-wrap;
                        line-height: 1.4;
                    ">{default_tooltip}</div>
                </div>
                """
                button.setToolTip(styled_default_tooltip)
            
            # 显示成功消息
            status_text = "提示信息已更新" if new_tooltip else "提示信息已清空"
            cmds.inViewMessage(message=status_text, pos='midCenter', fade=True)
    
    def move_tool_to_group(self, tool, button, new_group_id):
        """将工具移动到新分组"""
        if new_group_id not in self.group_containers:
            return
            
        # 旧组ID
        old_group_id = tool.get("group", "default")
        
        # 如果组没变，不做任何操作
        if old_group_id == new_group_id:
            return
            
        # 查找新旧组的名称
        old_group_name = "常用工具"
        new_group_name = "常用工具"
        
        for group in self.config["groups"]:
            if group["id"] == old_group_id:
                old_group_name = group["name"]
            if group["id"] == new_group_id:
                new_group_name = group["name"]
        
        # 源文件和目标文件路径
        old_group_dir = os.path.join(self.tools_dir, old_group_name)
        new_group_dir = os.path.join(self.tools_dir, new_group_name)
        
        # 确保目标目录存在
        if not os.path.exists(new_group_dir):
            os.makedirs(new_group_dir)
            
        # 文件路径
        source_file = os.path.join(old_group_dir, tool["filename"])
        dest_file = os.path.join(new_group_dir, tool["filename"])
        
        # 如果目标文件已存在，生成一个新的文件名
        if os.path.exists(dest_file) and source_file != dest_file:
            # 获取文件名和扩展名
            basename, ext = os.path.splitext(tool["filename"])
            
            # 生成新文件名
            counter = 1
            new_filename = f"{basename}_{counter}{ext}"
            while os.path.exists(os.path.join(new_group_dir, new_filename)):
                counter += 1
                new_filename = f"{basename}_{counter}{ext}"
                
            # 更新目标文件路径
            dest_file = os.path.join(new_group_dir, new_filename)
            
            # 更新工具文件名
            tool["filename"] = new_filename
        
        # 复制文件到新组目录
        try:
            # 读取源文件内容
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 写入目标文件
            with open(dest_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            # 删除源文件
            if os.path.exists(source_file) and source_file != dest_file:
                os.remove(source_file)
        except Exception as e:
            cmds.warning(f"移动文件失败: {str(e)}")
            return
        
        # 修改工具分组
        tool["group"] = new_group_id
        
        # 重新加载UI
        self.refresh_tools()
        
        # 显示目标组
        self.show_group(new_group_id)
    
    def create_new_group(self, tool=None, button=None):
        """创建新分组并可选移动工具到这个分组"""
        # 创建输入对话框
        group_name, ok = QInputDialog.getText(
            self, 
            "新建分组", 
            "请输入分组名称:",
            QLineEdit.Normal, 
            ""
        )
        
        if ok and group_name.strip():
            group_name = group_name.strip()
            
            # 检查分组名称是否已存在
            for group in self.config["groups"]:
                if group["name"] == group_name:
                    cmds.warning(f"分组名称 '{group_name}' 已存在，请使用其他名称。")
                    return
            
            # 创建新分组ID
            group_id = f"group_{int(time.time())}_{len(self.config['groups'])}"
            
            # 添加新分组
            new_group = {
                "id": group_id,
                "name": group_name
            }
            
            # 创建分组目录
            new_group_dir = os.path.join(self.tools_dir, group_name)
            if not os.path.exists(new_group_dir):
                os.makedirs(new_group_dir)
            
            self.config["groups"].append(new_group)
            
            # 刷新UI以添加新分组
            self.refresh_tools()
            
            # 如果提供了工具和按钮，则移动工具到新分组
            if tool and button:
                self.move_tool_to_group(tool, button, group_id)
            
            # 显示新分组
            self.show_group(group_id)
            
            cmds.inViewMessage(message=f"已创建新分组 '{group_name}'", pos='midCenter', fade=True)
    
    def edit_tool(self, tool):
        """编辑工具"""
        # 查找工具所在组
        group_id = tool.get("group", "default")
        group_name = "常用工具"
        
        for group in self.config["groups"]:
            if group["id"] == group_id:
                group_name = group["name"]
                break
        
        # 获取组目录
        group_dir = os.path.join(self.tools_dir, group_name)
        tool_path = os.path.join(group_dir, tool["filename"])
        
        # 如果在组目录中找不到文件，尝试在工具根目录查找（兼容旧版本）
        if not os.path.exists(tool_path):
            old_path = os.path.join(self.tools_dir, tool["filename"])
            if os.path.exists(old_path):
                # 找到文件，复制到正确的组目录
                try:
                    # 确保组目录存在
                    if not os.path.exists(group_dir):
                        os.makedirs(group_dir)
                    
                    # 复制文件到正确位置
                    shutil.copy2(old_path, tool_path)
                    cmds.warning(f"文件已从旧位置移动到分组目录: {old_path} -> {tool_path}")
                except Exception as e:
                    cmds.warning(f"移动文件失败: {str(e)}")
                    # 使用旧路径继续操作
                    tool_path = old_path
            else:
                cmds.warning(f"找不到工具文件: {tool_path}")
                cmds.warning(f"尝试在旧位置查找也未找到: {old_path}")
                # 尝试在所有组目录中查找该文件
                found = False
                for search_group in self.config["groups"]:
                    search_group_name = search_group["name"]
                    search_dir = os.path.join(self.tools_dir, search_group_name)
                    search_path = os.path.join(search_dir, tool["filename"])
                    if os.path.exists(search_path):
                        tool_path = search_path
                        tool["group"] = search_group["id"]
                        cmds.warning(f"在组 '{search_group_name}' 中找到工具文件，已更新工具分组")
                        found = True
                        break
                
                if not found:
                    # 尝试找到文件名相似的文件
                    basename, ext = os.path.splitext(tool["filename"])
                    found_similar = False
                    similar_files = []
                    
                    # 搜索所有分组目录
                    for search_group in self.config["groups"]:
                        search_group_name = search_group["name"]
                        search_dir = os.path.join(self.tools_dir, search_group_name)
                        if os.path.exists(search_dir):
                            for file_name in os.listdir(search_dir):
                                file_basename, file_ext = os.path.splitext(file_name)
                                # 检查文件类型是否匹配
                                if file_ext.lower() == ext.lower():
                                    # 检查文件名是否相似 (包含关系或开头相似)
                                    if basename.lower() in file_basename.lower() or file_basename.lower().startswith(basename.lower()):
                                        similar_path = os.path.join(search_dir, file_name)
                                        similar_files.append({
                                            "path": similar_path,
                                            "name": file_name,
                                            "group_id": search_group["id"],
                                            "group_name": search_group_name
                                        })
                    
                    if similar_files:
                        # 找到了相似文件，使用第一个
                        similar = similar_files[0]
                        tool_path = similar["path"]
                        tool["filename"] = similar["name"]
                        tool["group"] = similar["group_id"]
                        cmds.warning(f"找到相似文件: {similar['name']} (在 {similar['group_name']} 分组中)，将使用此文件")
                        found_similar = True
                    
                    if not found_similar:
                        cmds.warning(f"在所有分组中都找不到工具文件或相似文件: {tool['filename']}")
                        QMessageBox.critical(self, "文件未找到", f"无法找到工具文件: {tool['filename']}\n请检查文件是否已被删除或移动。")
                        return
        
        # 读取文件内容
        script_content = ""
        try:
            # 尝试不同编码读取文件
            try:
                with open(tool_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(tool_path, 'r', encoding='gbk') as f:
                        script_content = f.read()
                except UnicodeDecodeError:
                    with open(tool_path, 'r', encoding='latin-1') as f:
                        script_content = f.read()
        except Exception as e:
            cmds.warning(f"无法读取文件: {tool_path}，错误: {str(e)}")
            QMessageBox.critical(self, "读取错误", f"无法读取文件: {tool_path}\n错误: {str(e)}")
            return
        
        # 打开脚本编辑器
        self.open_script_editor(
            script_content=script_content,
            script_type=tool["type"],
            script_name=tool["name"],
            edit_mode=True,
            filename=tool["filename"]
        )
    
    def open_script_editor(self, script_content="", script_type="python", script_name="", edit_mode=False, filename=""):
        """打开脚本编辑器"""
        # 关闭之前的编辑器（如果存在）
        if self.script_editor:
            try:
                self.script_editor.close()
                self.script_editor.deleteLater()
            except:
                pass
        
        # 提取提示信息
        tooltip = ""
        if edit_mode and filename:
            # 存储当前编辑文件名以便回调使用
            self.script_editor_filename = filename
            # 查找工具配置中的提示
            for tool in self.config["tools"]:
                if tool["filename"] == filename:
                    tooltip = tool.get("tooltip", "")
                    break
            
            # 如果配置中没有提示，尝试从内容提取
            if not tooltip and script_content:
                tooltip = self.extract_tooltip_from_content(script_content, script_type) or ""
        
        # 创建回调函数
        def save_callback(name, content, type, is_edit):
            if is_edit:
                # 编辑现有脚本
                return self.update_tool(filename, name, content, type)
            else:
                # 创建新脚本
                return self.create_new_tool(name, content, type)
        
        # 创建新编辑器
        self.script_editor = ScriptEditor(
            self,
            script_content=script_content,
            script_type=script_type,
            script_name=script_name,
            edit_mode=edit_mode,
            callback=save_callback,
            tooltip=tooltip
        )
        
        # 显示编辑器
        self.script_editor.show()
    
    def update_tool(self, filename, name, content, script_type):
        """更新工具脚本"""
        try:
            # 查找工具所在的组
            tool_info = None
            group_id = "default"
            for tool in self.config["tools"]:
                if tool["filename"] == filename:
                    tool_info = tool
                    group_id = tool.get("group", "default")
                    break
            
            if not tool_info:
                cmds.warning(f"找不到要更新的工具: {filename}")
                return False
                
            # 获取组名称
            group_name = "常用工具"  # 默认组名
            for group in self.config["groups"]:
                if group["id"] == group_id:
                    group_name = group["name"]
                    break
                    
            # 获取组目录路径
            group_dir = os.path.join(self.tools_dir, group_name)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)
                
            # 原始文件路径
            original_file_path = os.path.join(group_dir, filename)
            
            # 如果名称发生变化，生成新的文件名
            if name != tool_info["name"]:
                # 获取扩展名
                suffix = ".py" if script_type == "python" else ".mel"
                
                # 使用新名称生成文件名
                clean_name = re.sub(r'[\\/*?:"<>|]', '_', name)  # 替换Windows非法文件名字符
                clean_name = clean_name.strip()  # 移除前后空格
                
                # 确保文件名唯一
                base_filename = clean_name
                new_filename = f"{base_filename}{suffix}"
                counter = 1
                while os.path.exists(os.path.join(group_dir, new_filename)) and new_filename != filename:
                    new_filename = f"{base_filename}_{counter}{suffix}"
                    counter += 1
            else:
                # 名称没变，保持原文件名
                new_filename = filename
                
            # 如果文件名发生变化，需要重命名文件
            if new_filename != filename:
                new_file_path = os.path.join(group_dir, new_filename)
                # 删除可能的同名文件(不太可能，因为我们已经避免了冲突)
                if os.path.exists(new_file_path):
                    os.remove(new_file_path)
                # 更新内容并保存到新文件
                with open(new_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                # 删除旧文件
                if os.path.exists(original_file_path) and original_file_path != new_file_path:
                    os.remove(original_file_path)
            else:
                # 文件名没变，只更新内容
                with open(original_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # 更新工具配置信息
            tool_info["name"] = name
            # 如果文件名发生变化，更新filename字段
            if new_filename != filename:
                tool_info["filename"] = new_filename
            
            # 重新加载工具
            self.refresh_tools()
            
            return True
        except Exception as e:
            cmds.warning(f"更新脚本失败: {str(e)}")
            return False
    
    def create_new_tool(self, name, content, script_type):
        """创建新工具脚本"""
        try:
            # 生成文件名
            suffix = ".py" if script_type == "python" else ".mel"
            
            # 使用脚本名称作为文件名（移除非法字符）
            clean_name = re.sub(r'[\\/*?:"<>|]', '_', name)  # 替换Windows非法文件名字符
            clean_name = clean_name.strip()  # 移除前后空格
            
            # 默认保存到默认组
            group_id = "default"
            group_name = "常用工具"
            
            # 获取组目录路径
            group_dir = os.path.join(self.tools_dir, group_name)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)
            
            # 确保文件名唯一
            base_filename = clean_name
            filename = f"{base_filename}{suffix}"
            counter = 1
            while os.path.exists(os.path.join(group_dir, filename)):
                filename = f"{base_filename}_{counter}{suffix}"
                counter += 1
            
            # 保存文件
            file_path = os.path.join(group_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 添加到配置
            tool_info = {
                "name": name,  # 保存原始名称
                "filename": filename,
                "type": script_type,
                "group": group_id
            }
            
            # 从文件内容中提取提示信息
            tooltip = self.extract_tooltip_from_content(content, script_type)
            if tooltip:
                tool_info["tooltip"] = tooltip
            
            # 重新扫描并加载工具
            self.refresh_tools()
            
            return True
        except Exception as e:
            cmds.warning(f"创建脚本失败: {str(e)}")
            return False
    
    def refresh_tools(self):
        """刷新工具列表，重新扫描工具目录"""
        # 保存当前状态 - 是否在回收站中
        was_in_recycle_bin = self.recycle_bin_visible
        
        # 保存回收站和布局设置
        recycle_bin = self.config.get("recycle_bin", [])
        button_layout = self.config.get("button_layout", "single")
        
        # 重新扫描目录获取分组和工具
        self.config = self.scan_tools_directory()
        
        # 恢复回收站和布局设置
        self.config["recycle_bin"] = recycle_bin
        self.config["button_layout"] = button_layout
        
        # 保存配置（只保存回收站和布局设置）
        self.save_config()
        
        # 重新加载工具
        self.load_tools()
        
        # 如果之前在回收站中，重新显示回收站
        if was_in_recycle_bin:
            self.show_recycle_bin()
    
    def show_settings_dialog(self):
        """显示设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog.setFixedWidth(400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #333333;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
            }
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 1em;
                padding-top: 10px;
                color: #E0E0E0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QRadioButton {
                color: #E0E0E0;
            }
            QRadioButton::indicator {
                width: 15px;
                height: 15px;
            }
        """)
        
        # 对话框布局
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        
        # 布局设置组
        layout_group = QGroupBox("按钮布局设置")
        layout_group_layout = QVBoxLayout(layout_group)
        
        # 布局选项
        current_layout = self.config.get("button_layout", "single")
        
        # 单列布局选项
        single_layout_radio = QRadioButton("单列布局")
        single_layout_radio.setChecked(current_layout == "single")
        layout_group_layout.addWidget(single_layout_radio)
        
        # 双列布局选项
        double_layout_radio = QRadioButton("双列布局")
        double_layout_radio.setChecked(current_layout == "double")
        layout_group_layout.addWidget(double_layout_radio)
        
        # 添加布局组到主布局
        layout.addWidget(layout_group)
        
        # 配置导入/导出组
        config_group = QGroupBox("配置管理")
        config_group_layout = QVBoxLayout(config_group)
        
        # 导出配置按钮
        export_btn = QPushButton("导出配置")
        export_btn.clicked.connect(self.export_config)
        config_group_layout.addWidget(export_btn)
        
        # 导入配置按钮
        import_btn = QPushButton("导入配置")
        import_btn.clicked.connect(self.import_config)
        config_group_layout.addWidget(import_btn)
        
        # 添加配置组到主布局
        layout.addWidget(config_group)
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        
        # 应用按钮
        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(lambda: self.apply_settings(
            single_layout_radio.isChecked(), dialog
        ))
        button_layout.addWidget(apply_btn)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        dialog.exec_()
    
    def apply_settings(self, single_layout_selected, dialog):
        """应用设置"""
        # 获取当前布局模式
        old_layout = self.config.get("button_layout", "single")
        
        # 设置新的布局模式
        new_layout = "single" if single_layout_selected else "double"
        
        # 如果布局模式改变了，保存并刷新
        if old_layout != new_layout:
            self.config["button_layout"] = new_layout
            self.save_config()
            self.refresh_tools()
            dialog.accept()
            
            # 显示提示
            cmds.inViewMessage(message=f"已切换到{('单' if new_layout == 'single' else '双')}列按钮布局", 
                              pos='midCenter', fade=True)
    
    def export_config(self):
        """导出配置"""
        # 获取导出文件路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", 
            os.path.expanduser("~"),
            "JSON文件 (*.json)"
        )
        
        if not file_path:
            return
            
        # 确保文件有正确的扩展名
        if not file_path.lower().endswith('.json'):
            file_path += '.json'
            
        try:
            # 询问是否一同导出脚本文件
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("导出配置")
            msg_box.setText("请选择导出选项:")
            msg_box.setIcon(QMessageBox.Question)
            
            # 添加导出选项
            export_config_btn = msg_box.addButton("仅导出配置", QMessageBox.ActionRole)
            export_all_btn = msg_box.addButton("导出配置和脚本文件", QMessageBox.ActionRole)
            cancel_btn = msg_box.addButton("取消", QMessageBox.RejectRole)
            
            msg_box.exec_()
            
            # 用户选择取消
            if msg_box.clickedButton() == cancel_btn:
                return
                
            # 是否导出脚本文件
            export_tools = (msg_box.clickedButton() == export_all_btn)
            
            # 准备导出的配置（保留回收站和按钮布局信息）
            export_config = {
                "recycle_bin": self.config["recycle_bin"],
                "button_layout": self.config["button_layout"]
            }
            
            # 导出当前配置
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_config, f, indent=4, ensure_ascii=False)
            
            # 导出工具脚本
            exported_files = []
            if export_tools:
                # 创建工具导出目录
                export_dir = os.path.dirname(file_path)
                tools_export_dir = os.path.join(export_dir, "tool")
                
                # 确保导出目录存在
                if not os.path.exists(tools_export_dir):
                    os.makedirs(tools_export_dir)
                
                # 复制整个工具目录结构
                for group in self.config["groups"]:
                    group_name = group["name"]
                    group_dir = os.path.join(self.tools_dir, group_name)
                    export_group_dir = os.path.join(tools_export_dir, group_name)
                    
                    # 创建分组目录
                    if not os.path.exists(export_group_dir):
                        os.makedirs(export_group_dir)
                    
                    # 复制该分组中的所有脚本文件
                    if os.path.exists(group_dir):
                        for file_name in os.listdir(group_dir):
                            source_file = os.path.join(group_dir, file_name)
                            if os.path.isfile(source_file):
                                # 只复制.py和.mel文件
                                if file_name.lower().endswith(('.py', '.mel')):
                                    dest_file = os.path.join(export_group_dir, file_name)
                                    shutil.copy2(source_file, dest_file)
                                    exported_files.append(os.path.join(group_name, file_name))
                
                # 显示导出统计
                export_msg = f"已导出配置和 {len(exported_files)} 个脚本文件到 {export_dir}"
                cmds.inViewMessage(message=export_msg, pos='midCenter', fade=True)
            else:
                # 仅导出配置
                cmds.inViewMessage(message=f"已导出配置到 {file_path}", pos='midCenter', fade=True)
                
        except Exception as e:
            cmds.warning(f"导出失败: {str(e)}")
            QMessageBox.critical(self, "导出失败", f"导出配置失败: {str(e)}")
    
    def import_config(self):
        """从JSON文件导入配置"""
        # 获取导入文件路径
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", 
            os.path.expanduser("~"),
            "JSON文件 (*.json)"
        )
        
        if not file_path or not os.path.exists(file_path):
            return
            
        try:
            # 读取配置文件
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 检查是否有相关的工具脚本文件夹
            import_dir = os.path.dirname(file_path)
            tools_folder = os.path.join(import_dir, "tool")
            has_tools_folder = os.path.exists(tools_folder) and os.path.isdir(tools_folder)
            
            # 确认导入选项
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("导入配置")
            msg_box.setText("请选择导入选项:")
            msg_box.setIcon(QMessageBox.Question)
            
            # 添加导入选项
            import_config_btn = msg_box.addButton("仅导入配置", QMessageBox.ActionRole)
            import_all_btn = msg_box.addButton("导入配置和脚本文件", QMessageBox.ActionRole)
            cancel_btn = msg_box.addButton("取消", QMessageBox.RejectRole)
            
            # 如果没有找到工具文件夹，禁用导入脚本选项
            if not has_tools_folder:
                import_all_btn.setEnabled(False)
                import_all_btn.setToolTip("未在配置文件同级目录找到 'tool' 文件夹")
            
            msg_box.exec_()
            
            # 用户选择取消
            if msg_box.clickedButton() == cancel_btn:
                return
                
            # 是否导入脚本文件
            import_tools = (msg_box.clickedButton() == import_all_btn)
            
            # 备份当前配置中的回收站信息
            recycle_bin = self.config.get("recycle_bin", [])
            button_layout = self.config.get("button_layout", "single")
            
            # 更新回收站和布局设置
            if "recycle_bin" in imported_config:
                recycle_bin = imported_config["recycle_bin"]
            if "button_layout" in imported_config:
                button_layout = imported_config["button_layout"]
            
            # 如果要导入脚本文件
            if import_tools and has_tools_folder:
                # 创建备份文件夹
                backup_dir = os.path.join(self.current_dir, f"tools_backup_{int(time.time())}")
                if os.path.exists(self.tools_dir):
                    shutil.copytree(self.tools_dir, backup_dir)
                
                # 复制整个工具目录结构
                for item in os.listdir(tools_folder):
                    source_path = os.path.join(tools_folder, item)
                    
                    # 只处理目录，作为分组
                    if os.path.isdir(source_path):
                        group_name = item
                        dest_path = os.path.join(self.tools_dir, group_name)
                        
                        # 创建目标目录（如果不存在）
                        if not os.path.exists(dest_path):
                            os.makedirs(dest_path)
                        
                        # 复制该目录中的所有文件
                        for file_name in os.listdir(source_path):
                            source_file = os.path.join(source_path, file_name)
                            if os.path.isfile(source_file):
                                # 只复制.py和.mel文件
                                if file_name.lower().endswith(('.py', '.mel')):
                                    dest_file = os.path.join(dest_path, file_name)
                                    shutil.copy2(source_file, dest_file)
            
            # 更新配置，但需要重新扫描目录
            self.config = self.scan_tools_directory()
            self.config["recycle_bin"] = recycle_bin
            self.config["button_layout"] = button_layout
            
            # 保存配置
            self.save_config()
            
            # 立即刷新界面显示
            self.refresh_tools()
            
            message = "配置已导入，界面已更新"
            if import_tools and has_tools_folder:
                message += f"，脚本文件已导入。原工具目录已备份至 {backup_dir}"
            
            cmds.inViewMessage(message=message, pos='midCenter', fade=True)
            
        except Exception as e:
            cmds.warning(f"导入失败: {str(e)}")
            QMessageBox.critical(self, "导入失败", f"导入配置失败: {str(e)}")
            
            # 如果已经更改了配置，尝试恢复
            try:
                if 'backup_config' in locals():
                    self.config = backup_config
                    self.save_config()
                    self.load_tools()
            except:
                pass
    
    def dragEnterEvent(self, event):
        """拖放进入事件处理"""
        # 接受文件拖放
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """拖放事件处理"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                # 默认添加到当前显示的分组
                current_group_id = "default"
                
                # 遍历所有分组容器，找出当前可见的一个
                for group_id, container in self.group_containers.items():
                    if container["panel"].isVisible():
                        current_group_id = group_id
                        break
                
                # 处理拖放的文件
                self.process_dropped_file(file_path, current_group_id)
            
            event.acceptProposedAction()
    
    def process_dropped_file(self, file_path, target_group_id="default"):
        """处理拖放的文件"""
        # 检查文件扩展名
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext not in ['.py', '.mel']:
            cmds.warning(f"只支持.py和.mel文件，跳过: {file_path}")
            return
            
        # 确定脚本类型
        script_type = 'python' if ext == '.py' else 'mel'
        
        # 提取文件名
        file_name = os.path.basename(file_path)
        
        # 尝试读取文件内容
        try:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
        except Exception as e:
            cmds.warning(f"读取文件失败: {file_path}，错误: {str(e)}")
            return
            
        # 从内容提取脚本名称
        display_name = self.extract_name_from_content(content, script_type)
        
        # 如果从内容中无法提取名称，则使用文件名
        if not display_name:
            display_name = os.path.splitext(file_name)[0]
        
        # 查找目标组
        group_name = "常用工具"
        for group in self.config["groups"]:
            if group["id"] == target_group_id:
                group_name = group["name"]
                break
        
        # 确保目标组目录存在
        group_dir = os.path.join(self.tools_dir, group_name)
        if not os.path.exists(group_dir):
            os.makedirs(group_dir)
        
        # 使用脚本名称作为文件名（移除非法字符）
        clean_name = re.sub(r'[\\/*?:"<>|]', '_', display_name)  # 替换Windows非法文件名字符
        clean_name = clean_name.strip()  # 移除前后空格
        
        # 确保文件名唯一
        base_filename = clean_name
        dest_filename = f"{base_filename}{ext}"
        counter = 1
        while os.path.exists(os.path.join(group_dir, dest_filename)):
            dest_filename = f"{base_filename}_{counter}{ext}"
            counter += 1
        
        # 复制文件到目标组目录
        dest_file = os.path.join(group_dir, dest_filename)
        try:
            shutil.copy2(file_path, dest_file)
        except Exception as e:
            cmds.warning(f"复制文件失败: {file_path}，错误: {str(e)}")
            return
        
        # 确保目标组有效，如果没有则使用默认组
        if target_group_id not in self.group_containers:
            target_group_id = "default"
        
        # 从内容中提取提示信息
        tooltip = self.extract_tooltip_from_content(content, script_type)
        
        # 重新扫描并加载工具
        self.refresh_tools()
        
        # 滚动到工具所在的组
        self.scroll_to_group(target_group_id)
        
        cmds.inViewMessage(message=f"工具已添加到 '{self.get_group_name(target_group_id)}' 组: {display_name}", pos='midCenter', fade=True)
    
    def get_group_name(self, group_id):
        """根据组ID获取组名"""
        for group in self.config["groups"]:
            if group["id"] == group_id:
                return group["name"]
        return "未知组"
    
    def scroll_to_group(self, group_id):
        """滚动到指定组 - 在新布局中，这个方法会显示对应的组"""
        self.show_group(group_id)
    
    def add_group(self):
        """添加新组"""
        # 弹出输入对话框
        group_name, ok = QInputDialog.getText(
            self, "添加分组", "请输入分组名称:", 
            QLineEdit.Normal, ""
        )
        
        if ok and group_name:
            # 检查分组名称是否已存在
            for group in self.config["groups"]:
                if group["name"] == group_name:
                    cmds.warning(f"分组名称 '{group_name}' 已存在，请使用其他名称。")
                    return
            
            # 创建分组目录
            group_dir = os.path.join(self.tools_dir, group_name)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)
            
            # 生成唯一ID
            group_id = "group_" + str(int(time.time()))
            
            # 添加到配置
            new_group = {
                "name": group_name,
                "id": group_id
            }
            
            self.config["groups"].append(new_group)
            
            # 创建组容器和导航按钮
            self.create_group_container(new_group)
            self.create_nav_button(new_group)
            
            # 显示新组
            self.show_group(group_id)
            
            cmds.inViewMessage(message=f"已创建新分组 '{group_name}'", pos='midCenter', fade=True)

    # 添加显示帮助信息的方法
    def show_help(self):
        """显示帮助信息"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("脚本管理器 - 帮助信息")
        help_dialog.setMinimumWidth(700)
        help_dialog.setMinimumHeight(600)
        
        # 设置对话框样式
        help_dialog.setStyleSheet("""
            QDialog {
                background-color: #333333;
                color: #E0E0E0;
            }
            QLabel {
                color: #E0E0E0;
            }
            QTextBrowser {
                background-color: #2A2A2A;
                color: #E0E0E0;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton {
                background-color: #3a6ea5;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a7eb5;
            }
            QPushButton:pressed {
                background-color: #2a5e95;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout(help_dialog)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 创建标题
        title_label = QLabel("Maya脚本管理器使用指南")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #E0E0E0; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 创建文本浏览器以显示帮助内容
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)  # 允许打开外部链接
        layout.addWidget(text_browser)
        
        # 设置帮助信息文本
        help_html = """
        <style>
            body { color: #E0E0E0; font-family: Arial, sans-serif; }
            h2 { color: #4a7eb5; margin-top: 20px; margin-bottom: 10px; }
            h3 { color: #66BBFF; margin-top: 15px; margin-bottom: 5px; }
            ul { margin-top: 5px; padding-left: 20px; }
            li { margin-bottom: 5px; }
            .note { background-color: #2D4056; padding: 8px; border-radius: 4px; margin: 10px 0; }
            .tip { color: #AAFFAA; }
            .highlight { color: #FFCC66; font-weight: bold; }
            a { color: #66BBFF; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .section { border-bottom: 1px solid #555555; padding-bottom: 10px; margin-bottom: 10px; }
        </style>
        
        <div class="section">
            <p>脚本管理器可以帮助您更高效地组织和运行Maya中的Python和MEL脚本，提高工作效率。</p>
        </div>
        
        <h2>主要功能</h2>
        <ul>
            <li><b>脚本管理</b> - 创建、编辑、组织和运行Python/MEL脚本</li>
            <li><b>分组功能</b> - 将脚本整理到不同分组中，便于管理</li>
            <li><b>一键执行</b> - 点击按钮即可运行脚本</li>
            <li><b>拖放支持</b> - 直接拖放外部.py或.mel文件导入</li>
            <li><b>回收站机制</b> - 删除的脚本可从回收站恢复</li>
            <li><b>脚本提示</b> - 鼠标悬停时显示脚本功能说明</li>
            <li><b>配置导入/导出</b> - 备份和共享您的脚本集合</li>
            <li><b>文件夹管理</b> - 可在tool文件夹下添加文件夹，然后放入对应脚本，然后回maya点刷新</li>
        </ul>
        
        <h2>基础操作</h2>
        <h3>脚本管理</h3>
        <ul>
            <li><b>创建脚本</b>：点击顶部工具栏中的"新建脚本"按钮</li>
            <li><b>运行脚本</b>：点击脚本按钮</li>
            <li><b>编辑脚本</b>：右键点击脚本按钮，选择"编辑脚本"</li>
            <li><b>删除脚本</b>：右键点击脚本按钮，选择"删除"</li>
            <li><b>修改提示信息</b>：右键点击脚本按钮，选择"编辑提示信息"</li>
        </ul>
        
        <h3>分组操作</h3>
        <ul>
            <li><b>创建分组</b>：点击左侧导航栏底部的"+"按钮</li>
            <li><b>重命名分组</b>：右键点击左侧导航栏中的分组按钮，选择"重命名"</li>
            <li><b>删除分组</b>：右键点击左侧导航栏中的分组按钮，选择"删除"</li>
            <li><b>移动脚本</b>：右键点击脚本按钮，选择"移动到分组"→选择目标分组</li>
        </ul>
        
        <h3>导入与导出</h3>
        <ul>
            <li><b>导入脚本</b>：直接将.py或.mel文件拖放到窗口中</li>
            <li><b>导出配置</b>：点击顶部"设置"按钮，选择"导出配置"</li>
            <li><b>导入配置</b>：点击顶部"设置"按钮，选择"导入配置"</li>
        </ul>
        
        <div class="note">
            <p><span class="highlight">提示：</span>您可以在脚本中添加注释来提供提示信息，格式如下：</p>
            <p>Python: <span class="tip"># 提示: 这是脚本的功能说明</span></p>
            <p>MEL: <span class="tip">// 提示: 这是脚本的功能说明</span></p>
        </div>
        
        <h2>高级功能</h2>
        <h3>回收站操作</h3>
        <ul>
            <li><b>查看回收站</b>：点击左侧导航栏底部的"回收站"按钮</li>
            <li><b>恢复脚本</b>：在回收站中点击脚本卡片上的"恢复"按钮</li>
            <li><b>永久删除</b>：在回收站中点击脚本卡片上的"删除"按钮</li>
            <li><b>清空回收站</b>：在回收站顶部点击"清空回收站"按钮</li>
        </ul>
        
        <h3>错误处理与调试</h3>
        <ul>
            <li>运行脚本报错会在Maya的脚本编辑器中显示详细错误信息</li>
            <li>找不到脚本文件时会自动在所有分组中搜索</li>
            <li>支持自动修复工具文件路径问题</li>
        </ul>
        
        <h2>常见问题</h2>
        <ul>
            <li><b>无法运行脚本</b>：检查脚本语法是否正确，Maya版本是否兼容</li>
            <li><b>脚本丢失</b>：检查回收站，或检查电脑中是否有备份</li>
            <li><b>无法导入配置</b>：确保导入的配置文件格式正确，且包含必要的工具目录结构</li>
        </ul>
        
        <div class="section">
            <p style="margin-top: 20px;"><b>作者信息:</b></p>
            <p>如有问题或建议，请通过以下方式联系作者:</p>
            <p><a href="https://space.bilibili.com/431406403">哔哩哔哩主页</a></p>
        </div>
        """
        
        text_browser.setHtml(help_html)
        
        # 创建底部按钮区域
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(10)
        
        # 添加版本信息
        version_info = get_version_info()
        version_label = QLabel(f"Maya版本: {version_info['maya_version']}, Qt版本: {version_info['qt_version']}")
        version_label.setStyleSheet("color: #999999; font-style: italic;")
        button_layout.addWidget(version_label)
        
        button_layout.addStretch(1)
        
        # 创建按钮
        open_link_btn = QPushButton("访问B站主页")
        open_link_btn.setIcon(self.style().standardIcon(QStyle.SP_DriveNetIcon))
        close_btn = QPushButton("关闭")
        close_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton))
        
        button_layout.addWidget(open_link_btn)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # 连接按钮事件
        open_link_btn.clicked.connect(lambda: self.open_external_url("https://space.bilibili.com/431406403"))
        close_btn.clicked.connect(help_dialog.accept)
        
        # 显示对话框
        help_dialog.exec_()
    
    def open_external_url(self, url):
        """打开外部URL链接"""
        try:
            if qt_version == "PySide6":
                from PySide6.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl(url))
            elif qt_version == "PySide2":
                from PySide2.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl(url))
            elif qt_version == "PyQt5":
                from PyQt5.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl(url))
            else:
                # 对于旧版Qt
                QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            cmds.warning(f"打开链接失败: {str(e)}")
            
    def extract_tooltip_from_content(self, content, script_type):
        """从文件内容中提取提示信息"""
        # 尝试查找注释中的提示信息
        if script_type == "python":
            # 查找Python文件中的提示信息
            tooltip_patterns = [
                r'#\s*提示[:：]\s*(.+)',
                r'#\s*说明[:：]\s*(.+)',
                r'#\s*tooltip[:：]\s*(.+)',
                r'#\s*description[:：]\s*(.+)'
            ]
        else:
            # 查找MEL文件中的提示信息
            tooltip_patterns = [
                r'//\s*提示[:：]\s*(.+)',
                r'//\s*说明[:：]\s*(.+)',
                r'//\s*tooltip[:：]\s*(.+)',
                r'//\s*description[:：]\s*(.+)'
            ]
        
        # 尝试每个模式
        for pattern in tooltip_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # 如果没有找到提示，尝试提取多行注释作为提示
        if script_type == "python":
            # 尝试提取Python多行注释
            docstring_pattern = r'"""(.*?)"""'
            match = re.search(docstring_pattern, content, re.DOTALL)
            if match:
                # 将多行注释转换为单行
                docstring = match.group(1).strip()
                # 如果多行注释太长，截断它
                if len(docstring) > 200:
                    docstring = docstring[:197] + "..."
                return docstring
        
        # 如果没有找到任何提示，返回None
        return None

# 全局变量，存储当前活动的脚本管理器窗口
scripts_box_dialog = None

# 创建启动函数
def show_scripts_box():
    global scripts_box_dialog
    
    try:
        # 尝试安全关闭之前的实例
        if scripts_box_dialog is not None:
            try:
                if scripts_box_dialog.isVisible():
                    # 如果窗口仍然可见，则尝试正常关闭
                    scripts_box_dialog.close()
                    
                # 尝试删除旧窗口
                scripts_box_dialog.deleteLater()
            except:
                # 如果无法关闭，只需记录警告
                pass
    except:
        pass
    
    try:
        # 输出版本信息
        version_info = get_version_info()
        print("Maya脚本管理器启动中...")
        print(f"版本信息: {version_info}")
        
        # 创建新实例
        scripts_box_dialog = ScriptsBox()
        
        # 在Maya 2025中，特殊处理窗口显示
        if MAYA_VERSION >= 2025:
            # 使用显式的show()调用而不是exec_()
            scripts_box_dialog.show()
            
            # 确保窗口在前台显示
            scripts_box_dialog.raise_()
            scripts_box_dialog.activateWindow()
        else:
            # 其他版本正常显示
            scripts_box_dialog.show()
        
        return scripts_box_dialog
    except Exception as e:
        error_msg = traceback.format_exc()
        cmds.warning(f"启动脚本管理器失败: {str(e)}\n{error_msg}")
        return None

# 安全关闭函数 - 可以从外部调用
def close_scripts_box():
    global scripts_box_dialog
    
    try:
        if scripts_box_dialog is not None:
            # 尝试正常关闭
            scripts_box_dialog.close()
            scripts_box_dialog.deleteLater()
            scripts_box_dialog = None
            return True
    except Exception as e:
        cmds.warning(f"关闭脚本管理器失败: {str(e)}")
    
    return False

# 当直接运行此脚本时启动
if __name__ == "__main__":
    show_scripts_box()