import bpy

bl_info = {
  "name": "VTK nodes",
  "category": "Node",
    "author":      "Lukasz Laniewski-Wollk",
    "version":     (0, 1, 0),
    "blender":     (2, 80, 0),
    "location":    "VTK Nodes",
    "category":    "Node",
    "warning":     "This version is still in development."
}

import paraview
import paraview.simple
import paraview.servermanager

class pvNodeTree(bpy.types.NodeTree):
  bl_description = "VTK Node Tree"
  bl_icon = "MESH_TORUS"
  bl_label = "VTK node tree"

class pvNodeSocket(bpy.types.NodeSocket):
  bl_label = "VTK Node Socket"
  def draw(self, context, layout, node, x):
    layout.label(text=self.name)
  def draw_color(self, context, node):
    return (1,1,1,1)

from .nodedata import pvDataNode

from .category import pvNodeCategory

from bpy.app.handlers import persistent

from . import pvnodes,inspector,object,polydata

@persistent
def pv_load_post(something):
    print("------------------------- POST LOAD  -------------------")
    if 'ParaViewState' in bpy.data.texts:
      data = bpy.data.texts['ParaViewState'].as_string()
      with open('_tmp.xml', 'w') as file:
        file.write(data)
      paraview.simple.LoadState("_tmp.xml")
    else:
      bpy.data.texts.new('ParaViewState')
    for g in bpy.data.node_groups:
        if type(g) == pvNodeTree:
            for n in g.nodes:
                n.update()

@persistent
def pv_save_pre(something):
    print("------ pvBlender: pre_save")
    paraview.simple.SaveState("_tmp.xml")
    with open('_tmp.xml', 'r') as file:
      data = file.read()
    bpy.data.texts['ParaViewState'].from_string(data)

def register():
    global my_pvClasses, vtknodes_tmp_mesh
    print("------ pvBlender: register plugin")
    bpy.utils.register_class(pvNodeTree)
    bpy.utils.register_class(pvNodeSocket)
    pvnodes.register()
    inspector.register()
    object.register()
    if not pv_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(pv_load_post)
    if not pv_save_pre in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(pv_save_pre)
    

def unregister():
    global my_pvClasses
    print("------ pvBlender: unregister plugin")
    pvnodes.unregister()
    inspector.unregister()
    object.unregister()
    bpy.utils.unregister_class(pvNodeTree)
    bpy.utils.unregister_class(pvNodeSocket)

