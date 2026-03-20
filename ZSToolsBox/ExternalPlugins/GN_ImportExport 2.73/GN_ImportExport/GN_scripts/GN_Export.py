import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

from functools import partial
from webbrowser import open_new_tab
from pathlib import Path
import shutil
import re

from ..GN_source import GN_GetSelection, GN_CheckMeshIntegrity, GN_FixMeshIntegrity, GN_Print


def clamp_colors(colors, values=[0, 1]):
    return [min(max(col, values[0]), values[1]) for col in colors]


def rgba_to_hex(rgba):
    if len(rgba) == 4:
        hex = '%02x%02x%02x%02x' % tuple(int(i * 255) for i in rgba)
    else:
        hex = "ffffffff"
    return hex


def GN_exportVertexColor(objects, file):
    # Make sure that objects is a list
    if not isinstance(objects, list):
        objects = [objects]
    
    # Initialize variables
    mrgb_list = []
    vertexColor = False

    # Loop objects
    for obj in objects:
        # Get fnMesh
        objList = om.MSelectionList().add(obj)
        dag = objList.getDagPath(0)
        fnMesh = om.MFnMesh(dag)

        # Build vertex color list
        # Check if object has a color set
        colorSet = fnMesh.numColorSets
        if colorSet > 0:
            # Initilize string
            hexString = ""

            # Get object vertex colors
            colors = fnMesh.getVertexColors()
            for color in colors:
                color = color.getColor()
                color = clamp_colors(color[-1:] + color[:-1])
                hex = rgba_to_hex(color)
                hexString += hex
            
            # Build MRGB block
            mrgb_lines = []
            start = "# The following MRGB block contains ZBrush Vertex Color (Polypaint) and masking output as 4 hexadecimal values per vertex. The vertex color format is MMRRGGBB with up to 64 entries per MRGB line."
            end = "# End of MRGB block"
            mrgb_lines.append(start)
            mrgb_lines.extend(["#MRGB " + hexString[i:i+512] for i in range(0, len(hexString), 512)])
            mrgb_lines.append(end)

            # Append MRGB block to vertex color list
            mrgb_string = "\n".join(mrgb_lines) + "\n"
            mrgb_list.append(mrgb_string)

            # Set vertex color variable
            if not vertexColor:
                vertexColor = True
        else:
            mrgb_list.append("")

    # If objects have vertex color
    if vertexColor:
        # Get file content
        fileContent = open(file, 'r').read()
        with open(file, 'w') as f:
            # Split file content by vertex data
            objects_data = re.findall(r"(^v .+$\n)+", fileContent, flags=re.MULTILINE)
            size = len(objects_data)

            # Progress bar
            gMainProgressBar = mel.eval("$gMainProgressBar = $gMainProgressBar")
            cmds.progressBar(gMainProgressBar, e=True, bp=True, ii=True, st="Exporting vertex color...", max=size)

            # Re-build file content with an MRGB block placed right after each vertex list
            for i in range(size):
                # Progress bar
                if cmds.progressBar(gMainProgressBar, q=True, ic=True):
                    break

                split = fileContent.split(objects_data[i], 1)
                fileContent = split[0] + objects_data[i] + mrgb_list[i] + split[1]

                # Progress bar
                cmds.progressBar(gMainProgressBar, e=True, s=1)
            
            f.write(fileContent)

            # Progress bar
            cmds.progressBar(gMainProgressBar, e=True, ep=True)


