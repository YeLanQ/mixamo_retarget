import bpy
from bpy.types import Panel


class MIXAMO_PT_Base:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Mixamo Retarget'


class MIXAMO_PT_BoneEditor(MIXAMO_PT_Base, Panel):
    bl_label = "Bone Editor"
    bl_idname = "MIXAMO_PT_BoneEditor"
    bl_order = 5

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def draw(self, context):
        layout = self.layout
        s = context.scene.mixamo_retarget
        cfg = s.bone_edit

        arm = context.active_object
        selected = context.selected_pose_bones if arm and arm.type == 'ARMATURE' else []

        if not selected:
            layout.label(text="Select a bone in Pose Mode", icon='INFO')
            return

        bone = selected[0]

        # --- Current values display ---
        box = layout.box()
        box.label(text=f"  {bone.name}", icon='BONE_DATA')

        loc = bone.location
        rot = bone.rotation_euler
        sca = bone.scale
        row = box.row(align=True)
        row.label(text=f"Loc  X:{loc.x:7.4f}  Y:{loc.y:7.4f}  Z:{loc.z:7.4f}")
        row = box.row(align=True)
        row.label(text=f"Rot  X:{rot.x:7.4f}  Y:{rot.y:7.4f}  Z:{rot.z:7.4f}")
        row = box.row(align=True)
        row.label(text=f"Scl  X:{sca.x:7.4f}  Y:{sca.y:7.4f}  Z:{sca.z:7.4f}")

        # --- Channel toggles ---
        layout.separator()
        box = layout.box()
        box.label(text="Channels", icon='ANIM_DATA')

        row = box.row(align=True)
        row.prop(cfg, "use_loc_x", text="X", toggle=True)
        row.prop(cfg, "use_loc_y", text="Y", toggle=True)
        row.prop(cfg, "use_loc_z", text="Z", toggle=True)
        row.label(text="  Rot:")
        row.prop(cfg, "use_rot_x", text="X", toggle=True)
        row.prop(cfg, "use_rot_y", text="Y", toggle=True)
        row.prop(cfg, "use_rot_z", text="Z", toggle=True)
        row.label(text="  Scl:")
        row.prop(cfg, "use_scale_x", text="X", toggle=True)
        row.prop(cfg, "use_scale_y", text="Y", toggle=True)
        row.prop(cfg, "use_scale_z", text="Z", toggle=True)

        row = box.row(align=True)
        row.operator("mixamo_retarget.bone_edit_channels_toggle", text="All").state = True
        row.operator("mixamo_retarget.bone_edit_channels_toggle", text="None").state = False

        # --- Increment & operation ---
        layout.separator()
        box = layout.box()
        box.label(text="Operation", icon='MODIFIER')
        row = box.row(align=True)
        row.prop(cfg, "operation", text="")
        row.prop(cfg, "increment", text="")
        row.operator("mixamo_retarget.bone_edit_snap_values", text="", icon='COPYDOWN')

        # --- Frame range ---
        box = layout.box()
        box.label(text="Apply To", icon='TIME')
        row = box.row(align=True)
        row.prop(cfg, "apply_mode", text="")
        if cfg.apply_mode == 'RANGE':
            row.prop(cfg, "frame_start", text="Start")
            row.prop(cfg, "frame_end", text="End")

        # --- Execute ---
        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("mixamo_retarget.bone_transform_edit", text="Execute", icon='PLAY')


class MIXAMO_PT_Import(MIXAMO_PT_Base, Panel):
    bl_label = "Import Mixamo FBX"
    bl_idname = "MIXAMO_PT_Import"
    bl_order = 10

    def draw(self, context):
        layout = self.layout
        s = context.scene.mixamo_retarget

        box = layout.box()
        box.label(text="Import Settings:", icon='PREFERENCES')
        box.prop(s, "fbx_scale", text="Scale")

        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("mixamo_retarget.import_mixamo_fbx", text="Import Mixamo FBX", icon='IMPORT')

        layout.separator()
        box = layout.box()
        box.label(text="New Mixamo Skeleton (65 bones):", icon='ARMATURE_DATA')
        row = box.row(align=True)
        row.prop(s, "skeleton_scale", text="Scale")
        row.prop(s, "skeleton_name", text="")
        row = box.row(align=True)
        row.prop(s, "skeleton_orientation", text="Orientation")
        box.operator("mixamo_retarget.new_mixamo_skeleton", text="Create Armature")

        if s.source_armature:
            box = layout.box()
            box.label(text="Source Armature:", icon='ARMATURE_DATA')
            box.prop(s, "source_armature", text="")

    def draw_header(self, context):
        self.layout.label(text="", icon='IMPORT')


