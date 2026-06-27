bl_info = {
    "name": "Mixamo Retarget",
    "author": "Kimodo Bridge Contributors",
    "version": (2, 0, 0),
    "blender": (5, 1, 0),
    "location": "View3D > Sidebar (N-Panel) > Mixamo Retarget",
    "description": "Retarget Mixamo FBX animations between Mixamo-rigged characters",
    "category": "Animation",
}

import bpy

from . import properties, operators, ui_list, panels


def register():
    properties.register()
    operators.register()
    ui_list.register()
    panels.register()


def unregister():
    panels.unregister()
    ui_list.unregister()
    operators.unregister()
    properties.unregister()
