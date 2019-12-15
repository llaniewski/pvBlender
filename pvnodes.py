import bpy
import nodeitems_utils
import paraview
import paraview.simple
import paraview.servermanager
import paraview.modules.vtkPVServerManagerCorePython as vtkPVServerManagerCorePython
import uuid
from .nodedata import pvDataNode
from . import category


class pvPropName(bpy.types.PropertyGroup):
    s : bpy.props.StringProperty()
    l : bpy.props.StringProperty()
    i : bpy.props.StringProperty()
    def draw(self, context, layout):
        layout.prop(self, "s")

class pvPropBase(pvDataNode):
    propertyId : bpy.props.StringProperty(default="")
    def update(self,context):
        print(self.propertyId,"updated")
    def load_prop(self):
        self.load_data()
        self.prop = self.pv().GetProperty(self.propertyId)

class pvPropString(bpy.types.PropertyGroup,pvPropBase):
    v : bpy.props.StringProperty()
    def read(self):
        self.load_prop()
    def draw(self, layout, p):
        layout.prop(self, "v",text=p)

class pvPropFloat(bpy.types.PropertyGroup,pvPropBase):
    v : bpy.props.FloatProperty()
    def read(self):
        self.load_prop()
    def draw(self, layout, p):
        layout.prop(self, "v",text=p)

def general_update(self,context):
    print(self)
    print(context)

def general_set(self,p,value):
    print("SET:",self,p,value)
    self.pv().SetPropertyWithName(p,value)
    self[p] = value

def general_get(self,p):
#    print("GET:",self,p,self[p])
    return self.pv().GetProperty(p)[0]
#    return self[p]



def sm_set(self,p,value):
    p.SetElement(0, value)
    p.GetParent().UpdateSelfAndAllInputs()

def sm_get(self,p):
#    print("get self:", str(type(self)))
    ret = p.GetElement(0)
    return ret

def sm_set_v(self,p,value):
    #print("set:", value)
    n = p.GetNumberOfElements()
    for i in range(n) :
        p.SetElement(i, value[i])
    p.GetParent().UpdateSelfAndAllInputs()

def sm_get_elements(p):
    n = p.GetNumberOfElements()
    return [ p.GetElement(i) for i in range(n) ]

def sm_get_v(self,p):
    ret = sm_get_elements(p)
    return ret

def sm_describe(prop):
    [sdom, dom] = get_prop_domain(prop)
    ret=""
    if "GetNumberOfElements" in dir(prop):
        ret = ret + str(prop.GetNumberOfElements()) + ":"
    ret = ret + str(type(prop)) + str([str(type(d)) for d in dom])
    return ret

def sm_set_arraylist(self,p,d,value):
    #print("set:" + str(value))
    ret = sm_get_strings(d)
    if value > 0:
        s = ret[value-1]
        p.SetElement(4, s)
    else:
        p.SetElement(4, None)
    p.GetParent().UpdateSelfAndAllInputs()

def sm_get_arraylist(self,p,d):
    ret = sm_get_strings(d)
    val = p.GetElement(4)
    try:
        i = ret.index(val)+1
    except ValueError:
        i = 0
#    print("get:" + str(i))
    return i


def sm_set_arrayselection(self,p,d,value):
#    print("set:" + str(value))
    s = sm_get_strings(d)
    bits = [ s[i] for i in range(len(s)) if value & (1<<i) != 0 ]
#    print("set:" + str(bits))
    n = p.GetNumberOfElements()
    for i in range(0,n,2) :
        if p.GetElement(i) in bits:
            p.SetElement(i+1, '1')
        else:
            p.SetElement(i+1, '0')
    p.GetParent().UpdateSelfAndAllInputs()



def sm_arrayselection_checked(e,v):
    try:
        i = e.index(v)
        return e[i+1] == '1'
    except ValueError:
        return False

def sm_get_arrayselection(self,p,d):
    s = sm_get_strings(d)
    e = sm_get_elements(p)
    bits = [sm_arrayselection_checked(e,i) for i in s]
    out = 0
    for k in range(len(bits)):
        if bits[k]:
            out = out + (1<<k)
