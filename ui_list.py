import bpy
from bpy.types import UIList


# ---------------------------------------------------------------------------
# Sync 3D bone selection → UI mapping row highlight
# ---------------------------------------------------------------------------

_cache_armature = ""
_cache_bone = ""


def _sync_bone_selection(*_args):
    """When a bone is selected in the 3D viewport, highlight the
    corresponding row in the bone-mapping list."""
    context = bpy.context
    scene = context.scene
    arm = context.active_object
    if not arm or arm.type != 'ARMATURE':
        return
    if context.mode != 'POSE':
        return

    s = getattr(scene, "mixamo_retarget", None)
    if not s:
        return

    global _cache_armature, _cache_bone

    selected = context.selected_pose_bones
    if not selected:
        return

    arm_name = arm.name
    selected_name = selected[0].name
    if (arm_name, selected_name) == (_cache_armature, _cache_bone):
        return
    _cache_armature, _cache_bone = arm_name, selected_name

    for idx, item in enumerate(s.bone_mappings):
        if item.source_bone == selected_name or item.target_bone == selected_name:
            if s.bone_mapping_index != idx:
                s.bone_mapping_index = idx
            break


# ---------------------------------------------------------------------------
# UI list
# ---------------------------------------------------------------------------

class MIXAMO_UL_BoneMappings(UIList):
    bl_idname = "MIXAMO_UL_BoneMappings"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            row.prop(item, "enabled", text="", emboss=False,
                     icon='CHECKBOX_HLT' if item.enabled else 'CHECKBOX_DEHLT')

            if item.source_bone:
                op = row.operator("mixamo_retarget.select_mapping_bone",
                                  text="", icon='BONE_DATA', emboss=False)
                op.bone_name = item.source_bone
                op.from_source = True
            row.prop(item, "source_bone", text="", emboss=False)

            row.label(text="", icon='TRIA_RIGHT')

            if item.target_bone:
                op = row.operator("mixamo_retarget.select_mapping_bone",
                                  text="", icon='BONE_DATA', emboss=False)
                op.bone_name = item.target_bone
                op.from_source = False
            row.prop(item, "target_bone", text="", emboss=False)

            row.prop(item, "retarget_mode", text="")

            if item.target_bone:
                op = row.operator("mixamo_retarget.remove_single_retargeting",
                                  text="", icon='X', emboss=False)
                op.bone_name = item.target_bone

        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='BONE_DATA')


_classes = [
    MIXAMO_UL_BoneMappings,
]


def _safe_register_class(cls):
    try:
        bpy.utils.register_class(cls)
    except ValueError:
        pass


def _safe_unregister_class(cls):
    try:
        bpy.utils.unregister_class(cls)
    except RuntimeError:
        pass


def register():
    for cls in _classes:
        _safe_register_class(cls)
    bpy.app.handlers.depsgraph_update_post.append(_sync_bone_selection)


def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(_sync_bone_selection)
    for cls in reversed(_classes):
        _safe_unregister_class(cls)
