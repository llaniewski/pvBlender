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
    propLabel : bpy.props.StringProperty()
    layoutType : bpy.props.StringProperty()
    sceneProp : bpy.props.StringProperty()

def sm_proxy(proxyName):
    return paraview.simple.FindSource(proxyName)
def sm_prop(proxyName,propName):
    return paraview.simple.FindSource(proxyName).GetProperty(propName).SMProperty

def sm_set(self,proxyName,propName,value):
    prop = sm_prop(proxyName,propName)
    prop.SetElement(0, value)
    prop.GetParent().UpdateSelfAndAllInputs()

def sm_set_fn(self,proxyName,propName,value):
    prop = sm_prop(proxyName,propName)
    prop.SetElement(0, value)
    sm_proxy(proxyName).FileNameChanged()

def sm_get(self,proxyName,propName):
    prop = sm_prop(proxyName,propName)
    ret = prop.GetElement(0)
    return ret

def sm_set_elements(prop,value):
    n = prop.GetNumberOfElements()
    for i in range(n) :
        prop.SetElement(i, value[i])

def sm_set_elements_varlen(prop,value):
    prop.SetNumberOfElements(len(value))
    for i in range(len(value)) :
        prop.SetElement(i, value[i])


def sm_get_elements(prop):
    n = prop.GetNumberOfElements()
    return [ prop.GetElement(i) for i in range(n) ]

def sm_set_v(self,proxyName,propName,value):
    prop = sm_prop(proxyName,propName)
    sm_set_elements(prop,value)
    prop.GetParent().UpdateSelfAndAllInputs()

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

items_bug_workaround = None

def sm_get_items(proxyName,propName):
    global items_bug_workaround
    prop = sm_prop(proxyName,propName)
    dom = get_prop_domains(prop)
    ret = sm_get_strings(dom[0])
    items_bug_workaround = [ (s,s,s) for s in ret ]
    return items_bug_workaround

def sm_set_arraylist(self,proxyName,propName,value):
    prop = sm_prop(proxyName,propName)
    dom = get_prop_domains(prop)
    ret = sm_get_strings(dom[0])
    print("set:" + str(value))
    if value < len(ret):
        s = ret[value]
        prop.SetElement(4, s)
    else:
        prop.SetElement(4, None)
    prop.GetParent().UpdateSelfAndAllInputs()

def sm_get_arraylist(self,proxyName,propName):
    prop = sm_prop(proxyName,propName)
    dom = get_prop_domains(prop)
    ret = sm_get_strings(dom[0])
    if prop.GetNumberOfElements() > 1:
        val = prop.GetElement(prop.GetNumberOfElements()-1)
    else:
        val = -1
    try:
        i = ret.index(val)
    except ValueError:
        i = -1
    return i

def sm_get_strings(d):
    n = d.GetNumberOfStrings()
    ret = [ d.GetString(i) for i in range(n) ]
    return ret


def sm_get_enum_items(proxyName,propName):
    global items_bug_workaround
    prop = sm_prop(proxyName,propName)
    dom = get_prop_domains(prop)
    items_bug_workaround = [ (dom[0].GetEntryText(i),dom[0].GetEntryText(i),dom[0].GetEntryText(i),dom[0].GetEntryValue(i)) for i in range(dom[0].GetNumberOfEntries()) ]
    return items_bug_workaround

def sm_set_enum(self,proxyName,propName,value):
    prop = sm_prop(proxyName,propName)
    prop.SetElement(0, value)
    prop.GetParent().UpdateSelfAndAllInputs()

def sm_get_enum(self,proxyName,propName):
    prop = sm_prop(proxyName,propName)
    return prop.GetElement(0)

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

def sm_arrayselection_set(self,value):
    prop = sm_prop(self.proxyName,self.propName)
    if value:
        val = '1'
    else:
        val = '0'
    i = self.index*2
    if i+1 < prop.GetNumberOfElements():
        if prop.GetElement(i) == self.option:
            prop.SetElement(i+1,val)

def sm_arrayselection_get(self):
    prop = sm_prop(self.proxyName,self.propName)
    i = self.index*2
    if i+1 < prop.GetNumberOfElements():
        if prop.GetElement(i) == self.option:
            return prop.GetElement(i+1) == '1'
    return False

    

class ArraySelectionElement(bpy.types.PropertyGroup):
    value : bpy.props.BoolProperty(set=sm_arrayselection_set, get=sm_arrayselection_get )
    proxyName : bpy.props.StringProperty()
    propName  : bpy.props.StringProperty()
    index : bpy.props.IntProperty()
    option : bpy.props.StringProperty()