#    print("get:" + str(out))
    return out

def sm_get_strings(d):
    n = d.GetNumberOfStrings()
    ret = [ d.GetString(i) for i in range(n) ]
    return ret

def sm_get_items(d):
    n = d.GetNumberOfStrings()
    ret = [ (d.GetString(i),d.GetString(i),"desc",i+1) for i in range(n) ]
#    print("items:"+str(ret))
    return ret


def dbg_set(self,p,value):
    pass

def dbg_get(self,prop):
    return sm_describe(prop)


def fn_set(self,p,value):
    print("SET filename:",self,p,value)
    self.pv().SetPropertyWithName(p,bpy.path.abspath(value))

def fn_get(self,p):
    return str(self.pv().GetProperty(p)[0])

def fn_update(self,context,p):
    self.load_data()
    value = getattr(self,p)
    print("Update filename:",self,p,value);
    self.pv().SetPropertyWithName(p,bpy.path.abspath(value))


def get_prop_domain(prop):
    i = prop.NewDomainIterator()
    s = []
    while i.GetKey() is not None:
        s.append(i.GetKey())
        i.Next()
    dom = [ prop.GetDomain(i) for i in s ]
    return (s,dom)

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
    i :bpy.props.StringProperty()
    def execute(self, context):
        pr = getattr(context.scene, self.i)
        pr.add()
        return {'FINISHED'}

def create_pv_prop(prop_, p):
    prop=prop_.SMProperty
    sdom,dom = get_prop_domain(prop)
    desc=sm_describe(prop)
    nm=p
    if type(prop) == vtkPVServerManagerCorePython.vtkSMStringVectorProperty:
        if len(sdom) == 1:
            if sdom[0] == "files":
                return ('standard', bpy.props.StringProperty(
                    description=desc,name=nm,
                    subtype="FILE_PATH",
                    update=lambda self,context: fn_update(self,context,p)))
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMArrayListDomain:
                return ('standard', bpy.props.EnumProperty(
                    description=desc,name=nm,
                    items=lambda self, context: sm_get_items(dom[0]),
                    set=lambda self,value: sm_set_arraylist(self,prop,dom[0],value),
                    get=lambda self: sm_get_arraylist(self,prop,dom[0])))
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMArraySelectionDomain:
#                return bpy.props.EnumProperty(
#                    options={'ENUM_FLAG'},
#                    items=lambda self, context: sm_get_items(dom[0]),
#                    set=lambda self,value: sm_set_arrayselection(self,prop,dom[0],value),
#                    get=lambda self: sm_get_arrayselection(self,prop,dom[0]))
                return ('standard', bpy.props.CollectionProperty(
                    description=desc,name=nm,
                    type=ArraySelectionElement))
        if len(sdom) == 0:
            if prop.GetNumberOfElements() == 1:
                return ('standard', bpy.props.StringProperty(
                    description=desc,name=nm,
                    set=lambda self,value: sm_set(self,prop,value),
                    get=lambda self: sm_get(self,prop)))
    if type(prop) == vtkPVServerManagerCorePython.vtkSMDoubleVectorProperty:
        if len(sdom) == 1:
            if type(dom[0]) == vtkPVServerManagerCorePython.vtkSMArrayRangeDomain:
                return ('DoubleArray', bpy.props.CollectionProperty(
                    description=desc,name=nm,
                    type=DoubleArrayElement))
        if prop.GetNumberOfElements() > 1:
            return ('standard', bpy.props.FloatVectorProperty(
                size=prop.GetNumberOfElements(),
                description=desc,name=nm,
                set=lambda self,value: sm_set_v(self,prop,value),
                get=lambda self: sm_get_v(self,prop)))
        elif prop.GetNumberOfElements() == 1:
            return ('standard', bpy.props.FloatProperty(
                description=desc,name=nm,
                set=lambda self,value: sm_set(self,prop,value),
                get=lambda self: sm_get(self,prop)))
    if type(prop) == vtkPVServerManagerCorePython.vtkSMIntVectorProperty:
        if len(sdom) == 1:
            sdom = sdom[0]
            if sdom == "bool":
                if prop.GetNumberOfElements() > 1:
                    return ('standard', bpy.props.BoolVectorProperty(
                        size=prop.GetNumberOfElements(),
                        description=desc,name=nm,
                        set=lambda self,value: sm_set(self,prop,value),
                        get=lambda self: sm_get(self,prop)))
                if prop.GetNumberOfElements() == 1:
                    return ('standard', bpy.props.BoolProperty(
                        description=desc,name=nm,
                        set=lambda self,value: sm_set(self,prop,value),
                        get=lambda self: sm_get(self,prop)))
            if prop.GetNumberOfElements() > 1:
                return ('standard', bpy.props.IntVectorProperty(
                    size=prop.GetNumberOfElements(),
                    description=desc,name=nm,
                    set=lambda self,value: sm_set_v(self,prop,value),
                    get=lambda self: sm_get_v(self,prop)))
            if prop.GetNumberOfElements() == 1:
                return ('standard', bpy.props.IntProperty(
                    description=desc,name=nm,
                    set=lambda self,value: sm_set(self,prop,value),
                    get=lambda self: sm_get(self,prop)))
    return ('standard', bpy.props.StringProperty(
        description=desc,name=nm,
        set=lambda self,value: dbg_set(self,prop,value),
        get=lambda self: dbg_get(self,prop)))

