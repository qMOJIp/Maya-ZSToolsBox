"""
拖放这个文件到Maya视口中以安装脚本工具箱
Drag and drop this file into the Maya viewport to install Scripts Box

确保'icons'文件夹与此脚本位于同一目录中，其中包含'scripts box.jpg'图标文件。
"""

import maya.cmds as cmds
import sys
import os
import shutil
from importlib import import_module, reload


def find_file_in_directory(directory, filename):
    """
    在指定目录中查找指定文件名的文件。
    增强了错误处理能力。
    """
    try:
        directory = os.path.normpath(directory)
        if not os.path.exists(directory):
            print(f"警告: 目录不存在: {directory}")
            return None

        if not os.path.isdir(directory):
            print(f"警告: 不是一个目录: {directory}")
            return None

        for root, dirs, files in os.walk(directory):
            if filename in files:
                file_path = os.path.normpath(os.path.join(root, filename))
                print(f"找到文件: {file_path}")
                return file_path

        print(f"在 {directory} 中未找到 {filename}")
        return None
    except Exception as e:
        print(f"搜索文件时出错: {e}")
        return None


def add_to_shelf(module_path):
    """将工具按钮添加到Maya工具架，使用动态导入"""
    try:
        current_shelf = cmds.tabLayout("ShelfLayout", query=True, selectTab=True)
        if not current_shelf:
            raise ValueError("未找到活动工具架")

        # 图标路径 - 直接使用icons目录中的图标
        installer_dir = os.path.dirname(__file__)
        icon_path = os.path.join(installer_dir, "icons", "scripts box.jpg")

        # 如果图标不存在，使用Maya默认图标
        if not os.path.exists(icon_path):
            icon_path = "menuIconHelp.png"
            print("未找到自定义图标，将使用Maya默认图标")
        else:
            print(f"使用图标: {icon_path}")

        # 模块名称和目录
        module_name = "scripts_box"
        script_dir = os.path.dirname(module_path).replace("\\", "\\\\")
        icons_dir = os.path.join(installer_dir, "icons").replace("\\", "\\\\")

        # 创建命令脚本，确保图标路径是可访问的
        command_script = f'''import maya.cmds as cmds
import sys
import os
from importlib import import_module, reload

# 添加脚本目录到路径
script_dir = r"{script_dir}"
if script_dir not in sys.path:
    sys.path.append(script_dir)

# 确保可以找到图标目录
icons_dir = r"{icons_dir}"
icon_path = os.path.join(icons_dir, "scripts box.jpg")

# 检查图标是否存在
if not os.path.exists(icon_path):
    print(f"警告: 图标文件不存在: {{icon_path}}")
    
# 设置环境变量以便脚本可以找到图标
os.environ["SCRIPTS_BOX_ICONS_DIR"] = icons_dir

# 删除声明提示，因为用户在安装时已经同意
# 设置环境变量永久记住用户已同意
os.environ["SCRIPTS_BOX_SHOWED_DISCLAIMER"] = "1" 

try:
    module = import_module("{module_name}")
    reload(module)
    module.show_scripts_box()
except ImportError as e:
    cmds.error(f"导入模块失败: {{e}}")
except AttributeError as e:
    cmds.error(f"运行工具失败: {{e}}")
'''

        # 添加工具架按钮
        # 为了确保每次启动Maya都能找到图标，使用绝对路径
        # 注意：Maya每次启动时都会重新载入工具架，所以需要保证路径始终有效
        cmds.shelfButton(
            annotation="脚本工具箱",
            label="Scripts_Box",
            image1=icon_path,  # 安装时使用的图标路径
            image=icon_path,   # 备用图标路径
            command=command_script,
            sourceType="python",
            style="iconOnly",
            width=35,
            height=35,
            parent=current_shelf
        )
        print(f"成功将 '脚本工具箱' 添加到工具架: {current_shelf}")
        return True
    except Exception as e:
        cmds.warning(f"添加到工具架失败: {e}")
        return False


