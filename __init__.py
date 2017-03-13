import bpy
from bpy.props import IntProperty, FloatProperty, PointerProperty
import nodeitems_utils
from nodeitems_utils import NodeItem, NodeCategory

import uuid

bl_info = {
  "name": "VTK nodes",
  "category": "Node",
}

#from paraview.simple import *
#from paraview import simple, servermanager
import paraview
import paraview.simple
import paraview.servermanager

tmp_data_table = {}

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

class bvtkNodeTree(bpy.types.NodeTree):
  bl_description = "VTK Node Tree"
  bl_icon = "MESH_TORUS"
  bl_label = "VTK node tree"

class bvtkNodeSocket(bpy.types.NodeSocket):
  bl_label = "VTK Node Socket"
  def draw(self, context, layout, node, x):
    layout.label(self.name)
  def draw_color(self, context, node):
    return (1,1,1,1)

class bvtpData():
#    def __init__(self):
#        print("----- Creating data object ----");
#    def __del__(self):
#        print("----- Deleting data object ----");
    pass

class bvtkDataNode():
    dataId = bpy.props.StringProperty(default="")
    def init_data(self):
        print("### Running generic init_data ",self.dataId);
    def load_data(self):
        if self.dataId == "":  # no data yet
            self.dataId = str(uuid.uuid1()) + self.name
        if self.dataId not in tmp_data_table:
            print("[pv:DATA] Create data[",self.dataId,"]")
            self.data = bvtpData()
            tmp_data_table[self.dataId] = self.data
            self.init_data()
        print("[pv:DATA] Getting data[",self.dataId,"]")
        self.data = tmp_data_table[self.dataId]
        return (self.data)
    def free_data(self):
        if self.dataId == "":  # no data yet
            return
        if self.dataId not in tmp_data_table:
            return
        print("[pv:DATA] Delete data[",self.dataId,"]")
        del tmp_data_table[self.dataId]

class pvInt(bpy.types.PropertyGroup):
    i = IntProperty()
    def draw(self, context, layout):
        layout.prop(self, "i")

class pvFloat(bpy.types.PropertyGroup):
    f = FloatProperty()
    def draw(self, context, layout):
        layout.prop(self, "f")

class pvPropertyUnion(bpy.types.PropertyGroup,bvtkDataNode):
    def update(self,context):
        print(self.propertyId,"updated")
    propertyId = bpy.props.StringProperty(default="")
    labelStr = bpy.props.StringProperty(default="")
    ints = bpy.props.CollectionProperty(type=pvInt)
    floats = bpy.props.CollectionProperty(type=pvFloat)
    def draw(self, context, layout):
        split = layout.split()
        col = split.column()
        col.label(self.propertyId)
        col.label(self.labelStr)
        col = split.column()
        for item in self.ints:
            item.draw(context, col)
        for item in self.floats:
            item.draw(context, col)
#        item = setattr(self, propertyId)
#        layout.label(self.name)
#        layout.prop(self,self.propertyId)
    
    def init(self):
        self.load_data()
        prop = self.data.pv.GetProperty(self.propertyId)
        self.labelStr = str(type(prop[0]))
        if type(prop) == paraview.servermanager.VectorProperty:
            for i in prop:
                v = self.floats.add()
                v.update=lambda s,c: self.update(s,c)
                v = i
    def getType(self):
        self.load_data()
        prop = self.data.pv.GetProperty(self.propertyId)
        return(type(prop))
#        print("setattr: ",pvPropertyUnion, self.propertyId)
#        setattr(pvPropertyUnion, self.propertyId, FloatProperty())
    

class pvPropName(bpy.types.PropertyGroup):
    s = bpy.props.StringProperty()
    def draw(self, context, layout):
        layout.prop(self, "s")

