import bpy
import os
import json
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, IntProperty

from . import retarget as rt


# ---------------------------------------------------------------------------
# FBX import compatibility across Blender versions
# ---------------------------------------------------------------------------

def _fbx_import_supported_params() -> set:
    """Detect which keyword args bpy.ops.import_scene.fbx accepts."""
    op = bpy.ops.import_scene.fbx
    rna = op.get_rna_type() if hasattr(op, "get_rna_type") else None
    if rna is None:
        return set()
    return {p.identifier for p in rna.properties}


class MIXAMO_OT_ImportMixamoFBX(Operator):
    """Import a Mixamo FBX animation file as the source armature"""
    bl_idname = "mixamo_retarget.import_mixamo_fbx"
    bl_label = "Import Mixamo FBX"

    filepath: StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        s = context.scene.mixamo_retarget
        path = self.filepath

        if not path or not os.path.exists(path):
            self.report({'ERROR'}, f"File not found: {path}")
            return {'CANCELLED'}

        before = set(bpy.context.scene.objects)

        fbx_kwargs = dict(
            filepath=path,
            global_scale=s.fbx_scale,
            use_anim=True,
            anim_offset=1,
            use_custom_normals=False,
            use_image_search=False,
            use_custom_props=False,
        )
        extra_params = dict(
            use_manual_orientation=False,
            bake_space_transform=False,
            use_alpha_decals=False,
            decal_offset=0.0,
            use_subsurf=False,
            use_tspace=False,
            use_mesh_modifiers=False,
        )
        supported = _fbx_import_supported_params()
        for k, v in extra_params.items():
            if k in supported:
                fbx_kwargs[k] = v

        try:
            bpy.ops.import_scene.fbx(**fbx_kwargs)
        except Exception as e:
            self.report({'ERROR'}, f"FBX import failed: {e}")
            return {'CANCELLED'}

        after = set(bpy.context.scene.objects)
        new_objs = after - before
        new_arm = next((o for o in new_objs if o.type == 'ARMATURE'), None)

        if new_arm:
            new_arm.name = "Mixamo_Source"
            s.source_armature = new_arm
            n_mixamo = sum(1 for b in new_arm.data.bones if rt.is_mixamo_bone(b.name))
            self.report({'INFO'},
                f"Imported '{new_arm.name}' with {len(new_arm.data.bones)} bones "
                f"({n_mixamo} mixamorig bones)")
        else:
            self.report({'WARNING'}, "FBX imported but no armature found in scene.")

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class MIXAMO_OT_SelectMixamoTarget(Operator):
    """Select an existing armature in the scene as the retarget target"""
    bl_idname = "mixamo_retarget.select_target"
    bl_label = "Select as Target"

    def execute(self, context):
        s = context.scene.mixamo_retarget
        active = context.active_object
        if active and active.type == 'ARMATURE':
            s.target_armature = active
            self.report({'INFO'}, f"Target set to '{active.name}'")
        else:
            self.report({'ERROR'}, "Select an armature object first.")
        return {'FINISHED'}


class MIXAMO_OT_SelectMixamoSource(Operator):
    """Select an existing armature in the scene as the animation source"""
    bl_idname = "mixamo_retarget.select_source"
    bl_label = "Select as Source"

    def execute(self, context):
        s = context.scene.mixamo_retarget
        active = context.active_object
        if active and active.type == 'ARMATURE':
            s.source_armature = active
            self.report({'INFO'}, f"Source set to '{active.name}'")
        else:
            self.report({'ERROR'}, "Select an armature object first.")
        return {'FINISHED'}


class MIXAMO_OT_DetectSkeleton(Operator):
    """Detect human skeleton structure from the selected armature's bone positions"""
    bl_idname = "mixamo_retarget.detect_skeleton"
    bl_label = "Detect Skeleton"
    bl_description = "Detect human bone structure from bone positions (VRM-style)"

    target: StringProperty(default="source")

    def execute(self, context):
        s = context.scene.mixamo_retarget
        arm = s.source_armature if self.target == "source" else s.target_armature
        label = "Source" if self.target == "source" else "Target"

        if not arm:
            self.report({'ERROR'}, f"Set {label} Armature first.")
            return {'CANCELLED'}

        detected = rt.detect_skeleton(arm)
        lines = "\n".join(f"  {bn:40s} → {hb}" for bn, hb in detected)
        self.report({'INFO'}, f"{label}: detected {len(detected)} human bones\n{lines}")
        print(f"[Mixamo Retarget] {label} skeleton detection ({len(detected)} bones):\n{lines}")
        return {'FINISHED'}


