import maya.cmds as mc
def matObj(obj):
    # 获取父节点
    obj_p = mc.listRelatives(obj, parent=True)
    # 获取形状节点
    shap_node = mc.listRelatives(obj, shapes=True)
    if not shap_node:
        print(f"警告：{obj} 没有找到形状节点，跳过")
        return
    # 获取关联的着色组（shadingEngine）
    dest = mc.listConnections(shap_node[0], source=False, type="shadingEngine")
    if not dest:
        print(f"警告：{obj} 没有关联的材质组，跳过")
        return
    mc.select(dest, replace=True, noExpand=True)
    shadingGrp = mc.ls(selection=True)
    # 创建分组
    grp_name = f'{obj}_shadingGrp'
    mc.group(empty=True, name=grp_name)
    for i in range(len(shadingGrp)):
        # 获取材质节点
        mat_node = mc.listConnections(shadingGrp[i], destination=False)
        if not mat_node:
            print(f"警告：{shadingGrp[i]} 没有关联的材质节点，跳过")
            continue
        # 复制模型
        dup_name = f'{obj}_{mat_node[0]}'
        dup_obj = mc.duplicate(obj, name=dup_name)[0]
        # 父化到分组
        mc.parent(dup_obj, grp_name)
        # 转换选择为面
        mc.select(dup_obj)
        mc.ConvertSelectionToContainedFaces()
        sets = mc.sets()
        mat_gs = mc.listConnections(mat_node, type='shadingEngine')
        print(mat_gs)
        # 处理初始粒子着色组
        if mat_gs and mat_gs[0] == 'initialParticleSE':
            mat_gs[0] = mat_gs[-1]
        # 选择指定材质的面并删除其他面
        if mat_gs:
            mc.select(mc.sets(mat_gs[0], intersection=sets))
            mc.InvertSelection()
            mc.delete()
        mc.delete(sets)
    # 删除原模型
    mc.delete(obj)
    # 父化分组到原父节点
    if obj_p:
        mc.parent(grp_name, obj_p[0])
# 执行主逻辑
selected_objs = mc.ls(selection=True)
if selected_objs:
    for obj_trs in selected_objs:
        matObj(obj_trs)
else:
    print("错误：请先选择要分离的模型！")