def sm_doublearray_set(self,value):
    prop = sm_prop(self.proxyName,self.propName)
    if (self.index >= prop.GetNumberOfElements()):
        prop.SetNumberOfElements(self.index+1)
    prop.SetElement(self.index, value)
def sm_doublearray_get(self):
    prop = sm_prop(self.proxyName,self.propName)
    return prop.GetElement(self.index)


class DoubleArrayElement(bpy.types.PropertyGroup):
    value : bpy.props.FloatProperty(set=sm_doublearray_set, get=sm_doublearray_get )
    proxyName : bpy.props.StringProperty()
    propName  : bpy.props.StringProperty()
    index : bpy.props.IntProperty()

class AddButtonOperator(bpy.types.Operator):
    bl_idname = "pvblender.my_add_button_operator"
    bl_label = "Add Button"
    proxyName : bpy.props.StringProperty()
    propName  : bpy.props.StringProperty()
    sceneProp : bpy.props.StringProperty()
    def execute(self, context):
        pr = getattr(context.scene, self.sceneProp)
        ret = pr.add()
        ret.propName = self.propName
        ret.proxyName = self.proxyName
        ret.index = len(pr)-1
        sm_doublearray_set(ret, 0)
        return {'FINISHED'}

def node_update(self, context):
    bpy.context.active_node.update()

