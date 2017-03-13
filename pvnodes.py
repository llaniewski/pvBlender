import bpy
import nodeitems_utils
import paraview
import paraview.simple
import paraview.servermanager

from .nodedata import pvDataNode
from . import category


class pvPropName(bpy.types.PropertyGroup):
    s = bpy.props.StringProperty()
    def draw(self, context, layout):
        layout.prop(self, "s")

class pvPropBase(pvDataNode):
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
    if type(prop) == paraview.servermanager.VectorProperty:
        if len(prop) == 0:
            return bpy.props.FloatProperty(default=0.0)
        if type(prop[0]) == float:
            if len(prop) == 1:
                return bpy.props.FloatProperty(default=prop[0])
            return bpy.props.FloatVectorProperty(size=len(prop))
        if type(prop[0]) == bool:
            if len(prop) == 1:
                return bpy.props.BoolProperty(default=prop[0])
            return bpy.props.BoolVectorProperty(size=len(prop))
        if type(prop[0]) == int:
            if len(prop) == 1:
                return bpy.props.IntProperty(default=prop[0])
            return bpy.props.IntVectorProperty(size=len(prop))
        
    return bpy.props.StringProperty(default=str(type(prop)))
#    ret = bpy.props.PointerProperty(type=pvPropString,name=p)
#    ret = bpy.props.PointerProperty(type=pvPropFloat,name=p)
#    ret.propertyId = p
#    return ret

class pvNode(pvDataNode):
    bl_label = "General pv node"
    propertyNames = bpy.props.CollectionProperty(type=pvPropName)
    def init(self, context):
        print("Init ",self.bl_label)
        self.load_data()
        self.pv_props()
        self.outputs.new("pvNodeSocket", "Output")
    def free(self):
        self.free_data()
    def draw_buttons(self, context, layout):
        layout.label(type(self).__name__)
        for n in self.propertyNames:
            p = n.s
            if hasattr(self,p):
                pr = getattr(self,p)
                if isinstance(pr,pvPropBase):
                    pr.draw(layout,p)
                else:
                    layout.prop(self,p)
    def init_data(self):
        self.data.pv = getattr(sys.modules["paraview.simple"],self.pvType)()
    def pv_props(self):
        op = {str(n) for n in self.data.pv.ListProperties()}
        ap = {str(n.s) for n in self.propertyNames}
        mp = {p for p in ap if hasattr(type(self),p)}
        sp = {p.name for p in self.inputs}
        ip = set()
        pp = op - mp - sp
        if len(pp) > 0:
            print("Adding to",self.bl_label,"properties:",pp)
        for p in pp:
            prop = self.data.pv.GetProperty(p)
            if type(prop) == paraview.servermanager.InputProperty:
                ip.add(p)
            else:
                setattr(type(self),p,create_pv_prop(prop,p))    
                if p not in ap:
                    it = self.propertyNames.add()
                    it.s = p
        # Adding inputs later, because it triggers update
        if len(ip) > 0:
            print("Adding to",self.bl_label,"inputs:",ip)
        for i in ip:
            self.inputs.new("pvNodeSocket", i)
    def update(self):
        print("Update ",self.bl_label)
        self.load_data()
        self.pv_props()

import sys

my_pvClasses = []

from bpy.app.handlers import persistent

def register():
    global my_pvClasses, vtknodes_tmp_mesh
    print("------------------------- REGISTER PV -------------------")
    bpy.utils.register_class(pvPropName)
    bpy.utils.register_class(pvPropString)
    bpy.utils.register_class(pvPropFloat)

    def pvClasses(mod):
        mylist = [i for i in dir(mod) if i[0] != "_"]
        retlist = []
        for k in mylist:
            c = "pvSimple" + k
            if c not in my_pvClasses:
                print("adding class ",c,"with object", k)
                new_class = type(c, (bpy.types.Node,pvNode), {
                    "bl_label": k,
                    "pvType": k
                })
                bpy.utils.register_class(new_class)
                setattr(sys.modules[__name__], c,new_class)
                my_pvClasses.append(c)
            retlist.append(nodeitems_utils.NodeItem(c))
        return(retlist)
        
    categories = [
      category.pvNodeCategory("BVTK_SOURCES", "Sources",
        items = pvClasses(paraview.servermanager.sources)),
      category.pvNodeCategory("BVTK_FILTERS", "Filters",
        items = pvClasses(paraview.servermanager.filters)),
      category.pvNodeCategory("BVTK_WRITERS", "Writers",
        items = pvClasses(paraview.servermanager.writers)),
    ]

    nodeitems_utils.register_node_categories("BVTK_CATEGORIES", categories)
    

def unregister():
    global my_pvClasses
    print("------------------------- UNREGISTER PV -------------------")
    bpy.utils.unregister_class(pvPropName)
    bpy.utils.unregister_class(pvPropString)
    bpy.utils.unregister_class(pvPropFloat)
    for c in my_pvClasses:
        new_class = getattr(sys.modules[__name__], c)
        if isinstance(new_class,type):
            print("unregistering: ",c)
            bpy.utils.unregister_class(new_class)
        else:
            print(c,"is not a class")
    my_pvClasses = []
    nodeitems_utils.unregister_node_categories("BVTK_CATEGORIES")


