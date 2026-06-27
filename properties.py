import bpy
from bpy.props import (
    StringProperty, FloatProperty, IntProperty, BoolProperty,
    EnumProperty, CollectionProperty, PointerProperty,
)
from bpy.types import PropertyGroup, AddonPreferences


class MIXAMO_BoneMappingItem(PropertyGroup):
    source_bone: StringProperty(
        name="Source Bone",
        description="Bone name in the source armature (animation source)",
        default="",
    )
    target_bone: StringProperty(
        name="Target Bone",
        description="Bone name in target armature (character to animate)",
        default="",
    )
    enabled: BoolProperty(
        name="Enabled",
        description="Include this bone in retargeting",
        default=True,
    )
    retarget_mode: EnumProperty(
        name="Mode",
        description="How this bone pair is driven",
        items=[
            ("COPY_ROTATION", "Copy Rotation", "Copy rotation in world space; root also gets Copy Location"),
            ("COPY_TRANSFORMS", "Copy Transforms", "Copy loc + rot + scale in local space"),
            ("CHILD_OF", "Child Of", "Child Of constraint with auto inverse matrix"),
            ("CHILD_OF_ROTATION", "Child Of (Rotation)", "Child Of with rotation only"),
        ],
        default="COPY_ROTATION",
    )


class MIXAMO_SceneSettings(PropertyGroup):
    source_armature: PointerProperty(
        name="Source Armature",
        description="The armature with animation (Mixamo FBX animation source)",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE',
    )
    target_armature: PointerProperty(
        name="Target Armature",
        description="Your character's armature to drive with the motion",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE',
    )

    bone_mappings: CollectionProperty(type=MIXAMO_BoneMappingItem)
    bone_mapping_index: IntProperty(default=0)

    retarget_root_bone: StringProperty(
        name="Root Bone (Target)",
        description="Root / hip bone on the target armature",
        default="",
    )

    fbx_scale: FloatProperty(
        name="FBX Scale",
        description="Scale factor for imported FBX",
        default=1.0,
        min=0.001,
        max=100.0,
    )

    bake_start_frame: IntProperty(name="Start Frame", default=1, min=0)
    bake_end_frame: IntProperty(name="End Frame", default=250, min=1)

    preset_name: StringProperty(
        name="Preset Name",
        description="Name to save/load bone mapping preset",
        default="default",
    )

    auto_align_rest_pose: BoolProperty(
        name="Align Rest Pose",
        description="Automatically compute rest-pose offset between source and target",
        default=True,
    )


class MIXAMO_AddonPreferences(AddonPreferences):
    bl_idname = __package__

    saved_presets: StringProperty(
        name="Saved Presets",
        description="JSON blob of all saved bone-mapping presets",
        default="{}",
    )


_classes = [
    MIXAMO_BoneMappingItem,
    MIXAMO_SceneSettings,
    MIXAMO_AddonPreferences,
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
    bpy.types.Scene.mixamo_retarget = PointerProperty(type=MIXAMO_SceneSettings)


def unregister():
    del bpy.types.Scene.mixamo_retarget
    for cls in reversed(_classes):
        _safe_unregister_class(cls)
