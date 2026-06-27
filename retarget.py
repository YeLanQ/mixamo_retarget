import bpy
import mathutils
import re

CONSTRAINT_PREFIX = "MIXAMO_RETARGET_"

MIXAMO_BONE_HINTS = [
    ("Hips",            ["hips", "pelvis", "root", "Hip", "Pelvis", "mixamorig:Hips"]),
    ("Spine",           ["spine", "Spine1", "mixamorig:Spine"]),
    ("Spine1",          ["spine1", "spine_01", "mixamorig:Spine1"]),
    ("Spine2",          ["spine2", "chest", "mixamorig:Spine2"]),
    ("Neck",            ["neck", "Neck1", "mixamorig:Neck"]),
    ("Head",            ["head", "Head", "mixamorig:Head"]),
    ("LeftShoulder",    ["l_shoulder", "shoulder.L", "mixamorig:LeftShoulder", "LeftShoulder"]),
    ("LeftArm",         ["upper_arm.L", "l_arm", "mixamorig:LeftArm", "LeftUpArm"]),
    ("LeftForeArm",     ["forearm.L", "l_forearm", "mixamorig:LeftForeArm"]),
    ("LeftHand",        ["hand.L", "l_hand", "mixamorig:LeftHand"]),
    ("RightShoulder",   ["r_shoulder", "shoulder.R", "mixamorig:RightShoulder", "RightShoulder"]),
    ("RightArm",        ["upper_arm.R", "r_arm", "mixamorig:RightArm", "RightUpArm"]),
    ("RightForeArm",    ["forearm.R", "r_forearm", "mixamorig:RightForeArm"]),
    ("RightHand",       ["hand.R", "r_hand", "mixamorig:RightHand"]),
    ("LeftUpLeg",       ["thigh.L", "l_thigh", "mixamorig:LeftUpLeg", "LeftThigh"]),
    ("LeftLeg",         ["shin.L", "l_shin", "mixamorig:LeftLeg", "LeftShin"]),
    ("LeftFoot",        ["foot.L", "l_foot", "mixamorig:LeftFoot"]),
    ("LeftToeBase",     ["toe.L", "l_toe", "mixamorig:LeftToeBase"]),
    ("RightUpLeg",      ["thigh.R", "r_thigh", "mixamorig:RightUpLeg", "RightThigh"]),
    ("RightLeg",        ["shin.R", "r_shin", "mixamorig:RightLeg", "RightShin"]),
    ("RightFoot",       ["foot.R", "r_foot", "mixamorig:RightFoot"]),
    ("RightToeBase",    ["toe.R", "r_toe", "mixamorig:RightToeBase"]),
    ("LeftHandThumb1",  ["mixamorig:LeftHandThumb1", "l_thumb1"]),
    ("LeftHandThumb2",  ["mixamorig:LeftHandThumb2", "l_thumb2"]),
    ("LeftHandThumb3",  ["mixamorig:LeftHandThumb3", "l_thumb3"]),
    ("LeftHandIndex1",  ["mixamorig:LeftHandIndex1", "l_index1"]),
    ("LeftHandIndex2",  ["mixamorig:LeftHandIndex2", "l_index2"]),
    ("LeftHandIndex3",  ["mixamorig:LeftHandIndex3", "l_index3"]),
    ("LeftHandMiddle1", ["mixamorig:LeftHandMiddle1", "l_middle1"]),
    ("LeftHandMiddle2", ["mixamorig:LeftHandMiddle2", "l_middle2"]),
    ("LeftHandMiddle3", ["mixamorig:LeftHandMiddle3", "l_middle3"]),
    ("LeftHandRing1",   ["mixamorig:LeftHandRing1", "l_ring1"]),
    ("LeftHandRing2",   ["mixamorig:LeftHandRing2", "l_ring2"]),
    ("LeftHandRing3",   ["mixamorig:LeftHandRing3", "l_ring3"]),
    ("LeftHandPinky1",  ["mixamorig:LeftHandPinky1", "l_pinky1"]),
    ("LeftHandPinky2",  ["mixamorig:LeftHandPinky2", "l_pinky2"]),
    ("LeftHandPinky3",  ["mixamorig:LeftHandPinky3", "l_pinky3"]),
    ("RightHandThumb1", ["mixamorig:RightHandThumb1", "r_thumb1"]),
    ("RightHandThumb2", ["mixamorig:RightHandThumb2", "r_thumb2"]),
    ("RightHandThumb3", ["mixamorig:RightHandThumb3", "r_thumb3"]),
    ("RightHandIndex1", ["mixamorig:RightHandIndex1", "r_index1"]),
    ("RightHandIndex2", ["mixamorig:RightHandIndex2", "r_index2"]),
    ("RightHandIndex3", ["mixamorig:RightHandIndex3", "r_index3"]),
    ("RightHandMiddle1",["mixamorig:RightHandMiddle1", "r_middle1"]),
    ("RightHandMiddle2",["mixamorig:RightHandMiddle2", "r_middle2"]),
    ("RightHandMiddle3",["mixamorig:RightHandMiddle3", "r_middle3"]),
    ("RightHandRing1",  ["mixamorig:RightHandRing1", "r_ring1"]),
    ("RightHandRing2",  ["mixamorig:RightHandRing2", "r_ring2"]),
    ("RightHandRing3",  ["mixamorig:RightHandRing3", "r_ring3"]),
    ("RightHandPinky1", ["mixamorig:RightHandPinky1", "r_pinky1"]),
    ("RightHandPinky2", ["mixamorig:RightHandPinky2", "r_pinky2"]),
    ("RightHandPinky3", ["mixamorig:RightHandPinky3", "r_pinky3"]),
]