def create_installer_gui():
    """创建安装器GUI界面"""
    # 窗口尺寸和标题
    window_width = 450
    window_height = 350

    # 如果窗口已存在则删除
    if cmds.window("scriptsBoxInstallerWindow", exists=True):
        cmds.deleteUI("scriptsBoxInstallerWindow")

    # 创建主窗口
    window = cmds.window("scriptsBoxInstallerWindow", title="脚本工具箱安装向导",
                         width=window_width, height=window_height, sizeable=False,
                         backgroundColor=[0.2, 0.2, 0.2])

    # 主布局
    main_layout = cmds.columnLayout(adjustableColumn=True, columnOffset=["both", 15],
                                   rowSpacing=10, columnAttach=["both", 15])

    # 标题区域
    cmds.separator(height=10, style="none")
    cmds.text(label="脚本工具箱安装向导", font="boldLabelFont", height=40, backgroundColor=[0.2, 0.3, 0.4])
    cmds.separator(height=1, style="in")
    cmds.separator(height=10, style="none")

    # 图标区域
    icon_img = 'menuIconHelp.png'
    # 尝试使用自定义图标 - 直接使用原始路径
    custom_icon = os.path.join(os.path.dirname(__file__), "icons", "scripts box.jpg")
    if os.path.exists(custom_icon):
        icon_img = custom_icon
        print(f"安装向导使用图标: {icon_img}")
    else:
        print("未找到自定义图标，安装向导将使用Maya默认图标")

    icon_placeholder = cmds.iconTextStaticLabel(style='iconOnly',
                                              image1=icon_img,
                                              width=64, height=64)

    # 信息区域
    cmds.separator(height=10, style="none")
    cmds.text(label="欢迎使用脚本工具箱安装向导！", align="center", font="boldLabelFont")
    cmds.text(label="此工具为免费分享工具，由作者提供，请勿倒卖！", align="center", font="boldLabelFont", backgroundColor=[0.5, 0.0, 0.0])
    cmds.separator(height=10, style="none")

    # 说明文本区域
    cmds.frameLayout(label="安装说明", collapsable=False,
                    marginWidth=5, marginHeight=5, width=window_width-30)
    cmds.columnLayout(adjustableColumn=True, columnOffset=["both", 5], rowSpacing=5)
    cmds.text(label="• 本安装向导将帮助您安装脚本工具箱到Maya当前活动的工具架中", align="left", wordWrap=True)
    cmds.text(label="• 您需要选择包含scripts_box.py的文件夹", align="left", wordWrap=True)
    cmds.text(label="• 安装完成后，您可以直接从Maya工具架访问该工具", align="left", wordWrap=True)
    cmds.text(label="• 工具箱支持拖放添加Python和MEL脚本", align="left", wordWrap=True)
    cmds.setParent('..')
    cmds.setParent('..')

    # 文件夹选择区域
    cmds.frameLayout(label="文件选择", collapsable=False,
                    marginWidth=5, marginHeight=5, width=window_width-30)
    cmds.columnLayout(adjustableColumn=True, columnOffset=["both", 5], rowSpacing=5)

    # 文件夹路径显示
    folder_text = cmds.textFieldButtonGrp(
        label="工具文件夹: ",
        buttonLabel="浏览...",
        columnWidth=[(1, 80), (2, 230), (3, 60)],
        adjustableColumn=2,
        buttonCommand=lambda: browse_folder(folder_text)
    )

    # 状态信息
    file_status = cmds.text(label="请选择包含scripts_box.py文件的文件夹", align="left")
    cmds.setParent('..')
    cmds.setParent('..')

    # 状态区域
    cmds.separator(height=10, style="none")
    status_text = cmds.text(label="准备就绪，请选择文件夹后点击\"安装\"按钮", align="center")
    cmds.separator(height=15, style="none")

    # 按钮区域
    cmds.separator(height=1, style="in")
    button_row = cmds.rowLayout(numberOfColumns=2, columnWidth2=[window_width/2-20, window_width/2-20],
                              columnAlign2=["center", "center"], columnAttach=[(1, "both", 10), (2, "both", 10)])

    # 安装按钮
    install_btn = cmds.button(label="安装", width=window_width/2-20, height=35,
                             backgroundColor=[0.2, 0.4, 0.6],
                             command=lambda x: install_with_feedback(folder_text, file_status, status_text))

    # 取消按钮
    cancel_btn = cmds.button(label="取消", width=window_width/2-20, height=35,
                            command=lambda x: cmds.deleteUI(window))

    # 版权信息
    cmds.setParent(main_layout)
    cmds.separator(height=10, style="none")
    current_year = cmds.about(currentTime=True)
    year_str = str(current_year).split("-")[0] if "-" in str(current_year) else "2025"
    cmds.text(label="Scripts Box © " + year_str, align="center", font="smallFixedWidthFont")

    # 显示窗口
    cmds.showWindow(window)

    # 浏览文件夹函数
    def browse_folder(text_field):
        folder = cmds.fileDialog2(caption="选择包含scripts_box.py的文件夹", fileMode=3, okCaption="选择")
        if folder and len(folder) > 0:
            cmds.textFieldButtonGrp(text_field, edit=True, text=folder[0])
            validate_folder(folder[0], file_status)

    # 验证选择的文件夹是否包含必要文件
    def validate_folder(folder_path, status_field):
        if not folder_path:
            cmds.text(status_field, edit=True, label="请选择文件夹", backgroundColor=[0.5, 0.0, 0.0])
            return False

        # 检查文件夹是否存在
        if not os.path.exists(folder_path):
            cmds.text(status_field, edit=True, label=f"错误: 文件夹不存在: {folder_path}", backgroundColor=[0.5, 0.0, 0.0])
            return False

        # 查找工具文件
        script_path = find_file_in_directory(folder_path, "scripts_box.py")

        if not script_path:
            cmds.text(status_field, edit=True, label="错误: 未找到scripts_box.py文件", backgroundColor=[0.5, 0.0, 0.0])
            return False

        # 尝试验证文件是否可读
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                # 只读取前几行来验证文件可读
                first_lines = ''.join([f.readline() for _ in range(5)])
                if '# -*-' not in first_lines and 'import' not in first_lines:
                    cmds.text(status_field, edit=True, label="警告: 文件内容可能不是有效的Python脚本", backgroundColor=[0.5, 0.3, 0.0])
                    # 仍然继续，因为这只是一个警告
        except UnicodeDecodeError:
            try:
                # 尝试其他编码
                with open(script_path, 'r', encoding='gbk') as f:
                    first_lines = ''.join([f.readline() for _ in range(5)])
            except Exception as e:
                cmds.text(status_field, edit=True, label=f"警告: 文件可能存在编码问题", backgroundColor=[0.5, 0.3, 0.0])
                print(f"文件编码问题: {e}")
                # 仍然继续，因为这只是一个警告
        except Exception as e:
            cmds.text(status_field, edit=True, label="警告: 文件读取问题，但仍将尝试安装", backgroundColor=[0.5, 0.3, 0.0])
            print(f"文件读取问题: {e}")
            # 仍然继续，因为这只是一个警告

        # 文件找到了
        cmds.text(status_field, edit=True, label="文件验证成功，可以安装", backgroundColor=[0.0, 0.3, 0.0])
        return True

    # 创建工具文件夹结构函数
    def create_tool_structure(source_dir, script_path):
        try:
            print(f"开始创建工具结构，源目录: {source_dir}")

            # 确保tool文件夹存在
            tool_dir = os.path.join(source_dir, "tool")
            if not os.path.exists(tool_dir):
                try:
                    os.makedirs(tool_dir)
                    print(f"创建tool目录: {tool_dir}")
                except Exception as e:
                    print(f"创建tool目录失败: {e}")
                    # 尝试使用其他方法创建目录
                    try:
                        os.mkdir(tool_dir)
                        print("使用mkdir成功创建tool目录")
                    except Exception as e2:
                        print(f"使用mkdir创建目录也失败: {e2}")
                        raise

            # 创建配置文件（如果不存在）
            config_path = os.path.join(source_dir, "config.json")
            if not os.path.exists(config_path):
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        f.write('{\n    "tools": []\n}')
                    print(f"创建配置文件: {config_path}")
                except Exception as e:
                    print(f"创建配置文件失败: {e}")
                    # 不抛出异常，因为这不是致命错误

            # 验证图标是否存在并可访问
            installer_dir = os.path.dirname(__file__)
            source_icon = os.path.join(installer_dir, "icons", "scripts box.jpg")
            if os.path.exists(source_icon):
                print(f"图标文件验证成功: {source_icon}")
            else:
                print("未找到图标文件，将使用Maya默认图标")

            return True
        except Exception as e:
            print(f"创建文件结构失败: {e}")
            return False

    # 安装逻辑函数
    def install_with_feedback(folder_field, file_status_field, status_label):
        try:
            # 先显示声明确认对话框
            agreement_result = cmds.confirmDialog(
                title="使用条款确认",
                message="此工具为免费分享工具，由作者提供，请勿倒卖。\n继续安装表示您同意此条款。",
                button=["同意并继续", "取消"],
                defaultButton="同意并继续",
                cancelButton="取消",
                dismissString="取消",
                icon="warning"
            )

            # 如果用户取消，则停止安装
            if agreement_result != "同意并继续":
                cmds.text(status_label, edit=True, label="安装已取消", backgroundColor=[0.3, 0.3, 0.3])
                return

            # 获取用户选择的文件夹路径
            folder_path = cmds.textFieldButtonGrp(folder_field, query=True, text=True)

            # 验证文件夹
            if not validate_folder(folder_path, file_status_field):
                cmds.text(status_label, edit=True, label="安装失败: 文件验证未通过", backgroundColor=[0.5, 0.0, 0.0])
                return

            # 更新状态
            cmds.text(status_label, edit=True, label="正在安装中...", backgroundColor=[0.3, 0.3, 0.0])

            # 查找脚本文件
            script_path = find_file_in_directory(folder_path, "scripts_box.py")

            # 创建必要的目录结构
            if not create_tool_structure(os.path.dirname(script_path), script_path):
                cmds.text(status_label, edit=True, label="创建目录结构失败", backgroundColor=[0.5, 0.0, 0.0])
                return

            # 将脚本路径添加到sys.path
            script_dir = os.path.dirname(script_path)
            if script_dir not in sys.path:
                sys.path.append(script_dir)

            # 添加到工具架
            if add_to_shelf(script_path):
                # 显示成功信息
                cmds.confirmDialog(title="安装成功",
                                  message="脚本工具箱已成功添加到当前工具架！\n现在可以直接从工具架启动该工具。",
                                  button=["确定"], defaultButton="确定", icon="information")

                # 更新状态
                cmds.text(status_label, edit=True, label="安装成功！", backgroundColor=[0.0, 0.3, 0.0])

                # 延时关闭窗口
                cmds.evalDeferred(lambda: close_window_delayed(window), lowestPriority=True)
            else:
                cmds.text(status_label, edit=True, label="添加到工具架失败", backgroundColor=[0.5, 0.0, 0.0])
                raise RuntimeError("添加到工具架失败")

        except Exception as e:
            cmds.text(status_label, edit=True, label=f"安装失败: {e}", backgroundColor=[0.5, 0.0, 0.0])
            cmds.confirmDialog(title="安装错误", message=f"安装过程中发生错误: {e}",
                              button=["确定"], defaultButton="确定", icon="critical")
            cmds.error(f"安装过程中发生错误: {e}")

    # 延时关闭窗口函数
    def close_window_delayed(win):
        # 等待2秒后关闭窗口
        cmds.pause(seconds=2)
        if cmds.window(win, exists=True):
            cmds.deleteUI(win)


