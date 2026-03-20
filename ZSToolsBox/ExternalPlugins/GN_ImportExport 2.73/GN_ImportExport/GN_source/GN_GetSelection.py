import maya.cmds as cmds


def GN_GetSelection(*args, **kwargs):
	type = kwargs["type"] if "type" in kwargs else "None"
	highlight = kwargs["highlight"] if "highlight" in kwargs else False
	flatten = kwargs["flatten"] if "flatten" in kwargs else False
	allParents = kwargs["allParents"] if "allParents" in kwargs else False

	# Check if there is any args
	if len(args) > 0:
		selection, objects = [], []
		# Get selection & objects from args
		for arg in args:
			selection.extend(arg)
			objects.extend(arg)
	else:
		# Get selection
		if flatten:
			selection = cmds.ls(sl=True, l=True, fl=True)
		else:
			selection = cmds.ls(sl=True, l=True)
		
		objects = list(selection)
		
		# Get highlighted objects
		if highlight:
			objects.extend(cmds.ls(hl=True, l=True))
	
	# Get shapes
	if type == "mesh":
		shapes = cmds.ls(objects, l=True, dag=True, ni=True, o=True, typ="mesh")
	elif type == "geometry" or type == "geo":
		shapes = cmds.ls(objects, l=True, dag=True, ni=True, o=True, g=True)
	elif type == "nurbsCurve" or type == "curve":
		shapes = cmds.ls(objects, l=True, dag=True, ni=True, typ="nurbsCurve")
	elif type == "transform":
		shapes = cmds.ls(objects, l=True, dag=True, ni=True, o=True, typ="transform")
	else:
		shapes = cmds.ls(objects, l=True, dag=True, ni=True, o=True)
	
	# Get objects
	if allParents:
		objects = cmds.listRelatives(shapes, f=True, ap=True, ni=True, typ="transform")
	else:
		objects = cmds.listRelatives(shapes, f=True, p=True, ni=True, typ="transform")
	
	# Remove intermediate objects
	objects = cmds.ls(objects, l=True, ni=True)
	
	# Remove duplicates objects
	if objects is not None:
		objects = list(dict.fromkeys(objects))
	
	return selection, shapes, objects