class MIXAMO_OT_AutoMapBones(Operator):
    """Auto-match bone names between source and target armature"""
    bl_idname = "mixamo_retarget.auto_map_bones"
    bl_label = "Auto-Match Bones"
    bl_description = "Auto-detect human skeleton on both armatures and build bone mapping"

    def execute(self, context):
        s = context.scene.mixamo_retarget
        if not s.source_armature:
            self.report({'ERROR'}, "Set the Source Armature first.")
            return {'CANCELLED'}
        if not s.target_armature:
            self.report({'ERROR'}, "Set the Target Armature first.")
            return {'CANCELLED'}

        pairs = rt.build_mapping_from_human_bones(
            s.source_armature, s.target_armature
        )
        if not pairs:
            pairs = rt.auto_build_mapping(s.source_armature, s.target_armature)

        s.bone_mappings.clear()

        for src, tgt in pairs:
            item = s.bone_mappings.add()
            item.source_bone = src
            item.target_bone = tgt
            item.enabled = True

        self.report({'INFO'}, f"Auto-matched {len(pairs)} bone pairs")
        return {'FINISHED'}


class MIXAMO_OT_AddBoneMapping(Operator):
    """Add a new empty bone mapping row"""
    bl_idname = "mixamo_retarget.add_bone_mapping"
    bl_label = "Add Bone Pair"

    def execute(self, context):
        s = context.scene.mixamo_retarget
        item = s.bone_mappings.add()
        item.source_bone = ""
        item.target_bone = ""
        item.enabled = True
        s.bone_mapping_index = len(s.bone_mappings) - 1
        return {'FINISHED'}


class MIXAMO_OT_RemoveBoneMapping(Operator):
    """Remove the selected bone mapping row"""
    bl_idname = "mixamo_retarget.remove_bone_mapping"
    bl_label = "Remove Bone Pair"

    def execute(self, context):
        s = context.scene.mixamo_retarget
        idx = s.bone_mapping_index
        if 0 <= idx < len(s.bone_mappings):
            s.bone_mappings.remove(idx)
            s.bone_mapping_index = max(0, idx - 1)
        return {'FINISHED'}


class MIXAMO_OT_ApplyRetargeting(Operator):
    """Apply constraints to drive target rig from source motion"""
    bl_idname = "mixamo_retarget.apply_retargeting"
    bl_label = "Apply Constraints"

    def execute(self, context):
        s = context.scene.mixamo_retarget
        if not s.source_armature:
            self.report({'ERROR'}, "Set Source Armature.")
            return {'CANCELLED'}
        if not s.target_armature:
            self.report({'ERROR'}, "Set Target Armature.")
            return {'CANCELLED'}
        if not s.bone_mappings:
            self.report({'ERROR'}, "No bone mappings defined. Use Auto-Match or add manually.")
            return {'CANCELLED'}

        pairs = [(item.source_bone, item.target_bone, item.enabled,
                  item.retarget_mode)
                 for item in s.bone_mappings]

        n, warnings = rt.apply_retargeting_constraints(
            s.source_armature, s.target_armature, pairs,
            s.retarget_root_bone, s.auto_align_rest_pose,
        )

        for w in warnings:
            self.report({'WARNING'}, w)

        self.report({'INFO'}, f"Applied retargeting constraints to {n} bones")
        return {'FINISHED'}


class MIXAMO_OT_RemoveRetargeting(Operator):
    """Remove all retargeting constraints from target armature"""
    bl_idname = "mixamo_retarget.remove_retargeting"
    bl_label = "Remove Constraints"

    def execute(self, context):
        s = context.scene.mixamo_retarget
        if not s.target_armature:
            self.report({'ERROR'}, "Set Target Armature.")
            return {'CANCELLED'}
        n = rt.remove_retargeting_constraints(s.target_armature)
        self.report({'INFO'}, f"Removed {n} retargeting constraints")
        return {'FINISHED'}


class MIXAMO_OT_RemoveSingleRetargeting(Operator):
    """Remove retargeting constraints from the selected bone mapping's target bone"""
    bl_idname = "mixamo_retarget.remove_single_retargeting"
    bl_label = "Remove Single"

    bone_name: StringProperty(
        name="Target Bone",
        description="Remove constraints from this target bone",
        default="",
    )

    def execute(self, context):
        s = context.scene.mixamo_retarget
        if not s.target_armature:
            self.report({'ERROR'}, "Set Target Armature.")
            return {'CANCELLED'}
        bone = self.bone_name.strip()
        if not bone:
            self.report({'WARNING'}, "No target bone specified.")
            return {'CANCELLED'}
        if bone not in s.target_armature.data.bones:
            self.report({'WARNING'}, f"Bone '{bone}' not found in target armature.")
            return {'CANCELLED'}
        n = rt.remove_retargeting_constraints_for_bone(s.target_armature, bone)
        if n:
            self.report({'INFO'}, f"Removed {n} constraint(s) from '{bone}'")
        else:
            self.report({'INFO'}, f"No retargeting constraints on '{bone}'")
        return {'FINISHED'}


class MIXAMO_OT_BakeRetargeting(Operator):
    """Bake the retargeted animation into keyframes and remove constraints"""
    bl_idname = "mixamo_retarget.bake_retargeting"
    bl_label = "Bake Animation"

    def execute(self, context):
        s = context.scene.mixamo_retarget
        if not s.target_armature:
            self.report({'ERROR'}, "Set Target Armature.")
            return {'CANCELLED'}

        success = rt.bake_retargeted_animation(
            s.target_armature,
            s.bake_start_frame,
            s.bake_end_frame,
        )
        if success:
            self.report({'INFO'}, "Animation baked successfully")
        else:
            self.report({'ERROR'}, "Bake failed — check console for details")
        return {'FINISHED'} if success else {'CANCELLED'}


