# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide2 import QtWidgets, QtCore
from shiboken2 import wrapInstance
import maya.OpenMaya as om
import sys

# 全局变量（保持原有）
bone_group_mapping = {}
SCRIPT_JOB_ID = -1
WINDOW_INSTANCE = None

def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QMainWindow)

class BoneCtrlCreatorUI(QtWidgets.QDialog):
    def __init__(self, parent=maya_main_window()):
        super(BoneCtrlCreatorUI, self).__init__(parent)
        global WINDOW_INSTANCE
        WINDOW_INSTANCE = self
        
        # 修复中文显示（保持）
        QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.Chinese))
        self.setObjectName("BoneCtrlCreatorWin")
        self.setWindowTitle("骨骼控制器生成工具（自定义前缀）")
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowMinimizeButtonHint | QtCore.Qt.WindowCloseButtonHint)
        self.setMinimumSize(480, 550)
        self.setStyleSheet("""
            QDialog {
                background-color: #e0e0e0; 
                color: #000000;
                font-family: "Microsoft YaHei", "SimHei", "Arial Unicode MS", sans-serif;
            }
            QGroupBox {
                font-weight: bold; 
                color: #000000;
                margin-top: 15px; 
                padding: 12px; 
                border: 1px solid #ccc; 
                border-radius: 5px;
                font-family: "Microsoft YaHei", "SimHei", "Arial Unicode MS", sans-serif;
            }
            QPushButton {
                background-color: #4a86e8; 
                color: white; 
                border: none; 
                padding: 10px 20px; 
                border-radius: 4px;
                font-size: 14px;
                font-family: "Microsoft YaHei", "SimHei", "Arial Unicode MS", sans-serif;
            }
            QPushButton:hover {background-color: #3a76d8;}
            QLabel {
                color: #000000; 
                font-size: 13px;
                font-family: "Microsoft YaHei", "SimHei", "Arial Unicode MS", sans-serif;
            }
            QCheckBox {
                color: #666666;
                margin: 4px 0;
                font-size: 13px;
                font-family: "Microsoft YaHei", "SimHei", "Arial Unicode MS", sans-serif;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f5f5f5;
            }
            QCheckBox::indicator:checked {
                background-color: #4a86e8;
                image: url(:/qt-project.org/styles/commonstyle/images/checkbox_checked.png);
            }
            QComboBox {
                color: #666666;
                padding: 6px; 
                border: 1px solid #ccc; 
                border-radius: 4px;
                background-color: #f5f5f5;
                font-size: 13px;
                font-family: "Microsoft YaHei", "SimHei", "Arial Unicode MS", sans-serif;
            }
            QComboBox::drop-down {border: none;}
            QComboBox::down-arrow {
                image: url(:/qt-project.org/styles/commonstyle/images/down_arrow.png);
                width: 10px;
                height: 10px;
            }
            QComboBox QAbstractItemView {
                color: #666666;
                background-color: #f5f5f5;
                selection-background-color: #4a86e8;
                selection-color: white;
                border: 1px solid #ccc;
                outline: none;
                font-family: "Microsoft YaHei", "SimHei", "Arial Unicode MS", sans-serif;
            }
        """)
        
        self.create_ui()
        self.init_signals()
        self.update_selection()

    def create_ui(self):
        # 保持原有UI布局，无修改
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(18)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        title_label = QtWidgets.QLabel("骨骼控制器批量生成（支持自定义前缀）")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 17px; font-weight: bold; color: #2a5699; margin-bottom: 5px;")
        main_layout.addWidget(title_label)
        
        layer_group = QtWidgets.QGroupBox("控制器组层数选择")
        layer_layout = QtWidgets.QHBoxLayout(layer_group)
        layer_layout.setSpacing(15)
        layer_label = QtWidgets.QLabel("选择层数：")
        self.layer_combo = QtWidgets.QComboBox()
        self.layer_combo.addItems([
            "3层（前缀1 + 前缀2 + 控制器）",
            "4层（前缀1 + 前缀2 + 前缀3 + 控制器）"
        ])
        self.layer_combo.setCurrentIndex(0)
        self.layer_combo.setMinimumWidth(280)
        layer_layout.addWidget(layer_label)
        layer_layout.addWidget(self.layer_combo)
        main_layout.addWidget(layer_group)
        
        prefix_group = QtWidgets.QGroupBox("层级前缀自定义（前缀+骨骼名）")
        prefix_layout = QtWidgets.QGridLayout(prefix_group)
        prefix_layout.setHorizontalSpacing(12)
        prefix_layout.setVerticalSpacing(15)
        
        self.prefix1_label = QtWidgets.QLabel("第1层前缀：")
        self.prefix1_edit = QtWidgets.QLineEdit("FKOffset")
        self.prefix1_edit.setMinimumWidth(200)
        prefix_layout.addWidget(self.prefix1_label, 0, 0, alignment=QtCore.Qt.AlignRight)
        prefix_layout.addWidget(self.prefix1_edit, 0, 1)
        
        self.prefix2_label = QtWidgets.QLabel("第2层前缀：")
        self.prefix2_edit = QtWidgets.QLineEdit("FKExtra")
        prefix_layout.addWidget(self.prefix2_label, 1, 0, alignment=QtCore.Qt.AlignRight)
        prefix_layout.addWidget(self.prefix2_edit, 1, 1)
        
        self.prefix3_label = QtWidgets.QLabel("第3层前缀：")
        self.prefix3_edit = QtWidgets.QLineEdit("FK")
        prefix_layout.addWidget(self.prefix3_label, 2, 0, alignment=QtCore.Qt.AlignRight)
        prefix_layout.addWidget(self.prefix3_edit, 2, 1)
        
        self.ctrl_suffix_label = QtWidgets.QLabel("控制器后缀：")
        self.ctrl_suffix_edit = QtWidgets.QLineEdit("Ctrl")
        self.ctrl_note = QtWidgets.QLabel("（控制器名：骨骼名+后缀）")
        self.ctrl_note.setStyleSheet("font-size: 11px; color: #666;")
        prefix_layout.addWidget(self.ctrl_suffix_label, 3, 0, alignment=QtCore.Qt.AlignRight)
        prefix_layout.addWidget(self.ctrl_suffix_edit, 3, 1)
        prefix_layout.addWidget(self.ctrl_note, 3, 2)
        
        main_layout.addWidget(prefix_group)
        
        constraint_group = QtWidgets.QGroupBox("约束类型选择（最少选一种）")
        constraint_layout = QtWidgets.QVBoxLayout(constraint_group)
        constraint_layout.setSpacing(8)
        self.parent_check = QtWidgets.QCheckBox("父子约束（Parent）- 控制位置/旋转")
        self.parent_check.setChecked(True)
        self.point_check = QtWidgets.QCheckBox("点约束（Point）- 仅控制位置")
        self.orient_check = QtWidgets.QCheckBox("方向约束（Orient）- 仅控制旋转")
        self.scale_check = QtWidgets.QCheckBox("比例约束（Scale）- 控制缩放")
        self.scale_check.setChecked(True)
        self.aim_check = QtWidgets.QCheckBox("目标约束（Aim）- 控制朝向目标")
        constraint_layout.addWidget(self.parent_check)
        constraint_layout.addWidget(self.point_check)
        constraint_layout.addWidget(self.orient_check)
        constraint_layout.addWidget(self.scale_check)
        constraint_layout.addWidget(self.aim_check)
        main_layout.addWidget(constraint_group)
        
        btn_status_layout = QtWidgets.QVBoxLayout()
        btn_status_layout.setSpacing(12)
        
        btn_container = QtWidgets.QHBoxLayout()
        btn_container.setSpacing(30)
        btn_container.setAlignment(QtCore.Qt.AlignCenter)
        
        self.create_selected_btn = QtWidgets.QPushButton("生成选中对象")
        self.create_selected_btn.setMinimumHeight(40)
        self.create_selected_btn.setMinimumWidth(160)
        
        self.create_hierarchy_btn = QtWidgets.QPushButton("生成层级所有")
        self.create_hierarchy_btn.setMinimumHeight(40)
        self.create_hierarchy_btn.setMinimumWidth(160)
        
        btn_container.addWidget(self.create_selected_btn)
        btn_container.addWidget(self.create_hierarchy_btn)
        
        self.status_label = QtWidgets.QLabel("状态：未生成 | 选中骨骼：0个 | 命名规则：前缀+骨骼名（默认FKOffset/FKExtra/FK）")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        
        btn_status_layout.addLayout(btn_container)
        btn_status_layout.addWidget(self.status_label)
        main_layout.addLayout(btn_status_layout)

    def init_signals(self):
        self.create_selected_btn.clicked.connect(self.on_create_selected_only)
        self.create_hierarchy_btn.clicked.connect(self.on_create_hierarchy)
        QtCore.QTimer.singleShot(500, self.init_selection_listener)

    def get_unique_name(self, base_name):
        if not cmds.objExists(base_name):
            return base_name
        index = 1
        while cmds.objExists(f"{base_name}{index}"):
            index += 1
        return f"{base_name}{index}"

    def get_selected_bone_hierarchy(self, selected_bones):
        hierarchy = []
        def traverse(joint):
            if joint not in hierarchy:
                hierarchy.append(joint)
            children = cmds.listRelatives(joint, children=True, type="joint") or []
            for child in children:
                traverse(child)
        for bone in selected_bones:
            traverse(bone)
        return hierarchy

    def create_ctrl_groups(self, bone, layer_count):
        """
        核心修复：控制器/组精准对齐骨骼位置，同时兼容Maya 2022
        """
        bone_short = cmds.ls(bone, shortNames=True)[0]
        ctrl_suffix = self.ctrl_suffix_edit.text().strip()
        
        # 收集前缀（保持原有）
        prefixes = []
        if layer_count == 3:
            prefix1 = self.prefix1_edit.text().strip()
            prefix2 = self.prefix2_edit.text().strip()
            if prefix1:
                prefixes.append(prefix1)
            if prefix2:
                prefixes.append(prefix2)
        elif layer_count == 4:
            prefix1 = self.prefix1_edit.text().strip()
            prefix2 = self.prefix2_edit.text().strip()
            prefix3 = self.prefix3_edit.text().strip()
            if prefix1:
                prefixes.append(prefix1)
            if prefix2:
                prefixes.append(prefix2)
            if prefix3:
                prefixes.append(prefix3)
        
        # 生成控制器名称（保持原有）
        ctrl_base = f"{bone_short}{ctrl_suffix}" if ctrl_suffix else bone_short
        ctrl_name = self.get_unique_name(ctrl_base)
        
        # ========== 修复1：先创建组，且组直接匹配骨骼位置 ==========
        groups = []
        for prefix in prefixes:
            grp_base = f"{prefix}{bone_short}"
            grp_name = self.get_unique_name(grp_base)
            grp = cmds.group(empty=True, name=grp_name)
            # 组创建后立即匹配骨骼位置（Maya 2022支持的基础matchTransform参数）
            cmds.matchTransform(grp, bone, pos=True, rot=True, scale=True)
            groups.append(grp)
        
        # ========== 修复2：控制器创建后精准匹配骨骼位置 ==========
        # 1. 创建控制器曲线
        ctrl_curve = cmds.circle(
            name=ctrl_name, 
            normal=[0, 1, 0], 
            radius=1, 
            constructionHistory=False
        )[0]
        # 2. 核心：直接匹配控制器到骨骼的位置/旋转/缩放（无多余参数，100%兼容）
        cmds.matchTransform(ctrl_curve, bone, pos=True, rot=True, scale=True)
        
        # 组层级父化（保持原有）
        for i in range(len(groups)-1):
            cmds.parent(groups[i+1], groups[i])
        if groups:
            # 父化控制器到组后，重置控制器的局部变换（避免父化导致偏移）
            cmds.parent(ctrl_curve, groups[-1])
            cmds.setAttr(f"{ctrl_curve}.translate", 0, 0, 0)
            cmds.setAttr(f"{ctrl_curve}.rotate", 0, 0, 0)
            cmds.setAttr(f"{ctrl_curve}.scale", 1, 1, 1)
        
        return (groups[0] if groups else None, 
                groups[-1] if groups else None, 
                ctrl_curve)

    def set_group_hierarchy(self, bone):
        # 保持原有逻辑
        parent_bones = cmds.listRelatives(bone, parent=True, type="joint")
        if not parent_bones:
            return
        parent_bone = parent_bones[0]
        
        if parent_bone not in bone_group_mapping:
            om.MGlobal.displayInfo(f"父骨骼{parent_bone}未在生成范围，{bone}控制器组保留在世界层级")
            return
        
        if bone not in bone_group_mapping:
            om.MGlobal.displayWarning(f"子骨骼{bone}未生成控制器，跳过层级父化")
            return
        
        parent_ctrl_curve = bone_group_mapping[parent_bone].get("ctrl_curve")
        current_outer_grp = bone_group_mapping[bone].get("outer_grp")
        
        if not parent_ctrl_curve or not current_outer_grp:
            om.MGlobal.displayWarning(f"{bone}的组或{parent_bone}的控制器不存在，跳过父化")
            return
        
        current_parent = cmds.listRelatives(current_outer_grp, parent=True) or []
        if current_parent == [parent_ctrl_curve]:
            return
        
        if current_parent and current_parent[0] != "world":
            cmds.parent(current_outer_grp, world=True)
        
        cmds.parent(current_outer_grp, parent_ctrl_curve)
        om.MGlobal.displayInfo(f"✅ 层级关系：{current_outer_grp} → {parent_ctrl_curve}")

    def create_constraints(self, bone, ctrl_curve):
        """
        保持约束逻辑：maintainOffset=True 避免骨骼参数突变
        """
        constraint_list = []
        bone_short = cmds.ls(bone, shortNames=True)[0]
        prefix1 = self.prefix1_edit.text().strip() or "Default"
        
        if self.parent_check.isChecked():
            const_name = self.get_unique_name(f"{bone_short}_{prefix1}ParentConstraint")
            parent_const = cmds.parentConstraint(ctrl_curve, bone, maintainOffset=True, name=const_name)
            constraint_list.append(parent_const[0])
        
        if self.point_check.isChecked():
            const_name = self.get_unique_name(f"{bone_short}_{prefix1}PointConstraint")
            point_const = cmds.pointConstraint(ctrl_curve, bone, maintainOffset=True, name=const_name)
            constraint_list.append(point_const[0])
        
        if self.orient_check.isChecked():
            const_name = self.get_unique_name(f"{bone_short}_{prefix1}OrientConstraint")
            orient_const = cmds.orientConstraint(ctrl_curve, bone, maintainOffset=True, name=const_name)
            constraint_list.append(orient_const[0])
        
        if self.scale_check.isChecked():
            const_name = self.get_unique_name(f"{bone_short}_{prefix1}ScaleConstraint")
            scale_const = cmds.scaleConstraint(ctrl_curve, bone, maintainOffset=True, name=const_name)
            constraint_list.append(scale_const[0])
        
        if self.aim_check.isChecked():
            const_name = self.get_unique_name(f"{bone_short}_{prefix1}AimConstraint")
            aim_const = cmds.aimConstraint(ctrl_curve, bone, maintainOffset=True,
                                          aimVector=[1, 0, 0], upVector=[0, 1, 0], worldUpType="scene", name=const_name)
            constraint_list.append(aim_const[0])
        
        return constraint_list

    def check_constraint_selection(self):
        if not (self.parent_check.isChecked() or self.point_check.isChecked() or 
                self.orient_check.isChecked() or self.scale_check.isChecked() or self.aim_check.isChecked()):
            cmds.warning("请至少选择一种约束类型！")
            self.status_label.setText("状态：错误 | 未选择任何约束类型 | 命名规则：前缀+骨骼名")
            return False
        return True

    def generate_controllers(self, bones_to_process, mode_desc):
        if not self.check_constraint_selection():
            return
        
        cmds.undoInfo(openChunk=True, chunkName=f"生成控制器-{mode_desc}")
        bone_group_mapping.clear()
        
        try:
            if not bones_to_process:
                self.status_label.setText(f"状态：错误 | {mode_desc} - 无有效骨骼 | 命名规则：前缀+骨骼名")
                return
            
            layer_count = 3 if self.layer_combo.currentIndex() == 0 else 4
            
            for bone in bones_to_process:
                outer_grp, inner_grp, ctrl_curve = self.create_ctrl_groups(bone, layer_count)
                bone_group_mapping[bone] = {
                    "outer_grp": outer_grp,
                    "inner_grp": inner_grp,
                    "ctrl_curve": ctrl_curve
                }
            
            for bone in bones_to_process:
                self.set_group_hierarchy(bone)
            
            constraint_total = 0
            for bone in bones_to_process:
                ctrl_curve = bone_group_mapping[bone]["ctrl_curve"]
                const_list = self.create_constraints(bone, ctrl_curve)
                constraint_total += len(const_list)
            
            prefix_desc = f"前缀1：{self.prefix1_edit.text()} | 前缀2：{self.prefix2_edit.text()}"
            if layer_count == 4:
                prefix_desc += f" | 前缀3：{self.prefix3_edit.text()}"
            prefix_desc += f" | 控制器后缀：{self.ctrl_suffix_edit.text()}"
            
            self.status_label.setText(
                f"状态：成功 | {mode_desc} - 处理{len(bones_to_process)}个骨骼，创建{constraint_total}个约束 | {prefix_desc}"
            )
            
            cmds.inViewMessage(
                amg=f"✅ 控制器生成成功！\n模式：{mode_desc}\n层数：{layer_count}层\n处理骨骼数：{len(bones_to_process)}\n约束数：{constraint_total}\n命名规则：前缀+骨骼名\n{prefix_desc}",
                pos="midCenter", fade=True, bgColor=(0, 0.6, 0, 0.8)
            )
        
        except Exception as e:
            error_msg = f"{mode_desc}失败：{str(e)[:50]}"
            self.status_label.setText(f"状态：失败 | {error_msg} | 命名规则：前缀+骨骼名")
            cmds.warning(error_msg)
            cmds.inViewMessage(
                amg=f"❌ {error_msg}",
                pos="midCenter", fade=True, bgColor=(0.8, 0, 0, 0.8)
            )
        
        finally:
            cmds.undoInfo(closeChunk=True)

    def on_create_selected_only(self):
        selected_bones = cmds.ls(selection=True, type="joint") or []
        
        if not selected_bones:
            self.status_label.setText("状态：错误 | 生成选中对象 - 未选中任何骨骼 | 命名规则：前缀+骨骼名")
            cmds.warning("请先选中一个或多个骨骼！")
            return
        
        self.generate_controllers(selected_bones, f"生成选中对象（{len(selected_bones)}个）")

    def on_create_hierarchy(self):
        selected_bones = cmds.ls(selection=True, type="joint") or []
        
        if not selected_bones:
            self.status_label.setText("状态：错误 | 生成层级所有 - 未选中任何骨骼 | 命名规则：前缀+骨骼名")
            cmds.warning("请先选中一个或多个骨骼！")
            return
        
        bone_hierarchy = self.get_selected_bone_hierarchy(selected_bones)
        if not bone_hierarchy:
            self.status_label.setText("状态：错误 | 生成层级所有 - 未找到子级骨骼 | 命名规则：前缀+骨骼名")
            return
        
        self.generate_controllers(bone_hierarchy, f"生成层级所有（{len(bone_hierarchy)}个）")

    def update_selection(self):
        selected_bones = cmds.ls(selection=True, type="joint") or []
        prefix_desc = f"前缀1：{self.prefix1_edit.text()} | 前缀2：{self.prefix2_edit.text()}"
        if self.layer_combo.currentIndex() == 1:
            prefix_desc += f" | 前缀3：{self.prefix3_edit.text()}"
        self.status_label.setText(
            f"状态：就绪 | 选中骨骼：{len(selected_bones)}个 | {prefix_desc} | 控制器后缀：{self.ctrl_suffix_edit.text()}"
        )

    def init_selection_listener(self):
        global SCRIPT_JOB_ID
        if SCRIPT_JOB_ID != -1 and cmds.scriptJob(exists=SCRIPT_JOB_ID):
            cmds.scriptJob(kill=SCRIPT_JOB_ID)
        SCRIPT_JOB_ID = cmds.scriptJob(event=["SelectionChanged", self.update_selection], killWithScene=True)
        om.MGlobal.displayInfo("骨骼选择监听创建成功，命名规则：前缀+骨骼名")

    def closeEvent(self, event):
        global SCRIPT_JOB_ID, WINDOW_INSTANCE
        if SCRIPT_JOB_ID != -1 and cmds.scriptJob(exists=SCRIPT_JOB_ID):
            cmds.scriptJob(kill=SCRIPT_JOB_ID)
            SCRIPT_JOB_ID = -1
        WINDOW_INSTANCE = None
        event.accept()

def show_ui():
    global WINDOW_INSTANCE
    if WINDOW_INSTANCE is not None:
        WINDOW_INSTANCE.close()
        WINDOW_INSTANCE = None
    WINDOW_INSTANCE = BoneCtrlCreatorUI()
    WINDOW_INSTANCE.show()
    return WINDOW_INSTANCE

if __name__ == "__main__":
    if SCRIPT_JOB_ID != -1 and cmds.scriptJob(exists=SCRIPT_JOB_ID):
        cmds.scriptJob(kill=SCRIPT_JOB_ID)
        SCRIPT_JOB_ID = -1
    show_ui()