class pvPropBase(bvtkDataNode):
    propertyId = bpy.props.StringProperty(default="")
    def update(self,context):
        print(self.propertyId,"updated")
    def load_prop(self):
        self.load_data()
        self.prop = self.data.pv.GetProperty(self.propertyId)

class pvPropString(bpy.types.PropertyGroup,pvPropBase):
    v = bpy.props.StringProperty()
    def read(self):
        self.load_prop()
    def draw(self, layout, p):
        layout.prop(self, "v",text=p)

class pvPropFloat(bpy.types.PropertyGroup,pvPropBase):
    v = bpy.props.FloatProperty()
    def read(self):
        self.load_prop()
    def draw(self, layout, p):
        layout.prop(self, "v",text=p)


def create_pv_prop(prop, p):
#    if type(prop) == paraview.servermanager.VectorProperty:
#        if len(prop) == 0:
#            return bpy.props.FloatProperty(default=0.0)
#        if len(prop) == 1:
#            return bpy.props.FloatProperty(default=prop[0])
#        return bpy.props.FloatVectorProperty(size=len(prop))
#    return (bpy.props.StringProperty(default=str(type(prop))))
#    ret = bpy.props.PointerProperty(type=pvPropString,name=p)
    ret = bpy.props.PointerProperty(type=pvPropFloat,name=p)
#    ret.propertyId = p
    return ret

class pvNode(bvtkDataNode):
    bl_label = "General pv node"
    #pvType = "None"
    #custom_properties = bpy.props.CollectionProperty(type=pvPropertyUnion)
    propertyNames = bpy.props.CollectionProperty(type=pvPropName)
    #propertyName = bpy.props.StringProperty(default="")
    def init(self, context):
        print("Init ",self.bl_label)
        self.load_data()
        self.pv_props()
        self.outputs.new("bvtkNodeSocket", "Output")
#        for p in self.data.pv.ListProperties():
#            item = self.custom_properties.add()
#            item.propertyId = p
#            item.dataId = self.dataId
#            item.init()
#            if item.getType() == paraview.servermanager.InputProperty:
#                sock = self.inputs.new("bvtkNodeSocket", p)
#                sock.value_property = item
    def free(self):
        self.free_data()
    def draw_buttons(self, context, layout):
        layout.label(type(self).__name__)
        for n in self.propertyNames:
            p = n.s
            if hasattr(self,p):
                pr = getattr(self,p)
                pr.draw(layout,p)
#                layout.prop(self,p)
    def init_data(self):
        self.data.pv = getattr(sys.modules["paraview.simple"],self.pvType)()
    def pv_props(self):
        op = {str(n) for n in self.data.pv.ListProperties()}
        ap = {str(n.s) for n in self.propertyNames}
        mp = {p for p in ap if hasattr(type(self),p)}
        sp = {p.name for p in self.inputs}
        print(sp)
        for p in (op - mp - sp):
            if p not in ap:
                it = self.propertyNames.add()
                it.s = p
            self.pv_add_prop(p)
    def pv_add_prop(self,p):
        print("Adding ",p," to ",self.bl_label)
        prop = self.data.pv.GetProperty(p)
        if type(prop) == paraview.servermanager.InputProperty:
            sock = self.inputs.new("bvtkNodeSocket", p)
        else:
            setattr(type(self),p,create_pv_prop(prop,p))
    def update(self):
        print("Update ",self.bl_label)
        self.load_data()
        self.pv_props()

class bvtkNodeCategory(NodeCategory):
  @classmethod
  def poll(cls, context):
    return context.space_data.tree_type == "bvtkNodeTree"


import sys

my_pvClasses = []

from bpy.app.handlers import persistent

@persistent
def post_init(something):
    global my_pvClasses, vtknodes_tmp_mesh
    print("------------------------- POST INIT  -------------------")
    if "vtknodes_tmp_mesh" in bpy.data.meshes:
        vtknodes_tmp_mesh = bpy.data.meshes["vtknodes_tmp_mesh"]
    else:
        vtknodes_tmp_mesh = bpy.data.meshes.new("vtknodes_tmp_mesh")
    for g in bpy.data.node_groups:
        print(g)
        if type(g) == bvtkNodeTree:
            for n in g.nodes:
                n.update()

