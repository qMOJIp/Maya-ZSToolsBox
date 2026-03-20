from maya import cmds

from ngSkinTools2 import api, signal
from ngSkinTools2.api.log import getLogger
from ngSkinTools2.api.python_compatibility import Object
from ngSkinTools2.api.session import Session
from ngSkinTools2.decorators import undoable
from ngSkinTools2.observableValue import ObservableValue
from ngSkinTools2.operations import layers
from ngSkinTools2.ui import dialogs

logger = getLogger("operation/tools")


def __create_tool_action__(parent, session, action_name, action_tooltip, exec_handler, enabled_handler=None):
    """
    :type session: Session
    """

    from ngSkinTools2.ui import actions

    def execute():
        if not session.active():
            return

        exec_handler()

    result = actions.define_action(parent, action_name, callback=execute, tooltip=action_tooltip)

    @signal.on(session.events.targetChanged, session.events.currentLayerChanged)
    def update_state():
        enabled = session.state.layersAvailable and session.state.currentLayer.layer is not None
        if enabled and enabled_handler is not None:
            enabled = enabled_handler(session.state.currentLayer.layer)
        result.setEnabled(enabled)

    update_state()

    return result


class ClosestJointOptions(Object):
    def __init__(self):
        self.create_new_layer = ObservableValue(False)
        self.all_influences = ObservableValue(True)


def create_action__from_closest_joint(parent, session):
    options = ClosestJointOptions()

    def exec_handler():
        layer = session.state.currentLayer.layer
        influences = None
        if not options.all_influences():
            influences = layer.paint_targets
            if not influences:
                dialogs.info("在影响列表中选择一个或多个影响")
                return

        if options.create_new_layer():
            layer = layers.addLayer()

        api.assign_from_closest_joint(
            session.state.selectedSkinCluster,
            layer,
            influences=influences,
        )
        session.events.currentLayerChanged.emitIfChanged()
        session.events.influencesListUpdated.emit()

        if layer.paint_target is None:
            used_influences = layer.get_used_influences()
            if used_influences:
                layer.paint_target = min(used_influences)

    return (
        __create_tool_action__(
            parent,
            session,
            action_name=u"从最近的关节分配",
            action_tooltip="为选定层中每个顶点的最近影响分配权重1.0",
            exec_handler=exec_handler,
        ),
        options,
    )


class UnifyWeightsOptions(Object):
    overall_effect = ObservableValue(1.0)
    single_cluster_mode = ObservableValue(False)


def create_action__unify_weights(parent, session):
    options = UnifyWeightsOptions()

    def exec_handler():
        api.unify_weights(
            session.state.selectedSkinCluster,
            session.state.currentLayer.layer,
            overall_effect=options.overall_effect(),
            single_cluster_mode=options.single_cluster_mode(),
        )

    return (
        __create_tool_action__(
            parent,
            session,
            action_name=u"统一权重",  # Unify Weights
            action_tooltip="对于选定的顶点，使所有顶点相同。", #对于选定的顶点，使所有顶点相同。
            exec_handler=exec_handler,
        ),
        options,
    )


def create_action__merge_layers(parent, session):
    """
    :param parent: UI parent for this action
    :type session: Session
    """

    def exec_handler():
        api.merge_layers(layers=session.context.selected_layers(default=[]))
        session.events.layerListChanged.emitIfChanged()
        session.events.currentLayerChanged.emitIfChanged()

    def enabled_handler(layer):
        return layer is not None and layer.index > 0

    return __create_tool_action__(
        parent,
        session,
        action_name=u"合并", # Merge
        action_tooltip="将本层的元素合并到底层。预效果权重将用于此。",
        exec_handler=exec_handler,
        enabled_handler=enabled_handler,
    )


def create_action__duplicate_layer(parent, session):
    """
    :param parent: UI parent for this action
    :type session: Session
    """

    @undoable
    def exec_handler():
        with api.suspend_updates(session.state.selectedSkinCluster):
            for source in session.context.selected_layers(default=[]):
                api.duplicate_layer(layer=source)

        session.events.layerListChanged.emitIfChanged()
        session.events.currentLayerChanged.emitIfChanged()

    return __create_tool_action__(
        parent,
        session,
        action_name=u"复制",
        action_tooltip="复制选择的图层(多选)",
        exec_handler=exec_handler,
    )


def create_action__fill_transparency(parent, session):
    """
    :param parent: UI parent for this action
    :type session: Session
    """

    @undoable
    def exec_handler():
        with api.suspend_updates(session.state.selectedSkinCluster):
            for source in session.context.selected_layers(default=[]):
                api.fill_transparency(layer=source)

    return __create_tool_action__(
        parent,
        session,
        action_name=u"填充透明度",
        action_tooltip="所选图层中的所有透明顶点接收其最近非空邻接顶点的权重，",
        exec_handler=exec_handler,
    )


def create_action__copy_component_weights(parent, session):
    """
    :param parent: UI parent for this action
    :type session: Session
    """

    def exec_handler():
        for source in session.context.selected_layers(default=[]):
            api.copy_component_weights(layer=source)

    return __create_tool_action__(
        parent,
        session,
        action_name=u"复制组件权重",
        action_tooltip="将组件权重存储在内存中，以便进行进一步的基于组件的粘贴操作",
        exec_handler=exec_handler,
    )


def create_action__paste_average_component_weight(parent, session):
    """
    :param parent: UI parent for this action
    :type session: Session
    """

    def exec_handler():
        for l in session.context.selected_layers(default=[]):
            api.paste_average_component_weights(layer=l)

    return __create_tool_action__(
        parent,
        session,
        action_name=u"粘贴平均组件权重",
        action_tooltip="计算复制的组件重量的平均值，并将该值设置为当前选定的组件",
        exec_handler=exec_handler,
    )


def create_action__add_influences(parent, session):
    """
    :param parent: UI parent for this action
    :type session: Session
    """

    def exec_handler():
        selection = cmds.ls(sl=True, l=True)
        if len(selection) < 2:
            logger.info("无效选择: %s", selection)
            return
        api.add_influences(selection[:-1], selection[-1])
        cmds.select(selection[-1])
        session.events.influencesListUpdated.emit()

    return __create_tool_action__(
        parent,
        session,
        action_name=u"增加影响",
        action_tooltip="将选定的影响添加到当前皮肤集群。",
        exec_handler=exec_handler,
    )


def create_action__select_affected_vertices(parent, session):
    """
    :param parent: UI parent for this action
    :type session: Session
    """

    def exec_handler():
        selected_layers = session.context.selected_layers(default=[])
        if not selected_layers:
            return

        if not session.state.currentLayer.layer:
            return

        influences = session.state.currentLayer.layer.paint_targets
        if not influences:
            return

        non_zero_weights = []
        for layer in selected_layers:
            for i in influences:
                weights = layer.get_weights(i)
                if weights:
                    non_zero_weights.append(weights)

        if not non_zero_weights:
            return

        current_selection = cmds.ls(sl=True, o=True, l=True)
        if len(current_selection) != 1:
            return

        # we're not sure - this won't work if skin cluster is selected directly
        selected_mesh_probably = current_selection[0]

        combined_weights = [sum(i) for i in zip(*non_zero_weights)]
        indexes = [selected_mesh_probably + ".vtx[%d]" % index for index, i in enumerate(combined_weights) if i > 0.00001]
        try:
            cmds.select(indexes)
        except:
            pass

    return __create_tool_action__(
        parent,
        session,
        action_name=u"选择受影响的顶点",
        action_tooltip="选择当前影响中权重不为要的顶点。",
        exec_handler=exec_handler,
    )