# Main function
def GN_PerformExport(filetype=1):
    # Initialize variables depending of filetype
    mode = cmds.optionVar(q="GNIE_mode")
    meshIntegrity = cmds.optionVar(q="GNE_meshIntegrity")
    uvSets = cmds.optionVar(q="GNE_uvSets")
    freezeTransforms = cmds.optionVar(q="GNE_freezeTransforms")
    combine = cmds.optionVar(q="GNE_combine") if mode == 1 else 0
    removeSets = cmds.optionVar(q="GNE_removeSets")
    vertexColor = cmds.optionVar(q="GNIE_vertexColor")
    colorIntegrity = False
    objectType = "geometry"

    if filetype == 1:
        fileFormat = "mayaAscii"
        extension = ".ma"
        removeSets = 0
        vertexColor = 0
        colorIntegrity = True
    
    elif filetype == 2:
        fileFormat = "OBJ"
        extension = ".obj"
        uvSets = 0
        freezeTransforms = 0
        combine = 0
        objectType = "mesh"

        # Load plugin if needed
        if not cmds.pluginInfo("objExport", q=True, l=True):
            cmds.loadPlugin("objExport")
    
    elif filetype == 3:
        fileFormat = "FBX"
        extension = ".fbx"
        uvSets = 0
        combine = 0
        removeSets = 0
        vertexColor = 0

        # Load plugin if needed
        if not cmds.pluginInfo("fbxmaya", q=True, l=True):
            cmds.loadPlugin("fbxmaya")
        
        # Edit Settings
        cmds.FBXExportAnimationOnly("-v", False)
        cmds.FBXExportApplyConstantKeyReducer("-v", False)
        cmds.FBXExportAxisConversionMethod("convertAnimation")
        cmds.FBXExportBakeComplexAnimation("-v", False)
        cmds.FBXExportBakeComplexEnd("-v", 30)
        cmds.FBXExportBakeComplexStart("-v", 0)
        cmds.FBXExportBakeComplexStep("-v", 1)
        cmds.FBXExportBakeResampleAnimation("-v", False)
        cmds.FBXExportCacheFile("-v", False)
        cmds.FBXExportCameras("-v", True)
        cmds.FBXExportColladaFrameRate(24)
        cmds.FBXExportColladaSingleMatrix(True)
        cmds.FBXExportColladaTriangulate(True)
        cmds.FBXExportConstraints("-v", True)
        cmds.FBXExportConvertUnitString("cm")
        cmds.FBXExportEmbeddedTextures("-v", False)
        cmds.FBXExportFileVersion("-v", "FBX201900")
        cmds.FBXExportGenerateLog("-v", True)
        cmds.FBXExportHardEdges("-v", False)
        cmds.FBXExportInAscii("-v", False)
        cmds.FBXExportIncludeChildren("-v", True)
        cmds.FBXExportInputConnections("-v", True)
        cmds.FBXExportInstances("-v", False)
        cmds.FBXExportLights("-v", True)
        cmds.FBXExportQuaternion("-v", "resample")
        #cmds.FBXExportQuickSelectSetAsCache("-v", "")
        cmds.FBXExportReferencedAssetsContent("-v", True)
        cmds.FBXExportScaleFactor(1.0)
        cmds.FBXExportShapes("-v", True)
        cmds.FBXExportSkeletonDefinitions("-v", True)
        cmds.FBXExportSkins("-v", True)
        cmds.FBXExportSmoothingGroups("-v", False)
        cmds.FBXExportSmoothMesh("-v", True)
        cmds.FBXExportSplitAnimationIntoTakes("-c")
        cmds.FBXExportTangents("-v", False)
        cmds.FBXExportTriangulate("-v", False)
        cmds.FBXExportUpAxis(cmds.upAxis(q=True, axis=True))
        cmds.FBXExportUseSceneName("-v", True)
        cmds.FBXExportAudio("-v", True)

    # Check directory (Single-File)
    directory = Path("C:/temp")
    if directory.is_file():
        GN_Print.GN_Print(f"Unable to create export directory because of existing file: {directory.as_posix()}", mode='ERROR')
        return
    
    # Create directory if it doesn't exist (Single-File)
    if mode == 1:
        if not directory.is_dir():
            directory.mkdir(parents=True, exist_ok=True)
    
    # Check directory (Multi-File)
    else:
        directory = Path("C:/temp/exported")
        if directory.is_file():
            GN_Print.GN_Print(f"Unable to create export directory because of existing file: {directory.as_posix()}", mode='ERROR')
            return
        
        # Create directory if it doesn't exist (Multi-File)
        elif not directory.is_dir():
            directory.mkdir(parents=True, exist_ok=True)

    # Get selection
    selection, objects = GN_GetSelection.GN_GetSelection(type=objectType, highlight=False)[0::2]
    objCount = len(objects)

    # Check that an object is selected
    if objCount <= 0:
        GN_Print.GN_Print("Current selection is incorrect and cannot be exported.", mode='ERROR')
        return
    
    # Check mesh integrity
    geoIssues = []
    if meshIntegrity == 2:
        geoIssues = GN_CheckMeshIntegrity.GN_CheckMeshIntegrity(objects, checkColor=colorIntegrity)
    
    useDuplicate = False
    if any([filetype == 2, mode == 2, meshIntegrity == 3, uvSets > 1, freezeTransforms, combine, removeSets]):
        useDuplicate = True

        # Store current namespace
        namespace = None
        if not cmds.namespace(q=True, ir=True):
            namespace = cmds.namespaceInfo(cur=True, fn=True)
            # Set namespace to root
            cmds.namespace(set=":")

        # Create namespaces
        namespaceExport = True
        if not cmds.namespace(ex="GN_Export"):
            cmds.namespace(add="GN_Export")
            namespaceExport = False

        namespaceDuplicate = True
        if not cmds.namespace(ex="GN_Duplicate"):
            cmds.namespace(add="GN_Duplicate")
            namespaceDuplicate = False
        
        # Initialize lists
        nameList = []
        dupList = om.MSelectionList()
        objList = om.MSelectionList()
        for obj in objects:
            objList.add(obj)
        
        # Duplicate & rename objects
        for i in range(objCount):
            # Get object
            dag = objList.getDagPath(i)
            object = dag.fullPathName()

            # Get object name and add to name list
            nameFull = object.split("|")[-1]
            nameShort = nameFull.split(":")[-1]
            nameList.append([nameFull, nameShort])

            # Duplicate object
            duplicate = cmds.ls(cmds.duplicate(object, n="GN_Duplicate:" + nameShort), l=True)[0]

            # Parent to world
            parent = cmds.listRelatives(duplicate, f=True, p=True)
            if parent:
                duplicate = cmds.ls(cmds.parent(duplicate, w=True), l=True)[0]
            
            # Delete children
            children = cmds.listRelatives(duplicate, f=True, c=True, ni=True, typ="transform")
            if children:
                cmds.delete(children)
            
            # Add to duplicate list
            dupList.add(duplicate)

            # Rename original object
            cmds.rename(object, "GN_Export:" + nameShort)

        # Rename duplicate objects
        for i in range(objCount):
            dag = dupList.getDagPath(i)
            duplicate = dag.fullPathName()
            cmds.rename(duplicate, nameList[i][1])
        
        # Remove GN_Duplicate namespace
        if not namespaceDuplicate:
            cmds.namespace(mnr=True, rm="GN_Duplicate")
        
        # Get new object list
        objects = cmds.ls(dupList.getSelectionStrings(), l=True)
        shapes, meshes = GN_GetSelection.GN_GetSelection(objects, type="mesh", highlight=False)[1:]
        transforms = [item for item in objects if item not in meshes]

        # Fix mesh if specified by user
        if meshIntegrity == 3:
            GN_FixMeshIntegrity.GN_FixMeshIntegrity(meshes, fixColor=colorIntegrity)
        
        # Remove sets
        if removeSets:
            for i in range(len(meshes)):
                sets = cmds.listSets(o=meshes[i], ets=True)
                if not sets:
                    continue

                for set in sets:
                    if not cmds.objExists(set) or set == "initialShadingGroup":
                        continue
                    elif cmds.sets(set, q=True, fc=True):
                        faces = meshes[i] + ".f[*]"
                        cmds.sets(faces, e=True, rm=set, nw=True)
                    else:
                        cmds.sets(shapes[i], e=True, rm=set, nw=True)
        
        # Delete UV Sets if specified by user
        if uvSets > 1:
            for obj in meshes:
                # Create list with all UV Sets
                allUvSets = cmds.polyUVSet(obj, q=True, auv=True)
                if len(allUvSets) > 1:
                    # Get current UV Set
                    currentUvSet = cmds.polyUVSet(obj, q=True, cuv=True)[0]
                    
                    # Make sure current UV Set is the first one if user specified to keep the current UV Set
                    if uvSets == 2 and currentUvSet != allUvSets[0]:
                        cmds.polyUVSet(obj, cp=True, uvs=currentUvSet, nuv=allUvSets[0])
                        cmds.polyUVSet(obj, rn=True, nuv=currentUvSet + "_tmp")
                        cmds.polyUVSet(obj, rn=True, uvs=allUvSets[0], nuv=currentUvSet)
                        allUvSets = cmds.polyUVSet(obj, q=True, auv=True)
                    
                    # Delete all UV Sets but the first one
                    for uvSet in allUvSets[1:]:
                        cmds.polyUVSet(obj, d=True, uvs=uvSet)

                # Make sure all objects have the same UV Set name before combining
                if combine:
                    if 'uvSetMem' not in locals():
                        uvSetMem = allUvSets[0]
                    elif allUvSets[0] != uvSetMem:
                        cmds.polyUVSet(obj, rn=True, nuv=uvSetMem)
        
        # Freeze transformations if specified by user
        if freezeTransforms:
            # Break object connections
            for obj in objects:
                connections = cmds.listConnections(obj, t="animCurve")
                if connections:
                    cmds.delete(connections)
                
                # Unlock all attributes
                attributes = cmds.listAttr(obj, l=True)
                if attributes:
                    for attr in attributes:
                        cmds.setAttr((obj + "." + attr), lock=False)
            
            # Freeze transforms
            cmds.makeIdentity(objects, a=True, t=True, r=True, s=True, n=False, pn=True)
        
        # Combine objects if specified by user
        if combine:
            # Check that there is more than one mesh object for the combine operation
            if len(meshes) > 1:
                name = meshes[-1].split("|")[-1]
                polyunite = cmds.ls(cmds.polyUnite(meshes, ch=False), l=True)[0]
                
                # Delete remaining junk
                for obj in meshes:
                    if cmds.objExists(obj):
                        cmds.delete(obj)
                
                # Rename combined object and append non-polymesh objects
                objects = cmds.ls(cmds.rename(polyunite, name), l=True)
                if len(transforms):
                    objects.extend(transforms)
        
    # Export Single-File
    if mode == 1:
        # Select objects
        cmds.select(objects, r=True)

        # Export in the specified file format
        file = directory / f"exported{extension}"
        if filetype == 1:
            cmds.file(file, f=True, op="v=0;", typ="mayaAscii", pr=True, ch=False, es=True)
        
        elif filetype == 2:
            cmds.file(file, f=True, op="groups=1;ptgroups=0;materials=0;smoothing=1;normals=1", typ="OBJexport", pr=True, es=True)
            # Write vertex color information in the file if specified by user
            if vertexColor:
                GN_exportVertexColor(objects, file)
        
        elif filetype == 3:
            cmds.FBXExport("-f", file, "-s")

        # Print result
        GN_Print.GN_Print(f"# Result: Exported to {file.as_posix()}", deferred=True)
    
    # Export Multi-File
    else:
        # Cleanup directory
        for file in directory.iterdir():
            if file.suffix.lower() == extension:
                if file.is_file():
                    file.unlink()
                elif file.is_dir():
                    shutil.rmtree(file, ignore_errors=True)
        
        # Loop & export each object
        for obj in objects:
            if cmds.listRelatives(obj, f=True, s=True):
                # Select object
                cmds.select(obj, r=True)
                
                # Set file name
                name = obj.split("|")[-1]
                file = directory / f"{name}{extension}"
                
                # Export in the specified file format
                if filetype == 1:
                    cmds.file(file, f=True, op="v=0;", typ="mayaAscii", pr=True, ch=False, es=True)
                
                elif filetype == 2:
                    cmds.file(file, f=True, op="groups=1;ptgroups=0;materials=0;smoothing=1;normals=1", typ="OBJexport", pr=True, es=True)
                    # Write vertex color information in the file if specified by user
                    if vertexColor:
                        GN_exportVertexColor(obj, file)
                
                elif filetype == 3:
                    cmds.FBXExport("-f", file, "-s")
        
        # Print result
        message = f"# Result: Exported {objCount} {fileFormat} file{'s' if objCount > 1 else ''} in {directory.as_posix()}"
        GN_Print.GN_Print(message, deferred=True)
    
    if useDuplicate:
        # Delete duplicate objects
        cmds.delete(objects)
        
        # Rename original objects
        for i in range(objCount):
            dag = objList.getDagPath(i)
            object = dag.fullPathName()
            cmds.rename(object, nameList[i][0])
        
        # Remove GN_Export namespace
        if not namespaceExport:
            cmds.namespace(mnr=True, rm="GN_Export")
        
        # Restore namespace
        if namespace:
            cmds.namespace(set=namespace)
    
    # Restore selection
    cmds.select(selection, r=True)
    
    # Print issues
    if len(geoIssues):
        GN_Print.GN_Print("\nObjects with geometry issue:", deferred=True)
        GN_Print.GN_Print(geoIssues, deferred=True)
        GN_Print.GN_Print("", deferred=True)
        GN_Print.GN_Print("Found objects with geometry issue. (List in script editor)", mode='WARNING', deferred=True)