class MIXAMO_PT_Retarget(MIXAMO_PT_Base, Panel):
    bl_label = "Retarget"
    bl_idname = "MIXAMO_PT_Retarget"
    bl_order = 20

    def draw(self, context):
        layout = self.layout
        s = context.scene.mixamo_retarget

        box = layout.box()
        box.label(text="Armatures", icon='ARMATURE_DATA')
        row = box.row(align=True)
        row.prop(s, "source_armature", text="Source")
        row.operator("mixamo_retarget.select_source", text="", icon='EYEDROPPER')

        row = box.row(align=True)
        row.prop(s, "target_armature", text="Target")
        row.operator("mixamo_retarget.select_target", text="", icon='EYEDROPPER')

        box.prop(s, "retarget_root_bone", text="Root Bone")
        box.prop(s, "auto_align_rest_pose", text="Align Rest Pose")

        layout.separator()

        # Skeleton detection buttons
        row = layout.row(align=True)
        if s.source_armature:
            row.operator("mixamo_retarget.detect_skeleton",
                         text="Detect Source", icon='BONE_DATA').target = "source"
        if s.target_armature:
            row.operator("mixamo_retarget.detect_skeleton",
                         text="Detect Target", icon='BONE_DATA').target = "target"

        layout.separator()

        layout.label(text="Bone Mapping:", icon='BONE_DATA')

        if s.source_armature and s.target_armature:
            layout.operator("mixamo_retarget.auto_map_bones",
                            text="Auto-Match Bones", icon='SHADERFX')

        row = layout.row()
        row.template_list(
            "MIXAMO_UL_BoneMappings", "",
            s, "bone_mappings",
            s, "bone_mapping_index",
            rows=6,
        )

        col = row.column(align=True)
        col.operator("mixamo_retarget.add_bone_mapping", text="", icon='ADD')
        col.operator("mixamo_retarget.remove_bone_mapping", text="", icon='REMOVE')

        layout.separator()

        row = layout.row(align=True)
        row.operator("mixamo_retarget.apply_retargeting", text="Apply Constraints", icon='CONSTRAINT_BONE')
        row.operator("mixamo_retarget.remove_retargeting", text="", icon='X')


class MIXAMO_PT_Bake(MIXAMO_PT_Base, Panel):
    bl_label = "Bake & Interpolate"
    bl_idname = "MIXAMO_PT_Bake"
    bl_order = 30

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def draw(self, context):
        layout = self.layout
        s = context.scene.mixamo_retarget

        box = layout.box()
        box.label(text="Bake to Keyframes", icon='RENDER_ANIMATION')
        row = box.row(align=True)
        row.prop(s, "bake_start_frame", text="Start")
        row.prop(s, "bake_end_frame", text="End")
        box.operator("mixamo_retarget.bake_retargeting",
                     text="Bake & Remove Constraints", icon='NLA_PUSHDOWN')

        layout.separator()

        box = layout.box()
        box.label(text="Bone In-Betweening (补帧)", icon='KEYINGSET')
        box.prop(s, "interp_step", text="Frame Step")
        box.prop(s, "smoothing_passes", text="Smoothing Passes")
        box.prop(s, "interp_use_mirror")

        col = box.column(align=True)

        row = col.row(align=True)
        op_pred = row.operator("mixamo_retarget.interpolate_bones",
                               text="Predict (预测)", icon='IPO_BEZIER')
        op_pred.mode = "predict"
        op_smooth2 = row.operator("mixamo_retarget.interpolate_bones",
                                  text="Smooth", icon='SMOOTHCURVE')
        op_smooth2.mode = "smooth"

        row = col.row(align=True)
        op_gaps = row.operator("mixamo_retarget.interpolate_bones",
                               text="Fill Gaps", icon='KEYFRAME_HLT')
        op_gaps.mode = "gaps"


class MIXAMO_PT_Presets(MIXAMO_PT_Base, Panel):
    bl_label = "Presets"
    bl_idname = "MIXAMO_PT_Presets"
    bl_order = 40
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        s = context.scene.mixamo_retarget

        box = layout.box()
        box.label(text="Bone Map Presets", icon='PRESET')
        row = box.row(align=True)
        row.prop(s, "preset_name", text="")
        row.operator("mixamo_retarget.save_preset", text="", icon='FILE_TICK')
        row.operator("mixamo_retarget.load_preset", text="", icon='IMPORT').preset_name = s.preset_name

        try:
            prefs = context.preferences.addons[__package__].preferences
            from . import retarget as rt
            preset_names = rt.list_presets(prefs)
        except Exception:
            preset_names = []

        if preset_names:
            col = box.column(align=True)
            for name in preset_names:
                row2 = col.row(align=True)
                op_load = row2.operator("mixamo_retarget.load_preset", text=name, icon='IMPORT')
                op_load.preset_name = name
                op_del = row2.operator("mixamo_retarget.delete_preset", text="", icon='TRASH')
                op_del.preset_name = name

        row = box.row(align=True)
        row.operator("mixamo_retarget.export_preset_file", text="Export to File", icon='EXPORT')
        row.operator("mixamo_retarget.import_preset_file", text="Import from File", icon='IMPORT')


_classes = [
    MIXAMO_PT_BoneEditor,
    MIXAMO_PT_Import,
    MIXAMO_PT_Retarget,
    MIXAMO_PT_Bake,
    MIXAMO_PT_Presets,
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