class pvNode:
    bl_label = "General pv node"
    proxyName : bpy.props.StringProperty()
    propertyNames : bpy.props.CollectionProperty(type=pvPropName)
    def init(self, context):
        print("Init ",self.bl_label)
        self.init_data()
        self.pv_props()
        self.outputs.new("pvNodeSocket", "Output")
    def free(self):
        self.free_data()
    def draw_buttons(self, context, layout):
        #self.load_data()
#        data=self.get_data()
#        layout.label(text=self.pv().GetDataInformation().GetDataSetTypeAsString())
        for n in self.propertyNames:
            p = n.s
            i = n.i
            lay = n.l
            if hasattr(context.scene, i):
                pr = getattr(context.scene, i)
                if isinstance(pr,pvPropBase):
                    pr.draw(layout,p)
                else:
                    if lay == "DoubleArray":
                        layout.label(text = p + ":")
                        for k in pr:
                            layout.prop(k,'val',text='')
                        ret = layout.operator("pvblender.my_add_button_operator")
                        ret.i = i
                    else:
                        layout.prop(context.scene, i)
    def init_data(self):
        paraview.simple.SetActiveSource(None)
        obj = getattr(sys.modules["paraview.simple"],self.pvType)()
        self.proxyName = obj.SMProxy.GetLogName()
    def pv(self):
        print("pv():" + self.proxyName)
        return paraview.simple.FindSource(self.proxyName)
    def pv_props(self):
        op = {str(n) for n in self.pv().ListProperties()}
        ap = {str(n.s) for n in self.propertyNames}
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
                i = str(uuid.uuid1()) + "-" + p
                (lay, bpy_prop) = create_pv_prop(prop,p)
#                setattr(type(self),p,bpy_prop)
                setattr(bpy.types.Scene,i,bpy_prop)
                if p not in ap:
                    it = self.propertyNames.add()
                    it.i = i
                    it.s = p
                    it.l = lay
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
                other.load_data()
                pv2 = other.self.pv
                pv1.SetPropertyWithName(socket.name, pv2)
            else:
                print("----------- Socket",socket.name,"connected!")
                pv1.SetPropertyWithName(socket.name, None)
            pv1.UpdatePipeline()

import sys

my_pvClasses = []

from bpy.app.handlers import persistent

def register():
    global my_pvClasses, vtknodes_tmp_mesh
    print("------------------------- REGISTER PV -------------------")
    bpy.utils.register_class(pvPropName)
    bpy.utils.register_class(pvPropString)
    bpy.utils.register_class(pvPropFloat)
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


