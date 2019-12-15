import bpy
import nodeitems_utils
import paraview
import paraview.simple
import paraview.servermanager
import paraview.modules.vtkPVServerManagerCorePython as vtkPVServerManagerCorePython
import uuid
from .nodedata import pvDataNode
from . import category

class pvPropNameType(bpy.types.PropertyGroup):
    propName : bpy.props.StringProperty()
    layoutType : bpy.props.StringProperty()
    sceneProp : bpy.props.StringProperty()

def sm_prop(proxyName,propName):
    return paraview.simple.FindSource(proxyName).GetProperty(propName).SMProperty

def sm_set(self,proxyName,propName,value):
    prop = sm_prop(proxyName,propName)
    prop.SetElement(0, value)
    prop.GetParent().UpdateSelfAndAllInputs()

def sm_get(self,proxyName,propName):
    prop = sm_prop(proxyName,propName)
    ret = prop.GetElement(0)
    return ret

def sm_set_v(self,proxyName,propName,value):
    prop = sm_prop(proxyName,propName)
    n = prop.GetNumberOfElements()
    for i in range(n) :
        prop.SetElement(i, value[i])
    prop.GetParent().UpdateSelfAndAllInputs()

def sm_get_elements(prop):
    n = prop.GetNumberOfElements()
    return [ prop.GetElement(i) for i in range(n) ]

def sm_get_v(self,proxyName,propName):
    prop = sm_prop(proxyName,propName)
    ret = sm_get_elements(prop)
    return ret

def sm_describe(prop):
    dom = get_prop_domains(prop)
    ret=""
    if "GetNumberOfElements" in dir(prop):
        ret = ret + str(prop.GetNumberOfElements()) + ":"
    ret = ret + str(type(prop)) + str([str(type(d)) for d in dom])
    return ret

def sm_get_items(proxyName,propName):
    prop = sm_prop(proxyName,propName)
    dom = get_prop_domains(prop)
    ret = sm_get_strings(dom[0])
    ret = [ (s,s,s) for s in ret ]
    return ret

def sm_set_arraylist(self,proxyName,propName,value):
    prop = sm_prop(proxyName,propName)
    dom = get_prop_domains(prop)
    ret = sm_get_strings(dom[0])
    print("set:" + str(value))
    if value > 0:
        s = ret[value-1]
        prop.SetElement(4, s)
    else:
        prop.SetElement(4, None)
    prop.GetParent().UpdateSelfAndAllInputs()

def sm_get_arraylist(self,proxyName,propName):
    prop = sm_prop(proxyName,propName)
    dom = get_prop_domains(prop)
    ret = sm_get_strings(dom[0])
    val = prop.GetElement(4)
    try:
        i = ret.index(val)+1
    except ValueError:
        i = 0
    return i

def sm_get_strings(d):
    n = d.GetNumberOfStrings()
    ret = [ d.GetString(i) for i in range(n) ]
    return ret



def dbg_set(self,proxyName,propName,value):
    pass

def dbg_get(self,proxyName,propName):
    prop = sm_prop(proxyName,propName)
    return sm_describe(prop)


def prop_domains(prop):
    i = prop.NewDomainIterator()
    while i.GetKey() is not None:
        yield i.GetDomain()
        i.Next()

def get_prop_domains(prop):
    return [d for d in prop_domains(prop)]

class ArraySelectionElement(bpy.types.PropertyGroup):
    name : bpy.props.BoolProperty(name="selected")


def test_set(self,value):
    print("set(" + str(type(self)) + ") = " + str(value))
    #self["pv_a"] = value
def test_get(self):
#    print("get self:" +str(type(self)))
    return 0#self["pv_a"]

class DoubleArrayElement(bpy.types.PropertyGroup):
    val : bpy.props.FloatProperty(set=test_set, get=test_get )

class AddButtonOperator(bpy.types.Operator):
    bl_idname = "pvblender.my_add_button_operator"
    bl_label = "Add Button"
    proxyName : bpy.props.StringProperty()
    propName  : bpy.props.StringProperty()
    sceneProp : bpy.props.StringProperty()
    def execute(self, context):
        pr = getattr(context.scene, self.sceneProp)
        pr.add()
        return {'FINISHED'}

