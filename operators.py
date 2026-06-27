import bpy
import os
import json
from bpy.types import Operator, Armature
from bpy.props import StringProperty, BoolProperty, IntProperty, EnumProperty
from mathutils import Vector

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


class MIXAMO_OT_NewMixamoSkeleton(Operator):
    """Create a Mixamo skeleton identical to mixamo.fbx structure (65 bones)"""
    bl_idname = "mixamo_retarget.new_mixamo_skeleton"
    bl_label = "New Mixamo Skeleton"
    bl_description = "Create a Mixamo-standard armature with exact bone data from mixamo.fbx"
    bl_options = {"REGISTER", "UNDO"}

    # Exact bone data + roll from mixamo.fbx. Coords in cm, armature.scale converts to Blender units.
    # Order matches FBX: parents precede children.
    _BONE_DATA = [
        ("mixamorig:Hips", "", (-7.727e-06, 104.274872, 1.554316), (-1.302e-05, 114.833229, 1.690704), 0.0),
        ("mixamorig:Spine", "mixamorig:Hips", (-1.283e-05, 114.456467, 1.685837), (-1.284e-05, 124.350426, 0.215126), -0.0),
        ("mixamorig:Spine1", "mixamorig:Spine", (-1.284e-05, 124.350426, 0.215126), (-1.285e-05, 133.571182, -1.155516), -0.0),
        ("mixamorig:Spine2", "mixamorig:Spine1", (-1.285e-05, 133.571182, -1.155516), (-1.186e-05, 147.171143, -2.82016), -0.0),
        ("mixamorig:Neck", "mixamorig:Spine2", (-1.163e-05, 150.3116, -3.204555), (-1.093e-05, 160.003632, -4.390865), -0.0),
        ("mixamorig:Head", "mixamorig:Neck", (-1.117e-05, 159.929474, -1.519546), (-9.489e-06, 183.036057, -4.347806), -0.0),
        ("mixamorig:HeadTop_End", "mixamorig:Head", (-9.032e-06, 181.966858, 5.981553), (-7.353e-06, 205.073441, 3.153292), -0.0),
        ("mixamorig:RightShoulder", "mixamorig:Spine2", (-4.569982, 144.586105, -3.316402), (-15.162832, 144.061295, -5.548502), -1.7887),
        ("mixamorig:RightArm", "mixamorig:RightShoulder", (-15.162832, 144.061295, -5.548502), (-43.004356, 144.061295, -5.548497), -1.5708),
        ("mixamorig:RightForeArm", "mixamorig:RightArm", (-43.004353, 144.06131, -5.548507), (-71.333199, 144.06131, -5.548503), -1.5708),
        ("mixamorig:RightHand", "mixamorig:RightForeArm", (-71.333191, 144.061295, -5.548489), (-79.559967, 144.061295, -5.548488), -1.5708),
        ("mixamorig:RightHandThumb1", "mixamorig:RightHand", (-73.797997, 142.487305, -2.866636), (-77.013184, 140.614532, -0.942356), -0.77),
        ("mixamorig:RightHandThumb2", "mixamorig:RightHandThumb1", (-77.013191, 140.614532, -0.942354), (-79.668022, 139.086548, 0.570252), -0.8034),
        ("mixamorig:RightHandThumb3", "mixamorig:RightHandThumb2", (-79.668015, 139.086548, 0.570255), (-81.686836, 137.93454, 1.67831), -0.828),
        ("mixamorig:RightHandThumb4", "mixamorig:RightHandThumb3", (-81.686836, 137.93454, 1.67831), (-83.574936, 136.7892, 3.002623), -0.9052),
        ("mixamorig:RightHandIndex1", "mixamorig:RightHand", (-80.441475, 143.543427, -3.288654), (-84.141472, 143.543427, -3.287439), -1.5705),
        ("mixamorig:RightHandIndex2", "mixamorig:RightHandIndex1", (-84.141472, 143.543427, -3.287439), (-86.991486, 143.543457, -3.287961), -1.571),
        ("mixamorig:RightHandIndex3", "mixamorig:RightHandIndex2", (-86.991486, 143.543457, -3.287961), (-89.763664, 143.543442, -3.28798), -1.5708),
        ("mixamorig:RightHandIndex4", "mixamorig:RightHandIndex3", (-89.763664, 143.543442, -3.28798), (-92.535851, 143.543442, -3.288483), -1.569),
        ("mixamorig:RightHandMiddle1", "mixamorig:RightHand", (-80.8657, 144.061249, -5.548513), (-84.565712, 144.061249, -5.544801), -1.5698),
        ("mixamorig:RightHandMiddle2", "mixamorig:RightHandMiddle1", (-84.565712, 144.061249, -5.544801), (-87.515701, 144.061264, -5.546855), -1.5715),
        ("mixamorig:RightHandMiddle3", "mixamorig:RightHandMiddle2", (-87.515701, 144.061264, -5.546855), (-90.462326, 144.061264, -5.547009), -1.5708),
        ("mixamorig:RightHandMiddle4", "mixamorig:RightHandMiddle3", (-90.462326, 144.061264, -5.547009), (-93.408958, 144.061279, -5.548146), -1.5693),
        ("mixamorig:RightHandRing1", "mixamorig:RightHand", (-80.43679, 144.018219, -7.413624), (-83.816063, 144.018219, -7.414678), -1.5711),
        ("mixamorig:RightHandRing2", "mixamorig:RightHandRing1", (-83.816063, 144.018219, -7.414678), (-86.705757, 144.018234, -7.414299), -1.5707),
        ("mixamorig:RightHandRing3", "mixamorig:RightHandRing2", (-86.705757, 144.018234, -7.414299), (-89.344566, 144.018234, -7.413358), -1.5704),
        ("mixamorig:RightHandRing4", "mixamorig:RightHandRing3", (-89.344566, 144.018234, -7.413358), (-91.983368, 144.018234, -7.408198), -1.5685),
        ("mixamorig:RightHandPinky1", "mixamorig:RightHand", (-79.409866, 143.574585, -9.354769), (-83.009872, 143.574554, -9.358516), -1.5718),
        ("mixamorig:RightHandPinky2", "mixamorig:RightHandPinky1", (-83.009872, 143.574554, -9.358516), (-85.109848, 143.574539, -9.364256), -1.5735),
        ("mixamorig:RightHandPinky3", "mixamorig:RightHandPinky2", (-85.109848, 143.574539, -9.364256), (-87.225624, 143.574509, -9.367936), -1.5725),
        ("mixamorig:RightHandPinky4", "mixamorig:RightHandPinky3", (-87.225624, 143.574509, -9.367936), (-89.3414, 143.574493, -9.371443), -1.5693),
        ("mixamorig:LeftShoulder", "mixamorig:Spine2", (4.570434, 144.585907, -3.316374), (15.162806, 144.06131, -5.548495), 1.7887),
        ("mixamorig:LeftArm", "mixamorig:LeftShoulder", (15.162806, 144.06131, -5.548495), (43.004326, 144.061295, -5.548472), 1.5708),
        ("mixamorig:LeftForeArm", "mixamorig:LeftArm", (43.004326, 144.061295, -5.548472), (71.333168, 144.061249, -5.548449), 1.5708),
        ("mixamorig:LeftHand", "mixamorig:LeftForeArm", (71.33316, 144.061249, -5.548455), (79.561035, 144.061234, -5.548448), 1.5708),
        ("mixamorig:LeftHandThumb1", "mixamorig:LeftHand", (73.799301, 142.485062, -2.86672), (77.017113, 140.613007, -0.950229), 0.7734),
        ("mixamorig:LeftHandThumb2", "mixamorig:LeftHandThumb1", (77.017105, 140.613007, -0.950233), (79.673126, 139.084198, 0.564276), 0.8029),
        ("mixamorig:LeftHandThumb3", "mixamorig:LeftHandThumb2", (79.673126, 139.084198, 0.564275), (81.694016, 137.930115, 1.679409), 0.8246),
        ("mixamorig:LeftHandThumb4", "mixamorig:LeftHandThumb3", (81.694016, 137.93013, 1.679407), (83.602867, 136.779297, 2.979897), 0.9351),
        ("mixamorig:LeftHandIndex1", "mixamorig:LeftHand", (80.442467, 143.543213, -3.288584), (84.142464, 143.543198, -3.288907), 1.5709),
        ("mixamorig:LeftHandIndex2", "mixamorig:LeftHandIndex1", (84.142464, 143.543198, -3.288907), (86.99247, 143.543182, -3.288556), 1.5707),
        ("mixamorig:LeftHandIndex3", "mixamorig:LeftHandIndex2", (86.99247, 143.543182, -3.288556), (89.767326, 143.543167, -3.288583), 1.5708),
        ("mixamorig:LeftHandIndex4", "mixamorig:LeftHandIndex3", (89.767326, 143.543167, -3.288583), (92.542191, 143.543167, -3.288682), 1.5701),
        ("mixamorig:LeftHandMiddle1", "mixamorig:LeftHand", (80.866562, 144.061279, -5.548411), (84.566559, 144.061279, -5.548642), 1.5709),
        ("mixamorig:LeftHandMiddle2", "mixamorig:LeftHandMiddle1", (84.566559, 144.061279, -5.548642), (87.516556, 144.061264, -5.548701), 1.5708),
        ("mixamorig:LeftHandMiddle3", "mixamorig:LeftHandMiddle2", (87.516556, 144.061264, -5.548701), (90.469421, 144.061264, -5.548638), 1.5708),
        ("mixamorig:LeftHandMiddle4", "mixamorig:LeftHandMiddle3", (90.469421, 144.061264, -5.548638), (93.422279, 144.061264, -5.54841), 1.5687),
        ("mixamorig:LeftHandRing1", "mixamorig:LeftHand", (80.437691, 144.018219, -7.413529), (83.5877, 144.018219, -7.413487), 1.5708),
        ("mixamorig:LeftHandRing2", "mixamorig:LeftHandRing1", (83.5877, 144.018219, -7.413487), (86.537689, 144.018204, -7.413447), 1.5708),
        ("mixamorig:LeftHandRing3", "mixamorig:LeftHandRing2", (86.537689, 144.018204, -7.413447), (89.182007, 144.018204, -7.413414), 1.5708),
        ("mixamorig:LeftHandRing4", "mixamorig:LeftHandRing3", (89.182007, 144.018188, -7.413391), (91.826324, 144.018188, -7.413271), 1.5717),
        ("mixamorig:LeftHandPinky1", "mixamorig:LeftHand", (79.410942, 143.574371, -9.354712), (83.010902, 143.574402, -9.339987), 1.5667),
        ("mixamorig:LeftHandPinky2", "mixamorig:LeftHandPinky1", (83.010902, 143.574402, -9.339987), (85.110901, 143.574432, -9.332282), 1.5671),
        ("mixamorig:LeftHandPinky3", "mixamorig:LeftHandPinky2", (85.110901, 143.574432, -9.332282), (87.236404, 143.574432, -9.324767), 1.5673),
        ("mixamorig:LeftHandPinky4", "mixamorig:LeftHandPinky3", (87.236404, 143.574432, -9.324767), (89.361916, 143.574448, -9.31851), 1.5663),
        ("mixamorig:RightUpLeg", "mixamorig:Hips", (-8.207794, 97.523209, -0.045244), (-8.207795, 53.15308, 0.300695), 3.1416),
        ("mixamorig:RightLeg", "mixamorig:RightUpLeg", (-8.207795, 53.15308, 0.300695), (-8.207794, 8.729401, -2.742842), 3.1416),
        ("mixamorig:RightFoot", "mixamorig:RightLeg", (-8.207794, 8.729401, -2.742842), (-8.207798, 0.000729, 7.967721), 3.1416),
        ("mixamorig:RightToeBase", "mixamorig:RightFoot", (-8.207797, 0.000728, 7.967721), (-8.2078, 5.2e-05, 17.245842), 3.1416),
        ("mixamorig:RightToe_End", "mixamorig:RightToeBase", (-8.207799, 5.2e-05, 17.245842), (-8.207802, -0.000624, 26.523964), -3.1184),
        ("mixamorig:LeftUpLeg", "mixamorig:Hips", (8.207784, 97.523178, -0.04524), (8.207782, 53.153145, 0.301718), 3.1416),
        ("mixamorig:LeftLeg", "mixamorig:LeftUpLeg", (8.207782, 53.153145, 0.301718), (8.207782, 8.729473, -2.742675), -3.1416),
        ("mixamorig:LeftFoot", "mixamorig:LeftLeg", (8.207782, 8.729473, -2.742675), (8.207779, 0.000805, 7.967885), 3.1416),
        ("mixamorig:LeftToeBase", "mixamorig:LeftFoot", (8.207779, 0.000805, 7.967887), (8.207776, 0.000128, 17.246023), 3.1416),
        ("mixamorig:LeftToe_End", "mixamorig:LeftToeBase", (8.207776, 0.000129, 17.246023), (8.207773, -0.000548, 26.524158), 3.1179),
    ]

    def execute(self, context):
        s = context.scene.mixamo_retarget

        bpy.ops.object.add(type="ARMATURE", enter_editmode=True, location=(0, 0, 0))
        armature = context.object
        if not armature:
            return {"CANCELLED"}
        armature_data = armature.data
        if not isinstance(armature_data, Armature):
            return {"CANCELLED"}

        armature.name = s.skeleton_name
        armature_data.name = s.skeleton_name
        armature_data.display_type = 'OCTAHEDRAL'

        # Keep bone data in original cm coordinates with proper armature scale,
        # matching the structure of an imported Mixamo FBX.
        armature.scale = (s.skeleton_scale,) * 3
        bone_map = {}
        for name, parent_name, head, tail, roll in self._BONE_DATA:
            eb = armature_data.edit_bones.new(name)
            eb.head = Vector(head)
            eb.tail = Vector(tail)
            eb.roll = roll
            if parent_name:
                eb.parent = bone_map[parent_name]
                eb.use_connect = False
            bone_map[name] = eb

        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'},
            f"Created '{armature.name}' ({len(armature_data.bones)} bones)")
        return {"FINISHED"}


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


