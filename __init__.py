bl_info = {
    "name": "Mixamo Retarget",
    "author": "Kimodo Bridge Contributors",
    "version": (2, 0, 1),
    "blender": (5, 1, 0),
    "location": "View3D > Sidebar (N-Panel) > Mixamo Retarget",
    "description": "Retarget Mixamo FBX animations between Mixamo-rigged characters",
    "category": "Animation",
}

import bpy
from bpy.app.handlers import persistent

_last_selected_bone = ""


@persistent
def _sync_selection_to_panel(scene):
    """Sync viewport bone selection to the bone mapping list index."""
    global _last_selected_bone
    context = bpy.context
    s = context.scene.mixamo_retarget
    arm = context.active_object
    if not arm or arm.type != 'ARMATURE' or context.mode != 'POSE':
        return
    selected = context.selected_pose_bones
    if not selected:
        return
    bone_name = selected[0].name
    if bone_name == _last_selected_bone:
        return
    _last_selected_bone = bone_name
    for i, item in enumerate(s.bone_mappings):
        if item.target_bone == bone_name or item.source_bone == bone_name:
            if s.bone_mapping_index != i:
                s.bone_mapping_index = i
            break


from . import properties, operators, ui_list, panels


def register():
    properties.register()
    operators.register()
    ui_list.register()
    panels.register()
    bpy.app.handlers.depsgraph_update_post.append(_sync_selection_to_panel)


def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(_sync_selection_to_panel)
    panels.unregister()
    ui_list.unregister()
    operators.unregister()
    properties.unregister()
