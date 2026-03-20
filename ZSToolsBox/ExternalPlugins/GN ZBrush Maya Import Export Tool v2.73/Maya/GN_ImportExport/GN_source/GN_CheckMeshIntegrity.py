import maya.cmds as cmds


def GN_CheckMeshIntegrity(objects, checkColor=False):
	selection = cmds.ls(sl=True, l=True)
	objectsWithIssues = []
	
	for obj in objects:
		cmds.select(obj, r=True)
		topoErrors = []
		
		# Check color sets
		if checkColor:
			colorSet = cmds.polyColorSet(obj, q=True, acs=True)
			if colorSet is not None:
				topoErrors.extend(colorSet)
		
		# Check nsided
		cmds.polySelectConstraint(dis=True)
		nsided = cmds.polySelectConstraint(m=3, t=0x0008, sz=3, rs=1)
		cmds.polySelectConstraint(dis=True)
		if len(nsided):
			topoErrors.extend(nsided)
		
		# Check holes
		holes = cmds.polySelectConstraint(m=3, t=0x0008, h=1, rs=1)
		cmds.polySelectConstraint(dis=True)
		if len(holes):
			topoErrors.extend(holes)
		
		# Check zero area faces
		fgeom = cmds.polySelectConstraint(m=3, t=0x0008, ga=1, gab=(0, 0.00001), rs=1)
		cmds.polySelectConstraint(dis=True)
		if len(fgeom):
			topoErrors.extend(fgeom)
		
		# Check zero length edges
		egeom = cmds.polySelectConstraint(m=3, t=0x8000, l=1, lb=(0, 0.00001), rs=1)
		cmds.polySelectConstraint(dis=True)
		if len(egeom):
			topoErrors.extend(fgeom)
		
		# Check lamina faces and non-manifold components
		nonManifold = cmds.polyInfo(obj, lf=True, nmv=True, nme=True)
		if nonManifold is not None:
			topoErrors.extend(nonManifold)
		
		if len(topoErrors):
			objectsWithIssues.append(obj)
	
	cmds.select(selection, r=True)
	return objectsWithIssues