import maya.cmds as cmds

from pathlib import Path
import shutil

from ..GN_source import GN_Print


def GN_ImportExportCleanup():
    # Confirm dialog
    confirm = cmds.confirmDialog(t="Cleanup confirmation", b=["OK", "Cancel"], m="Press OK to clean cache.", db="OK", cb="Cancel", ds="Closed by user")
    if confirm != "OK":
        return
    
    # Check that directory exist
    directory = Path("C:/temp")
    if not directory.is_dir():
        return
    
    # Loop files
    files = directory.iterdir()
    for file in files:
        if file.stem == "exported":
            # Remove exported files
            if file.is_file():
                file.unlink()
            # Remove exported folder
            elif file.is_dir():
                shutil.rmtree(file, ignore_errors=True)
    
    # Remove temp folder if empty
    if not any (directory.iterdir()):
        directory.rmdir()
    
    # Print result
    GN_Print.GN_Print(f"# Result: Deleted all files exported in {directory.as_posix()}")