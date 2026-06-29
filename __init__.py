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
_last_mapping_index = -1


def _select_bone_in_viewport(bone_name):
    """Select a bone in the active armature (direct data access, no bpy.ops)."""
    context = bpy.context
    arm = context.active_object
    if not arm or arm.type != 'ARMATURE' or context.mode != 'POSE':
        return
    pbone = arm.pose.bones.get(bone_name)
    if not pbone:
        return
    for b in arm.data.bones:
        b.select = False
    pbone.bone.select = True
    arm.data.bones.active = pbone.bone


@persistent
def _sync_selection(scene):
    """Bidirectional sync between viewport bone selection and mapping panel index."""
    global _last_selected_bone, _last_mapping_index
    context = bpy.context
    s = context.scene.mixamo_retarget
    arm = context.active_object
    if not arm or arm.type != 'ARMATURE' or context.mode != 'POSE':
        return

    current_index = s.bone_mapping_index
    selected = context.selected_pose_bones
    current_bone = selected[0].name if selected else ""

    # Direction 1: viewport → panel (selected bone changed)
    if current_bone and current_bone != _last_selected_bone:
        for i, item in enumerate(s.bone_mappings):
            if item.target_bone == current_bone or item.source_bone == current_bone:
                if current_index != i:
                    s.bone_mapping_index = i
                _last_selected_bone = current_bone
                _last_mapping_index = i
                return

    # Direction 2: panel → viewport (index changed, e.g. row clicked)
    if current_index != _last_mapping_index:
        if 0 <= current_index < len(s.bone_mappings):
            item = s.bone_mappings[current_index]
            target = item.target_bone or item.source_bone
            if target and target != _last_selected_bone:
                _select_bone_in_viewport(target)
                _last_selected_bone = target
                _last_mapping_index = current_index
                return
        _last_mapping_index = current_index

    # Update tracking vars if nothing changed
    if current_bone:
        _last_selected_bone = current_bone
    _last_mapping_index = current_index


from . import properties, operators, ui_list, panels


def register():
    properties.register()
    operators.register()
    ui_list.register()
    panels.register()
    bpy.app.handlers.depsgraph_update_post.append(_sync_selection)


def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(_sync_selection)
    panels.unregister()
    ui_list.unregister()
    operators.unregister()
    properties.unregister()
