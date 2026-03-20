import maya.cmds as cmds


def GN_ArraysMatch(a, b):
	if a is None and b is None:
		return True
	elif a is None or b is None:
		return False
	
	length = len(a)
	if length != len(b):
		return False
		
	for i in range(length):
		if a[i] != b[i]:
			return False
	
	return True


def GN_FixNonManifoldGeometry(object):
	# Check if we have non-manifold geometry
	nonManifold = cmds.polyInfo(object, nmv=True, nme=True)
	if nonManifold is None:
		return
	
	# Conform the geometry
	cmds.polyNormal((object + ".f[*]"), nm=2)
	
	# Split non-manifold components
	edges = cmds.polyInfo(object, nme=True)
	vertices = []
	if edges is None:
		vertices = cmds.polyInfo(object, nmv=True)
	
	lastEdges, lastVertices = [], []
	while not GN_ArraysMatch(lastEdges, edges) or not GN_ArraysMatch(lastVertices, vertices) and (len(edges) + len(vertices)):
		# Remember what was non-manifold last time
		lastEdges = edges
		lastVertices = vertices
		
		# Split any nonmanifold edges
		if edges is not None:
			cmds.polySplitEdge(edges)
			del edges[:]
			vertices = cmds.polyInfo(object, nmv=True)
		
		# Split any remaining non-manifold vertices
		if vertices is not None:
			cmds.polySplitVertex(vertices)
			del vertices[:]
		
		# Now check to see if the object is still non-manifold
		nonManifold = cmds.polyInfo(object, nmv=True, nme=True)
		if nonManifold is not None:
			# Chip off the faces
			nonManifoldFaces = cmds.polyListComponentConversion(nonManifold, tf=True)
			cmds.polyChipOff(nonManifoldFaces, kft=False, dup=False)
			
			# And then check for nonmanifold bits again
			edges = cmds.polyInfo(object, nme=True)
			if edges is None:
				vertices = cmds.polyInfo(object, nmv=True)


def GN_FixNonManifoldUvs(object):
	# Check if we have non-manifold UVs
	nonManifold = cmds.polyInfo(object, nuv=True, nue=True)
	if nonManifold is None:
		return
	
	uvs = cmds.polyListComponentConversion(nonManifold, tuv=True)
	edges = cmds.polyListComponentConversion(nonManifold, te=True)
	if len(uvs):
		uvEdges = cmds.polyListComponentConversion(uvs, fv=True, ff=True, fuv=True, fvf=True, te=True, vfa=True)
		if len(uvEdges):
			edges.extend(uvEdges)
	
	if len(edges):
		cmds.polyMapCut(edges)


def GN_FixMeshIntegrity(objects, fixColor=False):
	selection = cmds.ls(sl=True, l=True)
	
	for obj in objects:
		cmds.select(obj, r=True)
		
		# Remove color sets
		if fixColor:
			colorSet = cmds.polyColorSet(obj, q=True, acs=True)
			if colorSet is not None:
				for set in colorSet:
					cmds.polyColorSet(obj, d=True, cs=set)
		
		# Remove invalid components
		cmds.polyClean(obj, ce=True, cv=True, cuv=True, cpm=True)
		
		# Remove lamina faces
		lamina = cmds.polyInfo(obj, lf=True)
		if lamina is not None:
			cmds.delete(lamina)
			
		# Remove zero area faces
		cmds.polySelectConstraint(dis=True)
		fgeom = cmds.polySelectConstraint(m=3, t=0x0008, ga=1, gab=(0, 0.00001), rs=1)
		cmds.polySelectConstraint(dis=True)
		
		if len(fgeom):
			vertices = cmds.polyListComponentConversion(fgeom, tv=True)
			cmds.delete(fgeom)
			if len(vertices):
				cmds.polyMergeVertex(vertices, d=0.00001)
			
		# Collapse zero length edges
		egeom = cmds.polySelectConstraint(m=3, t=0x8000, l=1, lb=(0, 0.00001), rs=1)
		cmds.polySelectConstraint(dis=True)
		
		if len(egeom):
			cmds.polyCollapseEdge(egeom)
		
		# Fix non-manifold geometry
		GN_FixNonManifoldGeometry(obj)
		
		# Fix non-manifold UVs
		GN_FixNonManifoldUvs(obj)
		
		# Triangulate ngons & holed polygons
		triangulate = []
		
		nsided = cmds.polySelectConstraint(m=3, t=0x0008, sz=3, rs=1)
		cmds.polySelectConstraint(dis=True)
		if len(nsided):
			triangulate.extend(nsided)
		
		holes = cmds.polySelectConstraint(m=3, t=0x0008, h=1, rs=1)
		cmds.polySelectConstraint(dis=True)
		if len(holes):
			triangulate.extend(holes)
		
		if len(triangulate):
			triangulate = list(dict.fromkeys(triangulate)) # Remove duplicates
			cmds.polyTriangulate(triangulate)
		
		# Delete history
		cmds.delete(obj, ch=True)
	
	cmds.select(selection, r=True)