def onMayaDroppedPythonFile(*args):
    """
    当脚本被拖入 Maya 的视口时执行的函数。
    这是 Maya 拖放机制的入口点，名称不可更改。
    """
    # 检查 Python 版本
    if sys.version_info.major < 3:
        user_version = "{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
        error = "不兼容的Python版本。需要Python 3及以上版本。当前版本: " + user_version
        raise ImportError(error)

    # 初始反馈
    print("_" * 50)
    print("正在初始化脚本工具箱安装向导...")

    # 获取拖放位置并添加到 sys.path
    parent_dir = os.path.dirname(__file__)
    print('拖放位置: "' + parent_dir + '"')
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    # 启动安装器GUI
    print("启动安装向导界面...")
    create_installer_gui()
    print("_" * 50)


# 创建图标函数
def create_default_icon():
    """检查自定义图标是否存在"""
    try:
        # 检查是否有自定义图标
        installer_dir = os.path.dirname(__file__)
        source_icon = os.path.join(installer_dir, "icons", "scripts box.jpg")

        if os.path.exists(source_icon):
            print(f"找到自定义图标: {source_icon}")
            return True
        else:
            print("未找到自定义图标，将使用Maya默认图标")
            return False
    except Exception as e:
        print(f"检查图标时出错: {e}")
        return False


# 如果脚本直接运行（不是通过拖放）
if __name__ == "__main__":
    create_default_icon()  # 尝试创建默认图标
    create_installer_gui()