from sys import stdout
import maya.cmds as cmds
import maya.api.OpenMaya as om


def GN_Eval(msg="", mode='PRINT', deferred=False):
    if deferred is False:
        if mode == 'PRINT':
            stdout.write(f'{msg}\n')
        elif mode == 'INFO':
            om.MGlobal.displayInfo(msg)
        elif mode == 'WARNING':
            om.MGlobal.displayWarning(msg)
        elif mode == 'ERROR':
            om.MGlobal.displayError(msg)
    else:
        msg = msg.replace("\\", "\\\\")
        if mode == 'PRINT':
            cmds.evalDeferred(fr'from sys import stdout; stdout.write("{msg}\n")')
        elif mode == 'INFO':
            cmds.evalDeferred(f'import maya.api.OpenMaya as om; om.MGlobal.displayInfo("{msg}")')
        elif mode == 'WARNING':
            cmds.evalDeferred(f'import maya.api.OpenMaya as om; om.MGlobal.displayWarning("{msg}")')
        elif mode == 'ERROR':
            cmds.evalDeferred(f'import maya.api.OpenMaya as om; om.MGlobal.displayError("{msg}")')


def GN_Print(msg="", mode='PRINT', deferred=False):
    if isinstance(msg, list):
        for i in msg:
            GN_Eval(i, mode, deferred)
    elif isinstance(msg, str):
        GN_Eval(msg, mode, deferred)


# VERSION 2
'''
import maya.cmds as cmds
import maya.mel as mel

def GN_Eval(msg, deferred=False):
	if deferred is False:
		mel.eval(msg)
	else:
		cmds.evalDeferred(fr"import maya.mel as mel; mel.eval(r'{msg}')")

def GN_Print(obj, deferred=False):
    if type(obj) is not list:
        msg = fr"print('{obj}\n')"
        GN_Eval(msg, deferred)
    else:
        for i in range(len(obj)):
            msg = fr"print('{obj[i]}\n')"
            GN_Eval(msg, deferred)
'''


# VERSION 1
'''
import maya.mel as mel

def GN_Print(msg):
    if not isinstance(msg, list):
        mel.eval(fr"print('{msg}\n')")
    else:
        for i in range(len(msg)):
            mel.eval(fr"print('{msg[i]}\n')")
'''


# Builtin override
'''
from __future__ import print_function
import sys
import builtins



def print(*args, **kwargs):
    sep, end = kwargs.pop('sep', ' '), kwargs.pop('end', '\n')
    file, flush = kwargs.pop('file', sys.stdout), kwargs.pop('flush', False)
    if kwargs:
        raise TypeError(f'print() got an unexpected keyword argument {next(iter(kwargs))}')
    builtins.print(*args, sep=sep, end=end, file=file)
    if flush:
        file.flush()
'''