def create_pv_prop(proxyName, propName):
    prop = sm_prop(proxyName,propName)
    dom = get_prop_domains(prop)
    desc=sm_describe(prop)
    nm=propName
    if type(prop) == vtkPVServerManagerCorePython.vtkSMStringVectorProperty:
        if len(dom) == 1:
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMFileListDomain:
                return ('standard', bpy.props.StringProperty(
                    description=desc,name=nm,
                    subtype="FILE_PATH",
                    update=lambda self,context: fn_update(self,context,p)))
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMArrayListDomain:
                return ('standard', bpy.props.EnumProperty(
                    description=desc,name=nm,
                    items=lambda self, context: sm_get_items(proxyName,propName),
                    set=lambda self,value: sm_set_arraylist(self,proxyName,propName,value),
                    get=lambda self: sm_get_arraylist(self,proxyName,propName)))
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMArraySelectionDomain:
#                return bpy.props.EnumProperty(
#                    options={'ENUM_FLAG'},
#                    items=lambda self, context: sm_get_items(dom[0]),
#                    set=lambda self,value: sm_set_arrayselection(self,proxyName,propName,dom[0],value),
#                    get=lambda self: sm_get_arrayselection(self,proxyName,propName,dom[0]))
                return ('standard', bpy.props.CollectionProperty(
                    description=desc,name=nm,
                    type=ArraySelectionElement))
        if len(dom) == 0:
            if prop.GetNumberOfElements() == 1:
                return ('standard', bpy.props.StringProperty(
                    description=desc,name=nm,
                    set=lambda self,value: sm_set(self,proxyName,propName,value),
                    get=lambda self: sm_get(self,proxyName,propName)))
    if type(prop) == vtkPVServerManagerCorePython.vtkSMDoubleVectorProperty:
        if len(dom) == 1:
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMArrayRangeDomain:
                return ('DoubleArray', bpy.props.CollectionProperty(
                    description=desc,name=nm,
                    type=DoubleArrayElement))
        if prop.GetNumberOfElements() > 1:
            return ('standard', bpy.props.FloatVectorProperty(
                size=prop.GetNumberOfElements(),
                description=desc,name=nm,
                set=lambda self,value: sm_set_v(self,proxyName,propName,value),
                get=lambda self: sm_get_v(self,proxyName,propName)))
        elif prop.GetNumberOfElements() == 1:
            return ('standard', bpy.props.FloatProperty(
                description=desc,name=nm,
                set=lambda self,value: sm_set(self,proxyName,propName,value),
                get=lambda self: sm_get(self,proxyName,propName)))
    if type(prop) == vtkPVServerManagerCorePython.vtkSMIntVectorProperty:
        if len(dom) == 1:
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMBooleanDomain:
                if prop.GetNumberOfElements() > 1:
                    return ('standard', bpy.props.BoolVectorProperty(
                        size=prop.GetNumberOfElements(),
                        description=desc,name=nm,
                        set=lambda self,value: sm_set(self,proxyName,propName,value),
                        get=lambda self: sm_get(self,proxyName,propName)))
                if prop.GetNumberOfElements() == 1:
                    return ('standard', bpy.props.BoolProperty(
                        description=desc,name=nm,
                        set=lambda self,value: sm_set(self,proxyName,propName,value),
                        get=lambda self: sm_get(self,proxyName,propName)))
            if prop.GetNumberOfElements() > 1:
                return ('standard', bpy.props.IntVectorProperty(
                    size=prop.GetNumberOfElements(),
                    description=desc,name=nm,
                    set=lambda self,value: sm_set_v(self,proxyName,propName,value),
                    get=lambda self: sm_get_v(self,proxyName,propName)))
            if prop.GetNumberOfElements() == 1:
                return ('standard', bpy.props.IntProperty(
                    description=desc,name=nm,
                    set=lambda self,value: sm_set(self,proxyName,propName,value),
                    get=lambda self: sm_get(self,proxyName,propName)))
    return ('standard', bpy.props.StringProperty(
        description=desc,name=nm,
        set=lambda self,value: dbg_set(self,proxyName,propName,value),
        get=lambda self: dbg_get(self,proxyName,propName)))

