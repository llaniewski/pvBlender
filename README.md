# pvBlender - ParaView for Blender

Blender add-on for constructing ParaView pipelines

## Installation
Just download Paraview release package (with python 3.7), and set appropriate PYTHONPATH:
```bash
export PYTHONPATH=[path_to_paraview]/lib/python3.7/site-packages/vtkmodules/:[path_to_paraview]/lib/python3.7/site-packages/:$PYTHONPATH
[path_to_blender]/blender
```

## Usage
Go to "VTK/Paraview Nodes" view and add a panel. Then press "Shift+A" and add some nodes. You will find file readers in *Sources*.

### Blender mesh
A `Blender Object` node provides the possibility to add mesh object based on data from ParaView:
<p align="center"><img src="https://raw.githubusercontent.com/llaniewski/pvBlender/images/box_cone.gif"/></p>

### Filters
Any ParaView filter can be used as a node:
<p align="center"><img src="https://raw.githubusercontent.com/llaniewski/pvBlender/images/glyph.gif"/></p>

### And then ...
And then you can set smooth shading and render.
<p align="center"><img src="https://raw.githubusercontent.com/llaniewski/pvBlender/images/render.gif"/></p>