def post_init_once(something):
    if post_init_once in bpy.app.handlers.scene_update_post:
        bpy.app.handlers.scene_update_post.remove(post_init_once)
    post_init(something)



def register():
    global my_pvClasses, vtknodes_tmp_mesh
    print("------------------------- REGISTER PV -------------------")

    bpy.utils.register_class(pvInt)
    bpy.utils.register_class(pvFloat)
    bpy.utils.register_class(pvPropertyUnion)
    bpy.utils.register_class(pvPropName)
#    bpy.utils.register_class(pvPropBase)
    bpy.utils.register_class(pvPropString)
    bpy.utils.register_class(pvPropFloat)
    bpy.utils.register_class(bvtkNodeTree)
    bpy.utils.register_class(bvtkNodeSocket)

    def pvClasses(mod):
        mylist = [i for i in dir(mod) if i[0] != "_"]
        retlist = []
        for k in mylist:
            c = "pv" + k
            if c not in my_pvClasses:
                print("adding class ",c,"with object", k)
                new_class = type(c, (bpy.types.Node,pvNode), {
                    "bl_label": k,
                    "pvType": k
                })
                bpy.utils.register_class(new_class)
                setattr(sys.modules[__name__], c,new_class)
                my_pvClasses.append(c)
            retlist.append(NodeItem(c))
        return(retlist)
        
    categories = [
      bvtkNodeCategory("BVTK_SOURCES", "Sources",
        items = pvClasses(paraview.servermanager.sources)),
      bvtkNodeCategory("BVTK_FILTERS", "Filters",
        items = pvClasses(paraview.servermanager.filters)),
      bvtkNodeCategory("BVTK_WRITERS", "Writers",
        items = pvClasses(paraview.servermanager.writers)),
    ]
    #for k in mylist:
    #    c = "pv" + k
    #    bpy.utils.register_class(getattr(sys.modules[__name__], c))

#    bpy.utils.register_class(bvtkCubeNode)
#    bpy.utils.register_class(bvtkReaderNode)
#    bpy.utils.register_class(bvtkMarchingCubes)
#    bpy.utils.register_class(bvtkObjectNode)
    nodeitems_utils.register_node_categories("BVTK_CATEGORIES", categories)
    if not post_init in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(post_init)
    if not post_init_once in bpy.app.handlers.scene_update_post:
        bpy.app.handlers.scene_update_post.append(post_init_once)
    

def unregister():
    global my_pvClasses
    print("------------------------- UNREGISTER PV -------------------")
    bpy.utils.unregister_class(pvInt)
    bpy.utils.unregister_class(pvFloat)
    bpy.utils.unregister_class(pvPropertyUnion)
#    bpy.utils.unregister_class(pvPropBase)
    bpy.utils.unregister_class(pvPropName)
    bpy.utils.unregister_class(pvPropString)
    bpy.utils.unregister_class(pvPropFloat)
    bpy.utils.unregister_class(bvtkNodeTree)
    bpy.utils.unregister_class(bvtkNodeSocket)
    for c in my_pvClasses:
        new_class = getattr(sys.modules[__name__], c)
        if isinstance(new_class,type):
            print("unregistering: ",c)
            bpy.utils.unregister_class(new_class)
        else:
            print(c,"is not a class")
    my_pvClasses = []
#    bpy.utils.unregister_class(bvtkCubeNode)
#    bpy.utils.unregister_class(bvtkReaderNode)
#    bpy.utils.unregister_class(bvtkMarchingCubes)
#    bpy.utils.unregister_class(bvtkObjectNode)
    nodeitems_utils.unregister_node_categories("BVTK_CATEGORIES")