class pvNode:
    bl_label = "General pv node"
    proxyName : bpy.props.StringProperty()
    propertyNames : bpy.props.CollectionProperty(type=pvPropNameType)
    def init(self, context):
        print("Init ",self.bl_label)
        self.init_data()
        self.pv_props()
        self.outputs.new("pvNodeSocket", "Output")
    def free(self):
        self.free_data()
    def draw_buttons(self, context, layout):
        for n in self.propertyNames:
            if hasattr(context.scene, n.sceneProp):
                pr = getattr(context.scene, n.sceneProp)
                if n.layoutType == "DoubleArray":
                    layout.label(text = n.propName + ":")
                    for k in pr:
                        layout.prop(k,'val',text='')
                    ret = layout.operator("pvblender.my_add_button_operator")
                    ret.sceneProp = n.sceneProp
                    ret.propName = n.propName
                    ret.proxyName = self.proxyName
                else:
                    layout.prop(context.scene, n.sceneProp)
    def init_data(self):
        paraview.simple.SetActiveSource(None)
        obj = getattr(sys.modules["paraview.simple"],self.pvType)()
        self.proxyName = obj.SMProxy.GetLogName()
    def pv(self):
        print("pv():" + self.proxyName)
        return paraview.simple.FindSource(self.proxyName)
    def sm_prop(self, p):
        return pv().GetProperty(p)
    def pv_props(self):
        op = {str(n) for n in self.pv().ListProperties()}
        ap = {str(n.propName) for n in self.propertyNames}
        mp = {p for p in ap if hasattr(type(self),p)}
        sp = {p.name for p in self.inputs}
        ip = set()
        pp = op - mp - sp
        if len(pp) > 0:
            print("Adding to",self.bl_label,"properties:",pp)
        for p in pp:
            prop = self.pv().GetProperty(p)
            if type(prop) == paraview.servermanager.InputProperty:
                ip.add(p)
            else:
                sceneProp = self.proxyName + "-" + p
                (layoutType, bpy_prop) = create_pv_prop(self.proxyName,p)
#                setattr(type(self),p,bpy_prop)
                setattr(bpy.types.Scene, sceneProp, bpy_prop)
                if p not in ap:
                    it = self.propertyNames.add()
                    it.sceneProp = sceneProp
                    it.propName = p
                    it.layoutType = layoutType
        # Adding inputs later, because it triggers update
        if len(ip) > 0:
            print("Adding to",self.bl_label,"inputs:",ip)
        for i in ip:
            self.inputs.new("pvNodeSocket", i)
    def update(self):
        print("Update ",self.bl_label)
        self.pv_props()
        pv1 = self.pv()
        for socket in self.inputs:
            if socket.is_linked and len(socket.links) > 0:
                print("----------- Socket",socket.name,"connected!")
                other = socket.links[0].from_socket.node
                pv2 = other.pv()
                pv1.SetPropertyWithName(socket.name, pv2)
            else:
                print("----------- Socket",socket.name,"disconnected!")
                pv1.SetPropertyWithName(socket.name, None)
            pv1.UpdatePipeline()

import sys

my_pvClasses = []

from bpy.app.handlers import persistent

def register():
    global my_pvClasses, vtknodes_tmp_mesh
    print("------------------------- REGISTER PV -------------------")
    bpy.utils.register_class(pvPropNameType)
    bpy.utils.register_class(ArraySelectionElement)
    bpy.utils.register_class(DoubleArrayElement)
    bpy.utils.register_class(AddButtonOperator)
    def pvClasses(mod):
        mylist = [i for i in dir(mod) if i[0] != "_"]
        return [ pvClass(k) for k in mylist ]
    def pvClass(k):
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
        return nodeitems_utils.NodeItem(c)
        
    categories = [
      category.pvNodeCategory("BVTK_SOURCES", "Sources",
        items = pvClasses(paraview.servermanager.sources)),
      category.pvNodeCategory("BVTK_FILTERS", "Filters",
        items = pvClasses(paraview.servermanager.filters)),
      category.pvNodeCategory("BVTK_WRITERS", "Writers",
        items = pvClasses(paraview.servermanager.writers)),
      category.pvNodeCategory("BVTK_OTHER", "Other",
        items = [ pvClass("CreateLookupTable") ]),
    ]

    nodeitems_utils.register_node_categories("BVTK_CATEGORIES", categories)
    

def unregister():
    global my_pvClasses
    print("------------------------- UNREGISTER PV -------------------")
    bpy.utils.unregister_class(pvPropNameType)
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