class MIXAMO_OT_InterpolateBones(Operator):
    """Fill missing keyframes, fill frame gaps, and smooth jerky bone animations (补帧)"""
    bl_idname = "mixamo_retarget.interpolate_bones"
    bl_label = "Interpolate Bones"
    bl_description = "补帧: Fill missing keyframes and smooth jerky bone animation based on overall motion"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Mode",
        description="Interpolation mode",
        items=[
            ("all", "All (补帧)", "Fill missing + fill gaps + smooth"),
            ("missing", "Fill Missing", "Create keyframes for bones without any animation"),
            ("gaps", "Fill Gaps", "Fill in missing frames on existing F-curves"),
            ("smooth", "Smooth Only", "Smooth jerky F-curves (moving average)"),
        ],
        default="all",
    )

    def execute(self, context):
        s = context.scene.mixamo_retarget
        arm = s.target_armature

        if not arm:
            self.report({'ERROR'}, "Set Target Armature first.")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')

        fill_missing = self.mode in ("missing", "all")
        fill_gaps = self.mode in ("gaps", "all")
        smooth = self.mode in ("smooth", "all")

        stats = rt.interpolate_armature_animation(
            arm,
            s.bake_start_frame,
            s.bake_end_frame,
            fill_missing=fill_missing,
            fill_gaps=fill_gaps,
            smooth=smooth,
            smoothing_passes=s.smoothing_passes,
            step=s.interp_step,
            use_mirror=s.interp_use_mirror,
        )

        total_added = sum(v['keyframes_added'] for v in stats.values())
        bones_affected = sum(
            1 for v in stats.values()
            if v['keyframes_added'] > 0 or v['actions']
        )
        bones_missing = sum(
            1 for v in stats.values()
            if any("missing" in a for a in v['actions'])
        )
        bones_mirrored = sum(
            1 for v in stats.values()
            if any("mirror" in a for a in v['actions'])
        )
        bones_smoothed = sum(
            1 for v in stats.values()
            if any("smoothed" in a for a in v['actions'])
        )

        details = f"({total_added} keyframes, {bones_missing} missing, {bones_mirrored} mirrored, {bones_smoothed} smoothed)"
        self.report({'INFO'}, f"Interpolated {bones_affected} bones {details}")
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
    MIXAMO_OT_NewMixamoSkeleton,
    MIXAMO_OT_SelectMixamoTarget,
    MIXAMO_OT_SelectMixamoSource,
    MIXAMO_OT_DetectSkeleton,
    MIXAMO_OT_AutoMapBones,
    MIXAMO_OT_AddBoneMapping,
    MIXAMO_OT_RemoveBoneMapping,
    MIXAMO_OT_ApplyRetargeting,
    MIXAMO_OT_RemoveRetargeting,
    MIXAMO_OT_RemoveSingleRetargeting,
    MIXAMO_OT_InterpolateBones,
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