class MIXAMO_OT_SavePreset(Operator):
    """Save current bone mapping as a named preset"""
    bl_idname = "mixamo_retarget.save_preset"
    bl_label = "Save Preset"

    def execute(self, context):
        s = context.scene.mixamo_retarget
        prefs = context.preferences.addons[__package__].preferences
        name = s.preset_name.strip()
        if not name:
            self.report({'ERROR'}, "Enter a preset name first.")
            return {'CANCELLED'}

        pairs = [{"src": item.source_bone, "tgt": item.target_bone,
                  "en": item.enabled, "mode": item.retarget_mode}
                 for item in s.bone_mappings]
        rt.save_preset(prefs, name, pairs)
        self.report({'INFO'}, f"Preset '{name}' saved ({len(pairs)} bone pairs)")
        return {'FINISHED'}


class MIXAMO_OT_LoadPreset(Operator):
    """Load a saved bone mapping preset"""
    bl_idname = "mixamo_retarget.load_preset"
    bl_label = "Load Preset"

    preset_name: StringProperty()

    def execute(self, context):
        s = context.scene.mixamo_retarget
        prefs = context.preferences.addons[__package__].preferences
        name = self.preset_name or s.preset_name.strip()

        pairs = rt.load_preset(prefs, name)
        if pairs is None:
            self.report({'ERROR'}, f"Preset '{name}' not found.")
            return {'CANCELLED'}

        s.bone_mappings.clear()
        for p in pairs:
            item = s.bone_mappings.add()
            item.source_bone = p.get("src", "")
            item.target_bone = p.get("tgt", "")
            item.enabled = p.get("en", True)
            item.retarget_mode = p.get("mode", "COPY_ROTATION")

        self.report({'INFO'}, f"Loaded preset '{name}' ({len(pairs)} bone pairs)")
        return {'FINISHED'}


class MIXAMO_OT_DeletePreset(Operator):
    """Delete a saved bone mapping preset"""
    bl_idname = "mixamo_retarget.delete_preset"
    bl_label = "Delete Preset"

    preset_name: StringProperty()

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        name = self.preset_name
        try:
            presets = json.loads(prefs.saved_presets)
            if name in presets:
                del presets[name]
                prefs.saved_presets = json.dumps(presets)
                self.report({'INFO'}, f"Deleted preset '{name}'")
            else:
                self.report({'WARNING'}, f"Preset '{name}' not found")
        except Exception as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}


class MIXAMO_OT_ExportPresetFile(Operator):
    """Export the current bone mapping to a JSON file"""
    bl_idname = "mixamo_retarget.export_preset_file"
    bl_label = "Export Bone Map"

    filepath: StringProperty(subtype='FILE_PATH')
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        s = context.scene.mixamo_retarget
        self.filepath = (s.preset_name.strip() or "bone_map") + ".json"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        s = context.scene.mixamo_retarget
        pairs = [{"src": item.source_bone, "tgt": item.target_bone,
                  "en": item.enabled, "mode": item.retarget_mode}
                 for item in s.bone_mappings]
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(pairs, f, indent=2)
            self.report({'INFO'}, f"Exported {len(pairs)} bone pairs to {self.filepath}")
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}


class MIXAMO_OT_ImportPresetFile(Operator):
    """Import a bone mapping from a JSON file"""
    bl_idname = "mixamo_retarget.import_preset_file"
    bl_label = "Import Bone Map"

    filepath: StringProperty(subtype='FILE_PATH')
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        s = context.scene.mixamo_retarget
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                pairs = json.load(f)
            if not isinstance(pairs, list):
                self.report({'ERROR'}, "File does not contain a JSON array.")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            return {'CANCELLED'}

        s.bone_mappings.clear()
        for p in pairs:
            item = s.bone_mappings.add()
            item.source_bone = p.get("src", "")
            item.target_bone = p.get("tgt", "")
            item.enabled = p.get("en", True)
            item.retarget_mode = p.get("mode", "COPY_ROTATION")

        self.report({'INFO'}, f"Imported {len(pairs)} bone pairs from {self.filepath}")
        return {'FINISHED'}


_classes = [
    MIXAMO_OT_ImportMixamoFBX,
    MIXAMO_OT_SelectMixamoTarget,
    MIXAMO_OT_SelectMixamoSource,
    MIXAMO_OT_DetectSkeleton,
    MIXAMO_OT_AutoMapBones,
    MIXAMO_OT_AddBoneMapping,
    MIXAMO_OT_RemoveBoneMapping,
    MIXAMO_OT_ApplyRetargeting,
    MIXAMO_OT_RemoveRetargeting,
    MIXAMO_OT_RemoveSingleRetargeting,
    MIXAMO_OT_BakeRetargeting,
    MIXAMO_OT_SavePreset,
    MIXAMO_OT_LoadPreset,
    MIXAMO_OT_DeletePreset,
    MIXAMO_OT_ExportPresetFile,
    MIXAMO_OT_ImportPresetFile,
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