def create_pv_prop(proxyName, propName):
    prop = sm_prop(proxyName,propName)
    dom = get_prop_domains(prop)
    desc = sm_describe(prop)
    nm = prop.GetXMLLabel()
    if type(prop) == vtkPVServerManagerCorePython.vtkSMStringVectorProperty:
        if len(dom) == 1:
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMFileListDomain:
                return (nm, 'standard', bpy.props.StringProperty(
                    description=desc,name=nm,
                    subtype="FILE_PATH",
                    set=lambda self,value: sm_set_fn(self,proxyName,propName,value),
                    get=lambda self: sm_get(self,proxyName,propName),
                    update=node_update))
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMArrayListDomain:
                return (nm, 'standard', bpy.props.EnumProperty(
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
                return (nm, 'ArraySelection', bpy.props.CollectionProperty(
                    description=desc,name=nm,
                    type=ArraySelectionElement))
        if len(dom) == 0:
            if prop.GetNumberOfElements() == 1:
                return (nm, 'standard', bpy.props.StringProperty(
                    description=desc,name=nm,
                    set=lambda self,value: sm_set(self,proxyName,propName,value),
                    get=lambda self: sm_get(self,proxyName,propName)))
    if type(prop) == vtkPVServerManagerCorePython.vtkSMDoubleVectorProperty:
        if len(dom) == 1:
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMArrayRangeDomain:
                return (nm, 'DoubleArray', bpy.props.CollectionProperty(
                    description=desc,name=nm,
                    type=DoubleArrayElement))
        if prop.GetNumberOfElements() > 1:
            return (nm, 'standard', bpy.props.FloatVectorProperty(
                size=prop.GetNumberOfElements(),
                description=desc,name=nm,
                set=lambda self,value: sm_set_v(self,proxyName,propName,value),
                get=lambda self: sm_get_v(self,proxyName,propName)))
        elif prop.GetNumberOfElements() == 1:
            return (nm, 'standard', bpy.props.FloatProperty(
                description=desc,name=nm,
                set=lambda self,value: sm_set(self,proxyName,propName,value),
                get=lambda self: sm_get(self,proxyName,propName)))
    if type(prop) == vtkPVServerManagerCorePython.vtkSMIntVectorProperty:
        if len(dom) == 1:
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMBooleanDomain:
                if prop.GetNumberOfElements() > 1:
                    return (nm, 'standard', bpy.props.BoolVectorProperty(
                        size=prop.GetNumberOfElements(),
                        description=desc,name=nm,
                        set=lambda self,value: sm_set(self,proxyName,propName,value),
                        get=lambda self: sm_get(self,proxyName,propName)))
                if prop.GetNumberOfElements() == 1:
                    return (nm, 'standard', bpy.props.BoolProperty(
                        description=desc,name=nm,
                        set=lambda self,value: sm_set(self,proxyName,propName,value),
                        get=lambda self: sm_get(self,proxyName,propName)))
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMEnumerationDomain:
                if prop.GetNumberOfElements() == 1:
                    return (nm, 'standard', bpy.props.EnumProperty(
                        description=desc,name=nm,
                        items=sm_get_enum_items(proxyName,propName),
                        set=lambda self,value: sm_set_enum(self,proxyName,propName,value),
                        get=lambda self: sm_get_enum(self,proxyName,propName)))
            if prop.GetNumberOfElements() > 1:
                return (nm, 'standard', bpy.props.IntVectorProperty(
                    size=prop.GetNumberOfElements(),
                    description=desc,name=nm,
                    set=lambda self,value: sm_set_v(self,proxyName,propName,value),
                    get=lambda self: sm_get_v(self,proxyName,propName)))
            if prop.GetNumberOfElements() == 1:
                return (nm, 'standard', bpy.props.IntProperty(
                    description=desc,name=nm,
                    set=lambda self,value: sm_set(self,proxyName,propName,value),
                    get=lambda self: sm_get(self,proxyName,propName)))
    return (nm, 'standard', bpy.props.StringProperty(
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
                    layout.label(text = n.propLabel + ":")
                    for k in pr:
                        layout.prop(k,'value',text='')
                    ret = layout.operator("pvblender.my_add_button_operator")
                    ret.sceneProp = n.sceneProp
                    ret.propName = n.propName
                    ret.proxyName = self.proxyName
                elif n.layoutType == "ArraySelection":
                    layout.label(text = n.propLabel + ":")
                    for k in pr:
                        layout.prop(k,'value',text=k.option)
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
        propertyNames = {str(n.propName) for n in self.propertyNames}
        inputNames = {p.name for p in self.inputs}
        for p in self.pv().ListProperties():
            prop = self.pv().GetProperty(p)
            if type(prop) == paraview.servermanager.InputProperty:
                if p not in inputNames:
                    self.inputs.new("pvNodeSocket", p)
            else:
                sceneProp = self.proxyName + "-" + p
                if hasattr(bpy.types.Scene, sceneProp):
                    if p not in propertyNames:
                        print("---------- WEIRD")
                else:
                    (label, layoutType, bpy_prop) = create_pv_prop(self.proxyName,p)
                    setattr(bpy.types.Scene, sceneProp, bpy_prop)
                    if p not in propertyNames:
                        it = self.propertyNames.add()
                        it.sceneProp = sceneProp
                        it.propName = p
                        it.propLabel = label
                        it.layoutType = layoutType
                    else:
                        for n in self.propertyNames:
                            if n.propName == p:
                                n.sceneProp = sceneProp
                                n.layoutType = layoutType
                                n.propLabel = label
    def update(self):
        print("Update ",self.bl_label)
        self.pv_props()
        for n in self.propertyNames:
            if hasattr(bpy.context.scene, n.sceneProp):
                pr = getattr(bpy.context.scene, n.sceneProp)
                prop = sm_prop(self.proxyName, n.propName)
                if n.layoutType == "DoubleArray":
                    if len(pr) != prop.GetNumberOfElements():
                        pr.clear()
                        for i in range(prop.GetNumberOfElements()):
                            ret = pr.add()
                            ret.propName = n.propName
                            ret.proxyName = self.proxyName
                            ret.index = i
                elif n.layoutType == "ArraySelection":
                    dom = get_prop_domains(prop)
                    opt = sm_get_strings(dom[0])
                    if prop.GetNumberOfElements() != 2 * dom[0].GetNumberOfStrings():
                        prop.SetNumberOfElements(2 * dom[0].GetNumberOfStrings())
                        i = 0
                        for o in sm_get_strings(dom[0]):
                            prop.SetElement(2*i, o)
                            prop.SetElement(2*i+1, '0')
                            i = i + 1
                    if len(pr) != dom[0].GetNumberOfStrings():
                        pr.clear()
                        i = 0
                        for o in sm_get_strings(dom[0]):
                            ret = pr.add()
                            ret.propName = n.propName
                            ret.proxyName = self.proxyName
                            ret.index = i
                            ret.option = o
                            i = i + 1
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
    print("------ pvBlender: register nodes")
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
            #print("adding class ",c,"with object", k)
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
    print("------ pvBlender: unregister nodes")
    bpy.utils.unregister_class(pvPropNameType)
    bpy.utils.unregister_class(ArraySelectionElement)
    bpy.utils.unregister_class(DoubleArrayElement)
    bpy.utils.unregister_class(AddButtonOperator)
    for c in my_pvClasses:
        new_class = getattr(sys.modules[__name__], c)
        if isinstance(new_class,type):
            #print("unregistering: ",c)
            bpy.utils.unregister_class(new_class)
        else:
            print(c,"is not a class")
    my_pvClasses = []
    nodeitems_utils.unregister_node_categories("BVTK_CATEGORIES")


