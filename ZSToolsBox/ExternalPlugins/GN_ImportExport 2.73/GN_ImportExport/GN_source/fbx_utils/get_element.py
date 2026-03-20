# Blender <version>/<version>/scripts/addons/io_scene_fbx

#from ...GN_source import GN_Print
from . import parse_fbx
from .parse_fbx import (
	data_types,
	FBXElem
)


def elem_find_first(elem, id_search, default=None):
    for fbx_item in elem.elems:
        if fbx_item.id == id_search:
            return fbx_item
    return default


# ----
# Support for
# Properties70: { ... P:
# Custom properties ("user properties" in FBX) are ignored here and get handled separately (see #104773).
def elem_props_find_first(elem, elem_prop_id):
    if elem is None:
        # When properties are not found... Should never happen, but happens - as usual.
        return None
    # support for templates (tuple of elems)
    if type(elem) is not FBXElem:
        assert(type(elem) is tuple)
        for e in elem:
            result = elem_props_find_first(e, elem_prop_id)
            if result is not None:
                return result
        assert(len(elem) > 0)
        return None

    for subelem in elem.elems:
        assert(subelem.id == b'P')
        # 'U' flag indicates that the property has been defined by the user.
        if subelem.props[0] == elem_prop_id and b'U' not in subelem.props[3]:
            return subelem
    return None


def elem_props_get_number(elem, elem_prop_id, default=None):
    elem_prop = elem_props_find_first(elem, elem_prop_id)
    if elem_prop is not None:
        assert(elem_prop.props[0] == elem_prop_id)
        if elem_prop.props[1] == b'double':
            assert(elem_prop.props[1] == b'double')
            assert(elem_prop.props[2] == b'Number')
        else:
            assert(elem_prop.props[1] == b'Number')
            assert(elem_prop.props[2] == b'')

        # we could allow other number types
        assert(elem_prop.props_type[4] == data_types.FLOAT64)

        return elem_prop.props[4]
    return default


def elem_props_get_string(elem, elem_prop_id, default=None):
	elem_prop = elem_props_find_first(elem, elem_prop_id)
	if elem_prop is not None:
		assert(elem_prop.props[0] == elem_prop_id)
		if elem_prop.props[1] == b'KString':
			assert(elem_prop.props[1] == b'KString')
			assert(elem_prop.props[2] == b'')
			assert(elem_prop.props[3] == b'')

		# we could allow other string types
		assert(elem_prop.props_type[4] == data_types.STRING)

		return elem_prop.props[4]
	return default


def check_file(file):
	if file.is_file():
		try:
			with open(file, 'r', encoding="utf-8") as fh:
				fh.read(24)
			#GN_Print.GN_Print(f"ASCII FBX files are not supported: {file.as_posix()}", mode='ERROR')
			pass
		except Exception:
			return True
	
	return False


def parse_File(file):
	try:
		elem_root = parse_fbx.parse(file)[0]
	except Exception:
		#GN_Print.GN_Print(f"Couldn't open file: {filepath.as_posix()}", mode='ERROR')
		elem_root = None
	return elem_root


def get_blenderScale(file):
	if not check_file(file):
		return

	elem_root = parse_File(file)
	if not elem_root:
		return

	fbx_header = elem_find_first(elem_root, b'FBXHeaderExtension')
	fbx_scene_info = elem_find_first(fbx_header, b'SceneInfo')
	fbx_scene_info_props = elem_find_first(fbx_scene_info, b'Properties70')
	if not any([fbx_header, fbx_scene_info, fbx_scene_info_props]):
		#GN_Print.GN_Print(f"No 'FBXHeaderExtension' found in file: {filepath.as_posix()}", mode='ERROR')
		return
	
	lastSaved = elem_props_get_string(fbx_scene_info_props, b'LastSaved|ApplicationVendor')
	
	fbx_settings = elem_find_first(elem_root, b'GlobalSettings')
	fbx_settings_props = elem_find_first(fbx_settings, b'Properties70')
	if not any([fbx_settings, fbx_settings_props]):
		#GN_Print.GN_Print(f"No 'GlobalSettings' found in file: {filepath.as_posix()}", mode='ERROR')
		return
	
	unitScale = elem_props_get_number(fbx_settings_props, b'UnitScaleFactor', default=1.0)
	
	return lastSaved == b'Blender Foundation' or unitScale == 100.0