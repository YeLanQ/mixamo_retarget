import bpy
from bpy.types import UIList


class MIXAMO_UL_BoneMappings(UIList):
    bl_idname = "MIXAMO_UL_BoneMappings"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            row.prop(item, "enabled", text="", emboss=False,
                     icon='CHECKBOX_HLT' if item.enabled else 'CHECKBOX_DEHLT')

            row.prop(item, "source_bone", text="", emboss=False)

            row.label(text="", icon='TRIA_RIGHT')

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


def unregister():
    for cls in reversed(_classes):
        _safe_unregister_class(cls)