# Create window
class GN_Export(object):
    def __init__(self, optionBox=False, *args, **kwargs):
        # Create default variables
        self.pfx = "GNE_"
        self.windowName = self.pfx + "window"
        self.windowSizeMenuItem = self.pfx + "saveWindowSize_menuItem"
        
        self.windowTitle = "GN Export"
        self.runLabel = "Export"
        self.windowSize = [546, 350]
        
        # Create option variables
        self.saveWindowSize = self.pfx + "saveWindowSize"
        self.mode = self.pfx + "mode"
        self.filetype = self.pfx + "filetype"
        self.meshIntegrity = self.pfx + "meshIntegrity"
        self.uvSets = self.pfx + "uvSets"
        self.freezeTransforms = self.pfx + "freezeTransforms"
        self.combine = self.pfx + "combine"
        self.removeSets = self.pfx + "removeSets"
        self.vertexColor = self.pfx + "vertexColor"

        # Create window or run command
        if optionBox:
            self.createWindow()
        elif optionBox is not None:
            self.runCmd(closeWindow=False, **kwargs)
        
    # Help command
    def helpCmd(self, *args):
        open_new_tab("https://gabrielnadeau.com/pages/gn-zbrushmaya-importexport-tool")
    
    # Run command
    def runCmd(self, closeWindow=False, **kwargs):
        # Get option variables
        self.defaultSettings(reset=False)
        
        if "filetype" in kwargs:
            filetype = kwargs["filetype"]
        else:
            filetype = cmds.optionVar(q="GNIE_filetype")

        # Export
        GN_PerformExport(filetype)
        
        # Close window if specified
        if closeWindow:
            self.closeWindow()
    
    def sync(self):
        if cmds.window("GNI_window", ex=True):
            from ..GN_scripts import GN_Import
            GN_Import.GN_Import(optionBox=None).windowSetup()
    
    # Close window
    def closeWindow(self):
        if cmds.window(self.windowName, ex=True):
            cmds.evalDeferred('import maya.cmds as cmds; cmds.deleteUI("'+self.windowName+'", wnd=True)')

    # Window size
    def resizeWindow(self):
        if cmds.optionVar(q=self.saveWindowSize) == 0:
            cmds.window(self.windowName, e=True, wh=self.windowSize)

    # Default settings
    def defaultSettings(self, reset=False):
        if cmds.optionVar(ex=self.saveWindowSize) == 0:
            cmds.optionVar(iv=(self.saveWindowSize, 1))
        if reset or cmds.optionVar(ex="GNIE_mode") == 0:
            cmds.optionVar(iv=("GNIE_mode", 1))
        if reset or cmds.optionVar(ex="GNIE_filetype") == 0:
            cmds.optionVar(iv=("GNIE_filetype", 1))
        if reset or cmds.optionVar(ex=self.meshIntegrity) == 0:
            cmds.optionVar(iv=(self.meshIntegrity, 2))
        if reset or cmds.optionVar(ex=self.uvSets) == 0:
            cmds.optionVar(iv=(self.uvSets, 2))
        if reset or cmds.optionVar(ex=self.freezeTransforms) == 0:
            cmds.optionVar(iv=(self.freezeTransforms, 1))
        if reset or cmds.optionVar(ex=self.combine) == 0:
            cmds.optionVar(iv=(self.combine, 1))
        if reset or cmds.optionVar(ex=self.removeSets) == 0:
            cmds.optionVar(iv=(self.removeSets, 1))
        if reset or cmds.optionVar(ex="GNIE_vertexColor") == 0:
            cmds.optionVar(iv=("GNIE_vertexColor", 0))
        
    # Reset settings
    def resetSettings(self, sync=False, *args):
        self.defaultSettings(reset=True)
        self.windowSetup()
        if sync:
            self.sync()

    # Save settings
    def saveSettings(self, sync=False, *args):
        cmds.optionVar(iv=(self.saveWindowSize, cmds.menuItem(self.windowSizeMenuItem, q=True, cb=True)))
        mode = cmds.radioButtonGrp(self.mode, q=True, sl=True)
        cmds.optionVar(iv=("GNIE_mode", mode))
        filetype = cmds.optionMenu(self.filetype, q=True, sl=True)
        cmds.optionVar(iv=("GNIE_filetype", filetype))
        cmds.optionVar(iv=(self.meshIntegrity, cmds.radioButtonGrp(self.meshIntegrity, q=True, sl=True)))
        cmds.optionVar(iv=(self.uvSets, cmds.radioButtonGrp(self.uvSets, q=True, sl=True)))
        cmds.optionVar(iv=(self.freezeTransforms, cmds.checkBoxGrp(self.freezeTransforms, q=True, v1=True)))
        cmds.optionVar(iv=(self.combine, cmds.checkBoxGrp(self.combine, q=True, v1=True)))
        cmds.optionVar(iv=(self.removeSets, cmds.checkBoxGrp(self.removeSets, q=True, v1=True)))
        cmds.optionVar(iv=("GNIE_vertexColor", cmds.checkBoxGrp(self.vertexColor, q=True, v1=True)))
        
        if filetype == 1:
            cmds.radioButtonGrp(self.uvSets, e=True, vis=True)
            cmds.checkBoxGrp(self.freezeTransforms, e=True, vis=True)
            cmds.checkBoxGrp(self.removeSets, e=True, vis=False)
            cmds.checkBoxGrp(self.vertexColor, e=True, vis=False)
            if mode == 1:
                cmds.checkBoxGrp(self.combine, e=True, vis=True)
            else:
                cmds.checkBoxGrp(self.combine, e=True, vis=False)
        elif filetype == 2:
            cmds.radioButtonGrp(self.uvSets, e=True, vis=False)
            cmds.checkBoxGrp(self.freezeTransforms, e=True, vis=False)
            cmds.checkBoxGrp(self.combine, e=True, vis=False)
            cmds.checkBoxGrp(self.removeSets, e=True, vis=True)
            cmds.checkBoxGrp(self.vertexColor, e=True, vis=True)
        elif filetype == 3:
            cmds.radioButtonGrp(self.uvSets, e=True, vis=False)
            cmds.checkBoxGrp(self.freezeTransforms, e=True, vis=True)
            cmds.checkBoxGrp(self.combine, e=True, vis=False)
            cmds.checkBoxGrp(self.removeSets, e=True, vis=False)
            cmds.checkBoxGrp(self.vertexColor, e=True, vis=False)
        
        if sync:
            self.sync()
        
    # Setup window
    def windowSetup(self):
        cmds.menuItem(self.windowSizeMenuItem, e=True, cb=cmds.optionVar(q=self.saveWindowSize))
        cmds.radioButtonGrp(self.mode, e=True, sl=cmds.optionVar(q="GNIE_mode"))
        cmds.optionMenu(self.filetype, e=True, sl=cmds.optionVar(q="GNIE_filetype"))
        cmds.radioButtonGrp(self.meshIntegrity, e=True, sl=cmds.optionVar(q=self.meshIntegrity))
        cmds.radioButtonGrp(self.uvSets, e=True, sl=cmds.optionVar(q=self.uvSets))
        cmds.checkBoxGrp(self.freezeTransforms, e=True, v1=cmds.optionVar(q=self.freezeTransforms))
        cmds.checkBoxGrp(self.combine, e=True, v1=cmds.optionVar(q=self.combine))
        cmds.checkBoxGrp(self.removeSets, e=True, v1=cmds.optionVar(q=self.removeSets))
        cmds.checkBoxGrp(self.vertexColor, e=True, v1=cmds.optionVar(q="GNIE_vertexColor"))
        self.saveSettings()
    
    def initializeWindow(self):
        cmds.showWindow(self.windowName)
        self.resizeWindow()
        cmds.setFocus(self.windowName)
    
    # Create window
    def createWindow(self):
        # If window already opened, set focus on it
        if cmds.window(self.windowName, ex=True) is True:
            self.initializeWindow()
            return
        
        # Window
        cmds.window(self.windowName, t=self.windowTitle, mb=True, wh=self.windowSize)
        
        # Edit Menu
        cmds.menu(l="Edit")
        cmds.menuItem(l="Save Settings", c=partial(self.saveSettings), ecr=False)
        cmds.menuItem(l="Reset Settings", c=partial(self.resetSettings, True), ecr=False)
        cmds.menuItem(d=True)
        cmds.menuItem(self.windowSizeMenuItem, l="Save Window Size", c=partial(self.saveSettings), cb=False, ecr=False)
        cmds.setParent("..")	
        # Help Menu
        cmds.menu(l="Help", helpMenu=True)
        cmds.menuItem(l="Help on "+self.windowTitle, i="help.png", c=partial(self.helpCmd), ecr=False)
        cmds.setParent("..")
        
        # Window Form (START)
        cmds.formLayout(self.pfx+"window_formLayout")
        # Tab Layout (START)
        cmds.tabLayout(self.pfx+"window_tabLayout", tv=False)
        cmds.formLayout(self.pfx+"scroll_formLayout")
        # Scroll Layout (START)
        cmds.scrollLayout(self.pfx+"settings_scrollLayout", cr=True)
        cmds.formLayout(self.pfx+"settings_formLayout")
        
        # Settings Frame (START)
        cmds.frameLayout(self.pfx+"settings_frameLayout", cll=True, l="Settings", li=5, bgs=True, mh=4, mw=0)
        # Settings Column (START)
        cmds.columnLayout(adj=1)
        
        # Mode
        cmds.radioButtonGrp(self.mode, nrb=2, l="Mode:  ", la2=("Single-File", "Multi-File"), cc=partial(self.saveSettings, True))
        
        # File type
        cmds.rowLayout(nc=2, cw=(1, 138), cat=(1, "right", 4), ct2=("left", "left"))
        cmds.text(l="File type:")
        cmds.optionMenu(self.filetype, w=124, cc=partial(self.saveSettings, True))
        cmds.menuItem(l="Maya ASCII")
        cmds.menuItem(l="OBJ")
        cmds.menuItem(l="FBX")
        cmds.setParent("..")
        
        # Separation
        cmds.rowLayout(h=3)
        cmds.setParent("..")
        cmds.rowLayout(h=2, bgc=[0.266, 0.266, 0.266])
        cmds.setParent("..")
        cmds.rowLayout(h=3)
        cmds.setParent("..")
        
        # Options
        cmds.radioButtonGrp(self.meshIntegrity, nrb=3, l="Mesh Integrity:  ", la3=("Ignore", "Check Mesh", "Fix Mesh"), cc=partial(self.saveSettings))
        cmds.radioButtonGrp(self.uvSets, nrb=3, l="UV Sets:  ", la3=("Keep All", "Keep Current", "Keep First"), cc=partial(self.saveSettings))
        cmds.checkBoxGrp(self.freezeTransforms, l1="Freeze Transformations", cat=(1, "left", 143), cc=partial(self.saveSettings))
        cmds.checkBoxGrp(self.combine, l1="Combine Objects", cat=(1, "left", 143), cc=partial(self.saveSettings))
        cmds.checkBoxGrp(self.removeSets, l1="Remove Sets", cat=(1, "left", 143), cc=partial(self.saveSettings))
        cmds.checkBoxGrp(self.vertexColor, l1="Vertex Color", cat=(1, "left", 143), cc=partial(self.saveSettings, True))
        
        # Settings Column (END)
        cmds.setParent("..")
        # Settings Frame (END)
        cmds.setParent("..")
        # Scroll Layout (END)
        cmds.setParent("..")
        cmds.setParent("..")
        # Tab Layout (END)
        cmds.setParent("..")
        cmds.setParent("..")
        
        # Buttons
        cmds.formLayout(self.pfx+"buttons_formLayout", nd=150)
        cmds.iconTextButton(self.pfx+"applyAndClose_button", st="textOnly", l=self.runLabel, c=partial(self.runCmd, closeWindow=True), fla=False, h=26, rpt=True)
        cmds.iconTextButton(self.pfx+"apply_button", st="textOnly", l="Apply", c=partial(self.runCmd, closeWindow=False), fla=False, h=26, rpt=True)
        cmds.iconTextButton(self.pfx+"close_button", st="textOnly", l="Close", c=partial(self.closeWindow), fla=False, h=26, rpt=True)
        cmds.setParent("..")
        
        # Window Form (END)
        cmds.setParent("..")
        
        # Window Form Layout
        cmds.formLayout(self.pfx+"window_formLayout", e=True,
            af=[(self.pfx+"window_tabLayout", "top", 0), (self.pfx+"window_tabLayout", "left", 0), (self.pfx+"window_tabLayout", "right", 0), (self.pfx+"window_tabLayout", "bottom", 36)])
        
        cmds.formLayout(self.pfx+"window_formLayout", e=True,
            ac=(self.pfx+"buttons_formLayout", "top", 5, self.pfx+"window_tabLayout"),
            af=[(self.pfx+"buttons_formLayout", "left", 5), (self.pfx+"buttons_formLayout", "right", 5)],
            an=(self.pfx+"buttons_formLayout", "bottom"))
        
        # Scroll Form Layout
        cmds.formLayout(self.pfx+"scroll_formLayout", e=True,
            af=[(self.pfx+"settings_scrollLayout", "top", 2), (self.pfx+"settings_scrollLayout", "left", 2), (self.pfx+"settings_scrollLayout", "right", 2), (self.pfx+"settings_scrollLayout", "bottom", 2)])
        
        # Settings Form Layout
        cmds.formLayout(self.pfx+"settings_formLayout", e=True,
            af=[(self.pfx+"settings_frameLayout", "top", 0), (self.pfx+"settings_frameLayout", "left", 0), (self.pfx+"settings_frameLayout", "right", 0)],
            an=(self.pfx+"settings_frameLayout", "bottom"))
        
        # Buttons Form Layout
        cmds.formLayout(self.pfx+"buttons_formLayout", e=True,
            af=[(self.pfx+"applyAndClose_button", "top", 0), (self.pfx+"applyAndClose_button", "left", 0)],
            ap=(self.pfx+"applyAndClose_button", "right", 2, 50),
            an=(self.pfx+"applyAndClose_button", "bottom"))
        
        cmds.formLayout(self.pfx+"buttons_formLayout", e=True,
            af=(self.pfx+"apply_button", "top", 0),
            ap=[(self.pfx+"apply_button", "left", 2, 50), (self.pfx+"apply_button", "right", 2, 100)],
            an=(self.pfx+"apply_button", "bottom"))
            
        cmds.formLayout(self.pfx+"buttons_formLayout", e=True,
            af=[(self.pfx+"close_button", "top", 0), (self.pfx+"close_button", "right", 0)],
            ap=(self.pfx+"close_button", "left", 2, 100),
            an=(self.pfx+"close_button", "bottom"))
        
        # Window Setup
        self.defaultSettings(reset=False)
        self.windowSetup()
        self.initializeWindow()