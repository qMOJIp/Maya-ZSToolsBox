from ngSkinTools2 import api, signal


def can_import(session):
    """
    :type session: ngSkinTools2.api.session.Session
    """

    if not session.state.selection:
        return False

    if session.state.layersAvailable:
        return False

    return api.import_v1.can_import(session.state.selection[-1])


def build_action_import_v1(session, parent):
    """
    :type parent: PySide2.QtWidgets.QWidget
    :type session: ngSkinTools2.api.session.Session
    """
    from ngSkinTools2.ui import actions

    def do_convert():
        api.import_v1.import_layers(session.state.selection[-1])
        api.import_v1.cleanup(session.state.selection[-1:])
        update_state()
        session.events.targetChanged.emitIfChanged()

    result = actions.define_action(parent, "从v1.0图层转换", callback=do_convert)
    result.setToolTip("“转化旧版ngSkinTools的图层;完成此操作后，v1节点将被删除。")

    @signal.on(session.events.targetChanged)
    def update_state():
        result.setVisible(can_import(session))

    update_state()

    return result