def _normalize(name: str) -> str:
    name = name.lower()
    if ":" in name:
        name = name.split(":")[-1]
    return re.sub(r"[^a-z0-9_]", "", name)


def is_mixamo_bone(name: str) -> bool:
    return "mixamorig" in name.lower()


def auto_build_mapping(source_arm: bpy.types.Object,
                       target_arm: bpy.types.Object) -> list[tuple[str, str]]:
    src_name_list = list(source_arm.data.bones.keys())
    tgt_name_list = list(target_arm.data.bones.keys())
    src_norm_map = {b.name: _normalize(b.name) for b in source_arm.data.bones}
    tgt_norm_map = {b.name: _normalize(b.name) for b in target_arm.data.bones}

    def _find_bone(name: str, norm_map: dict, name_list: list) -> str | None:
        exact = norm_map.get(name)
        if exact is not None:
            return name
        norm = _normalize(name)
        for bn in name_list:
            if norm == norm_map[bn]:
                return bn
        return None

    result = []
    mapped_src_names = set()
    mapped_tgt_names = set()

    for src_hint, alternatives in MIXAMO_BONE_HINTS:
        src_matched = _find_bone(src_hint, src_norm_map, src_name_list)
        if src_matched is None:
            for alt in alternatives:
                src_matched = _find_bone(alt, src_norm_map, src_name_list)
                if src_matched:
                    break
        if src_matched is None or src_matched in mapped_src_names:
            continue

        tgt_matched = _find_bone(src_hint, tgt_norm_map, tgt_name_list)
        if tgt_matched is None:
            for alt in alternatives:
                tgt_matched = _find_bone(alt, tgt_norm_map, tgt_name_list)
                if tgt_matched:
                    break
        if tgt_matched is None or tgt_matched in mapped_tgt_names:
            continue

        result.append((src_matched, tgt_matched))
        mapped_src_names.add(src_matched)
        mapped_tgt_names.add(tgt_matched)

    return result


def apply_retargeting_constraints(
    source_arm: bpy.types.Object,
    target_arm: bpy.types.Object,
    bone_pairs: list,
    root_bone: str = "",
    align_rest: bool = True,
) -> tuple[int, list[str]]:
    source_arm.hide_viewport = False
    target_arm.hide_viewport = False

    tgt_pose = target_arm.pose
    applied = 0
    warnings = []

    for entry in bone_pairs:
        if len(entry) == 4:
            src_name, tgt_name, enabled, mode = entry
        elif len(entry) == 3:
            src_name, tgt_name, enabled = entry
            mode = "COPY_ROTATION"
        else:
            continue

        if not enabled:
            continue

        tgt_pbone = tgt_pose.bones.get(tgt_name)
        if not tgt_pbone:
            warnings.append(f"Target bone '{tgt_name}' not found — skipped.")
            continue
        if src_name not in source_arm.data.bones:
            warnings.append(f"Source bone '{src_name}' not in source armature — skipped.")
            continue

        for c in list(tgt_pbone.constraints):
            if c.name.startswith(CONSTRAINT_PREFIX):
                tgt_pbone.constraints.remove(c)

        if root_bone:
            is_root = (tgt_name == root_bone)
        else:
            src_name_lower = src_name.lower()
            is_root = any(k in src_name_lower for k in ("hips", "pelvis", "root"))

        if mode == "COPY_ROTATION":
            _add_copy_rotation(tgt_pbone, source_arm, src_name, is_root)
        elif mode == "COPY_TRANSFORMS":
            _add_copy_transforms(tgt_pbone, source_arm, src_name)
        elif mode == "CHILD_OF":
            _add_child_of(tgt_pbone, source_arm, target_arm, src_name, is_root)
        elif mode == "CHILD_OF_ROTATION":
            _add_child_of(tgt_pbone, source_arm, target_arm, src_name, is_root, rotation_only=True)
        else:
            warnings.append(f"Unknown mode '{mode}' for '{tgt_name}' — using Copy Rotation.")
            _add_copy_rotation(tgt_pbone, source_arm, src_name, is_root)

        applied += 1

    return applied, warnings


