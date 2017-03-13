import bpy
import paraview
import paraview.simple
import paraview.servermanager

vtknodes_tmp_mesh = {}

def PolyDataMesh(pdata, ob):
        print("replace mesh ...")
        me = ob.data
        ob.data = vtknodes_tmp_mesh
        bpy.data.meshes.remove(me)
        me = bpy.data.meshes.new(ob.name + "Mesh")
        ob.data = me
        verts = []
        faces = []
        for i in range(pdata.GetNumberOfPoints()):
            point = pdata.GetPoint(i)
            verts.append([point[0],point[1],point[2]])
        for i in range(pdata.GetNumberOfCells()):
            cell = pdata.GetCell(i)
            if pdata.GetCellType(i)==5:
                faces.append([cell.GetPointId(0),cell.GetPointId(1),cell.GetPointId(2)])
            if pdata.GetCellType(i)==9:
                faces.append([cell.GetPointId(0),cell.GetPointId(1),cell.GetPointId(2),cell.GetPointId(3)])
        me.from_pydata(verts, [], faces)
        print("replaced ...")
        bpy.context.scene.objects.active = ob    

def post_init(something):
    global vtknodes_tmp_mesh
    if "vtknodes_tmp_mesh" in bpy.data.meshes:
        vtknodes_tmp_mesh = bpy.data.meshes["vtknodes_tmp_mesh"]
    else:
        vtknodes_tmp_mesh = bpy.data.meshes.new("vtknodes_tmp_mesh")
