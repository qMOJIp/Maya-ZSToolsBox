import sys
sys.dont_write_bytecode = True
import os
import importlib.util

def onMayaDroppedPythonFile(*args):
    script_path = os.path.realpath(__file__)
    script_dir = os.path.dirname(script_path)

    ver = f"{sys.version_info[0]}{sys.version_info[1]}"

    pyc_path = os.path.join(script_dir, "src", f"mpm_py{ver}.pyc")

    spec = importlib.util.spec_from_file_location("module_name", pyc_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.show_manager()

    cache_dir = os.path.join(script_dir, "__pycache__")
    if os.path.exists(cache_dir):
        import shutil
        shutil.rmtree(cache_dir)