def _add_copy_rotation(pbone, source_arm, src_name: str, is_root: bool = False) -> None:
    if is_root:
        loc = pbone.constraints.new("COPY_LOCATION")
        loc.name = CONSTRAINT_PREFIX + "Location"
        loc.target = source_arm
        loc.subtarget = src_name
        loc.use_offset = False

    rot = pbone.constraints.new("COPY_ROTATION")
    rot.name = CONSTRAINT_PREFIX + "Rotation"
    rot.target = source_arm
    rot.subtarget = src_name
    rot.mix_mode = 'REPLACE'
    rot.owner_space = 'WORLD'
    rot.target_space = 'WORLD'


def _add_copy_transforms(pbone, source_arm, src_name: str) -> None:
    ct = pbone.constraints.new("COPY_TRANSFORMS")
    ct.name = CONSTRAINT_PREFIX + "CopyTransforms"
    ct.target = source_arm
    ct.subtarget = src_name
    ct.mix_mode = 'REPLACE'
    ct.owner_space = 'LOCAL'
    ct.target_space = 'LOCAL'


def _add_child_of(pbone, source_arm, target_arm, src_name: str,
                  is_root: bool = False,
                  rotation_only: bool = False) -> None:
    use_location = not rotation_only

    if is_root and use_location:
        loc = pbone.constraints.new("COPY_LOCATION")
        loc.name = CONSTRAINT_PREFIX + "Location"
        loc.target = source_arm
        loc.subtarget = src_name
        loc.use_offset = False

    co = pbone.constraints.new("CHILD_OF")
    co.name = CONSTRAINT_PREFIX + ("ChildOfRotation" if rotation_only else "ChildOf")
    co.target = source_arm
    co.subtarget = src_name
    co.use_location_x = use_location
    co.use_location_y = use_location
    co.use_location_z = use_location
    co.use_rotation_x = True
    co.use_rotation_y = True
    co.use_rotation_z = True
    co.use_scale_x = False
    co.use_scale_y = False
    co.use_scale_z = False

    src_bone = source_arm.data.bones.get(src_name)
    if src_bone:
        src_rest_world = source_arm.matrix_world @ src_bone.matrix_local
        tgt_current_world = target_arm.matrix_world @ pbone.matrix
        co.inverse_matrix = src_rest_world.inverted() @ tgt_current_world
    else:
        co.inverse_matrix = mathutils.Matrix.Identity(4)


def remove_retargeting_constraints(target_arm: bpy.types.Object) -> int:
    removed = 0
    for pbone in target_arm.pose.bones:
        for c in list(pbone.constraints):
            if c.name.startswith(CONSTRAINT_PREFIX):
                pbone.constraints.remove(c)
                removed += 1
    return removed


def remove_retargeting_constraints_for_bone(target_arm: bpy.types.Object,
                                            bone_name: str) -> int:
    removed = 0
    pbone = target_arm.pose.bones.get(bone_name)
    if pbone:
        for c in list(pbone.constraints):
            if c.name.startswith(CONSTRAINT_PREFIX):
                pbone.constraints.remove(c)
                removed += 1
    return removed


def bake_retargeted_animation(
    target_arm: bpy.types.Object,
    frame_start: int,
    frame_end: int,
) -> bool:
    try:
        bpy.ops.object.select_all(action='DESELECT')
        target_arm.select_set(True)
        bpy.context.view_layer.objects.active = target_arm

        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')

        bpy.ops.nla.bake(
            frame_start=frame_start,
            frame_end=frame_end,
            only_selected=False,
            visual_keying=True,
            clear_constraints=True,
            clear_parents=False,
            use_current_action=True,
            bake_types={'POSE'},
        )

        bpy.ops.object.mode_set(mode='OBJECT')
        return True

    except Exception as e:
        print(f"[Mixamo Retarget] Bake error: {e}")
        return False


def save_preset(prefs, preset_name: str, bone_pairs: list[dict]) -> None:
    import json
    try:
        presets = json.loads(prefs.saved_presets)
    except Exception:
        presets = {}
    presets[preset_name] = bone_pairs
    prefs.saved_presets = json.dumps(presets)


def load_preset(prefs, preset_name: str) -> list[dict] | None:
    import json
    try:
        presets = json.loads(prefs.saved_presets)
        return presets.get(preset_name)
    except Exception:
        return None


def list_presets(prefs) -> list[str]:
    import json
    try:
        return list(json.loads(prefs.saved_presets).keys())
    except Exception:
        return []
