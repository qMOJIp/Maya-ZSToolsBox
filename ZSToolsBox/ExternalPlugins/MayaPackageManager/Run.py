import importlib.util
import sys
import os

ver = f"{sys.version_info[0]}{sys.version_info[1]}"
pyc_path = "@ReplaceMe@ExternalPlugins/MayaPackageManager/src/mpm_py"+str(ver)+".pyc"
try:
    if not os.path.exists(pyc_path):
        raise FileNotFoundError(f"文件不存在: {pyc_path}")

    spec = importlib.util.spec_from_file_location("module_name", pyc_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.show_manager()

except FileNotFoundError as e:
    cmds.warning(f"错误: {e}")
except Exception as e:
    cmds.warning(f"加载模块时发生错误: {e}")
