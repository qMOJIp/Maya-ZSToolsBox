//Maya ASCII 2019 scene
//Name: [ZBrush,WriteString,FileName].ma
//Codeset: UTF-8

requires maya "2019";

createNode transform -n "[ZBrush,WriteString,FileName]";
createNode mesh -n "[ZBrush,WriteString,FileName]Shape" -p "[ZBrush,WriteString,FileName]";

//===================================
//UVs - segmented to 250 entries per block
//===================================
	setAttr ".uvst[0].uvsn" -type "string" "map1";[ZBrush,If,UVCount,	
	setAttr -s [ZBrush,Write,UVCount] ".uvst[0].uvsp";[ZBrush,While,[Larger,[Sub,UVCount,UVIndex],249],
	setAttr ".uvst[0].uvsp[[ZBrush,Write,UVIndex]:[ZBrush,Write,[Add,UVIndex,249]]]" -type "float2"[ZBrush,Repeat,125,
		[ZBrush,Repeat,2, [ZBrush,Write,U] [ZBrush,Write,V]]];]
[ZBrush,If,[Smaller,UVIndex,UVCount],	setAttr ".uvst[0].uvsp[[ZBrush,Write,UVIndex][ZBrush,If,[Smaller,UVIndex,[Sub,UVCount,1]],:[ZBrush,Write,[Sub,UVCount,1]]]]" -type "float2"[ZBrush,While,[Larger,[Sub,UVCount,UVIndex],2],
		[ZBrush,Repeat,2, [ZBrush,Write,U] [ZBrush,Write,V]]]
		[ZBrush,Repeat,[Sub,UVCount,UVIndex], [ZBrush,Write,U] [ZBrush,Write,V]];]][ZBrush,If,[Smaller,UVCount, 1],
	setAttr -s [ZBrush, Write, [Sub,[Mul,EdgeCount,2],3]] ".uvst[0].uvsp";]
	setAttr ".cuvs" -type "string" "map1";
	setAttr ".dcc" -type "string" "Ambient+Diffuse";

//===================================
// Vertices  - segmented to 166 entries per block
//===================================
	setAttr -s [ZBrush,Write,VertexCount] ".vt";[ZBrush,While,[Larger,[Sub,VertexCount,VertexIndex],165],
	setAttr ".vt[[ZBrush,Write,VertexIndex]:[ZBrush,Write,[Add,VertexIndex,165]]]"[ZBrush,Repeat,83,
		[ZBrush,Repeat,2, [ZBrush,Write,X] [ZBrush,Write,Y] [ZBrush,Write,Z]]];]
[ZBrush,If,[Smaller,VertexIndex,VertexCount],	setAttr ".vt[[ZBrush,Write,VertexIndex][ZBrush,If,[Smaller,VertexIndex,[Sub,VertexCount,1]],:[ZBrush,Write,[Sub,VertexCount,1]]]]"[ZBrush,While,[Larger,[Sub,VertexCount,VertexIndex],2],
		[ZBrush,Repeat,2, [ZBrush,Write,X] [ZBrush,Write,Y] [ZBrush,Write,Z]]]
		[ZBrush,Repeat,[Sub,VertexCount,VertexIndex], [ZBrush,Write,X] [ZBrush,Write,Y] [ZBrush,Write,Z]];]

//===================================
// Edges - segmented to 166 entries per block
//===================================
 	setAttr -s [ZBrush,Write,EdgeCount] ".ed";[ZBrush,While,[Larger,[Sub,EdgeCount,EdgeIndex],165],
	setAttr ".ed[[ZBrush,Write,EdgeIndex]:[ZBrush,Write,[Add,EdgeIndex,165]]]"[ZBrush,Repeat,83,
		[ZBrush,Repeat,2, [ZBrush,Write,EdgeStart] [ZBrush,Write,EdgeEnd] 0]];]
[ZBrush,If,[Smaller,EdgeIndex,EdgeCount],	setAttr ".ed[[ZBrush,Write,EdgeIndex][ZBrush,If,[Smaller,EdgeIndex,[Sub,EdgeCount,1]],:[ZBrush,Write,[Sub,EdgeCount,1]]]]"[ZBrush,While,[Larger,[Sub,EdgeCount,EdgeIndex],2],
		[ZBrush,Repeat,2, [ZBrush,Write,EdgeStart] [ZBrush,Write,EdgeEnd] 0]]
		[ZBrush,Repeat,[Sub,EdgeCount,EdgeIndex], [ZBrush,Write,EdgeStart] [ZBrush,Write,EdgeEnd] 0];]

//===================================
// Faces - segmented to 500 entries per block
//===================================
	setAttr -s [ZBrush,Write,FaceCount] -ch [ZBrush, Write, [Mul, EdgeCount, 2]] ".fc";[ZBrush,While,[Larger,[Sub,FaceCount,FaceIndex],499],
	setAttr ".fc[[ZBrush,Write,FaceIndex]:[ZBrush,Write,[Add,FaceIndex,499]]]" -type "polyFaces"[ZBrush,Repeat,500,
		f [ZBrush,Write,EdgeCountInFace][ZBrush,Repeat,EdgeCountInFace, [ZBrush,Write,EdgeIndexInFace]]
		mu 0 [ZBrush,Write,UVCountInFace][ZBrush,Repeat,UVCountInFace, [ZBrush,Write,UVIndexInFace]]];]
[ZBrush,If,[Smaller,FaceIndex,FaceCount],	setAttr ".fc[[ZBrush,Write,FaceIndex][ZBrush,If,[Smaller,FaceIndex,[Sub,FaceCount,1]],:[ZBrush,Write,[Sub,FaceCount,1]]]]" -type "polyFaces"[ZBrush,Repeat,[Sub,FaceCount,FaceIndex],
		f [ZBrush,Write,EdgeCountInFace][ZBrush,Repeat,EdgeCountInFace, [ZBrush,Write,EdgeIndexInFace]]
		mu 0 [ZBrush,Write,UVCountInFace][ZBrush,Repeat,UVCountInFace, [ZBrush,Write, UVIndexInFace]]];]

//===================================
// Creased Edges
//===================================
	setAttr ".cd" -type "dataPolyComponent" Index_Data Edge [ZBrush,Write,CreasedEdgeCount][ZBrush,Repeat,CreasedEdgeCount,
		[ZBrush,Write,CreasedEdgeIndex] 1000];
	setAttr ".cvd" -type "dataPolyComponent" Index_Data Vertex 0;
	setAttr ".pd[0]" -type "dataPolyComponent" Index_Data UV 0;
	setAttr ".hfd" -type "dataPolyComponent" Index_Data Face 0;

//===================================
connectAttr "[ZBrush,WriteString,FileName]Shape.iog" ":initialShadingGroup.dsm" -na;

// End of [ZBrush,WriteString,FileName].ma
[ZBrush,AutoSaveTool]