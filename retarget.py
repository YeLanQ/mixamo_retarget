import bpy
import mathutils
import re
from dataclasses import dataclass
from functools import cache
from typing import Optional
from mathutils import Matrix, Vector

CONSTRAINT_PREFIX = "MIXAMO_RETARGET_"


def _find_fcurve(action, data_path, index=0):
    """Find an FCurve without creating one. Works across Blender versions."""
    if hasattr(action, 'fcurves'):
        for fcu in action.fcurves:
            if fcu.data_path == data_path and fcu.array_index == index:
                return fcu
    return None


def _ensure_fcurve(action, armature_obj, data_path, index=0, group_name=''):
    """Get or create an FCurve using the API available in this Blender version."""
    if hasattr(action, 'fcurve_ensure_for_datablock'):
        fcu = action.fcurve_ensure_for_datablock(
            armature_obj, data_path, index=index, group_name=group_name)
        return fcu
    if hasattr(action, 'fcurves'):
        fcu = _find_fcurve(action, data_path, index)
        if fcu:
            return fcu
        fcu = action.fcurves.new(data_path, index=index)
        if group_name:
            fcu.group = action.groups.new(group_name)
        return fcu
    return None


# ============================================================================
# Bone Name Canonicalization (from VRM addon)
# ============================================================================

_BONE_NAME_LOWER_TO_UPPER_REGEX = (re.compile(r"([a-z])([A-Z])"), r"\1.\2")
_BONE_NAME_DIGIT_REGEX = (re.compile(r"(\d+)"), r".\1.")
_BONE_NAME_COMPONENT_SPLIT_REGEX = re.compile(r"[-._: (){}[\]<>]+")


@cache
def canonicalize_bone_name(name: str) -> str:
    s = "".join(
        chr(ord(c) - 0xFEE0) if 0x21 <= ord(c) - 0xFEE0 <= 0x7E else c
        for c in name
    )
    s = re.sub(*_BONE_NAME_LOWER_TO_UPPER_REGEX, s)
    s = s.lower()
    s = "".join(" " if c.isspace() else c for c in s)
    s = re.sub(*_BONE_NAME_DIGIT_REGEX, s).strip(".")
    parts = re.split(_BONE_NAME_COMPONENT_SPLIT_REGEX, s)
    for patterns, replacement in {
        ("l", "左", "left"): "left",
        ("r", "右", "right"): "right",
    }.items():
        parts = [replacement if p in patterns else p for p in parts]
    return ".".join(parts)


def names_match(a: str, b: str) -> bool:
    return canonicalize_bone_name(a) == canonicalize_bone_name(b)


# ============================================================================
# Human Bone Specification (from VRM specification)
# ============================================================================

HUMAN_BONE_NAMES = [
    "hips", "spine", "chest", "upperChest", "neck",
    "head", "leftEye", "rightEye", "jaw",
    "leftUpperLeg", "leftLowerLeg", "leftFoot", "leftToes",
    "rightUpperLeg", "rightLowerLeg", "rightFoot", "rightToes",
    "leftShoulder", "leftUpperArm", "leftLowerArm", "leftHand",
    "rightShoulder", "rightUpperArm", "rightLowerArm", "rightHand",
    "leftThumbMetacarpal", "leftThumbProximal", "leftThumbDistal",
    "leftIndexProximal", "leftIndexIntermediate", "leftIndexDistal",
    "leftMiddleProximal", "leftMiddleIntermediate", "leftMiddleDistal",
    "leftRingProximal", "leftRingIntermediate", "leftRingDistal",
    "leftLittleProximal", "leftLittleIntermediate", "leftLittleDistal",
    "rightThumbMetacarpal", "rightThumbProximal", "rightThumbDistal",
    "rightIndexProximal", "rightIndexIntermediate", "rightIndexDistal",
    "rightMiddleProximal", "rightMiddleIntermediate", "rightMiddleDistal",
    "rightRingProximal", "rightRingIntermediate", "rightRingDistal",
    "rightLittleProximal", "rightLittleIntermediate", "rightLittleDistal",
]

# Subset of finger/hand bone names (excluding palm/wrist)
FINGER_HUMAN_BONES = frozenset(HUMAN_BONE_NAMES[25:])

REQUIRED_BONE_NAMES = frozenset([
    "hips", "spine", "head",
    "leftUpperLeg", "leftLowerLeg", "leftFoot",
    "rightUpperLeg", "rightLowerLeg", "rightFoot",
    "leftUpperArm", "leftLowerArm", "leftHand",
    "rightUpperArm", "rightLowerArm", "rightHand",
])


# ============================================================================
# Naming Convention Mappings
# ============================================================================

def _inv_map(m: dict) -> dict:
    return {v: k for k, v in m.items()}


# Mixamo → human bone name
MIXAMO_TO_HUMAN_BONE = {
    "mixamorig:Hips": "hips",
    "mixamorig:Spine": "spine",
    "mixamorig:Spine1": "chest",
    "mixamorig:Spine2": "upperChest",
    "mixamorig:Neck": "neck",
    "mixamorig:Head": "head",
    "mixamorig:LeftShoulder": "leftShoulder",
    "mixamorig:LeftArm": "leftUpperArm",
    "mixamorig:LeftForeArm": "leftLowerArm",
    "mixamorig:LeftHand": "leftHand",
    "mixamorig:RightShoulder": "rightShoulder",
    "mixamorig:RightArm": "rightUpperArm",
    "mixamorig:RightForeArm": "rightLowerArm",
    "mixamorig:RightHand": "rightHand",
    "mixamorig:LeftUpLeg": "leftUpperLeg",
    "mixamorig:LeftLeg": "leftLowerLeg",
    "mixamorig:LeftFoot": "leftFoot",
    "mixamorig:LeftToeBase": "leftToes",
    "mixamorig:RightUpLeg": "rightUpperLeg",
    "mixamorig:RightLeg": "rightLowerLeg",
    "mixamorig:RightFoot": "rightFoot",
    "mixamorig:RightToeBase": "rightToes",
    "mixamorig:LeftHandThumb1": "leftThumbMetacarpal",
    "mixamorig:LeftHandThumb2": "leftThumbProximal",
    "mixamorig:LeftHandThumb3": "leftThumbDistal",
    "mixamorig:LeftHandIndex1": "leftIndexProximal",
    "mixamorig:LeftHandIndex2": "leftIndexIntermediate",
    "mixamorig:LeftHandIndex3": "leftIndexDistal",
    "mixamorig:LeftHandMiddle1": "leftMiddleProximal",
    "mixamorig:LeftHandMiddle2": "leftMiddleIntermediate",
    "mixamorig:LeftHandMiddle3": "leftMiddleDistal",
    "mixamorig:LeftHandRing1": "leftRingProximal",
    "mixamorig:LeftHandRing2": "leftRingIntermediate",
    "mixamorig:LeftHandRing3": "leftRingDistal",
    "mixamorig:LeftHandPinky1": "leftLittleProximal",
    "mixamorig:LeftHandPinky2": "leftLittleIntermediate",
    "mixamorig:LeftHandPinky3": "leftLittleDistal",
    "mixamorig:RightHandThumb1": "rightThumbMetacarpal",
    "mixamorig:RightHandThumb2": "rightThumbProximal",
    "mixamorig:RightHandThumb3": "rightThumbDistal",
    "mixamorig:RightHandIndex1": "rightIndexProximal",
    "mixamorig:RightHandIndex2": "rightIndexIntermediate",
    "mixamorig:RightHandIndex3": "rightIndexDistal",
    "mixamorig:RightHandMiddle1": "rightMiddleProximal",
    "mixamorig:RightHandMiddle2": "rightMiddleIntermediate",
    "mixamorig:RightHandMiddle3": "rightMiddleDistal",
    "mixamorig:RightHandRing1": "rightRingProximal",
    "mixamorig:RightHandRing2": "rightRingIntermediate",
    "mixamorig:RightHandRing3": "rightRingDistal",
    "mixamorig:RightHandPinky1": "rightLittleProximal",
    "mixamorig:RightHandPinky2": "rightLittleIntermediate",
    "mixamorig:RightHandPinky3": "rightLittleDistal",
}

# Mixamo → generic BVH standard names
MIXAMO_TO_STANDARD = {
    "mixamorig:Hips": "Hips",
    "mixamorig:Spine": "Spine",
    "mixamorig:Spine1": "Spine1",
    "mixamorig:Spine2": "Spine2",
    "mixamorig:Neck": "Neck",
    "mixamorig:Head": "Head",
    "mixamorig:LeftShoulder": "LeftShoulder",
    "mixamorig:LeftArm": "LeftArm",
    "mixamorig:LeftForeArm": "LeftForeArm",
    "mixamorig:LeftHand": "LeftHand",
    "mixamorig:RightShoulder": "RightShoulder",
    "mixamorig:RightArm": "RightArm",
    "mixamorig:RightForeArm": "RightForeArm",
    "mixamorig:RightHand": "RightHand",
    "mixamorig:LeftUpLeg": "LeftUpLeg",
    "mixamorig:LeftLeg": "LeftLeg",
    "mixamorig:LeftFoot": "LeftFoot",
    "mixamorig:LeftToeBase": "LeftToeBase",
    "mixamorig:RightUpLeg": "RightUpLeg",
    "mixamorig:RightLeg": "RightLeg",
    "mixamorig:RightFoot": "RightFoot",
    "mixamorig:RightToeBase": "RightToeBase",
}

# VRM addon naming → human bone name
VRM_TO_HUMAN_BONE = {
    "head": "head",
    "spine": "spine",
    "hips": "hips",
    "upper_arm.R": "rightUpperArm",
    "lower_arm.R": "rightLowerArm",
    "hand.R": "rightHand",
    "upper_arm.L": "leftUpperArm",
    "lower_arm.L": "leftLowerArm",
    "hand.L": "leftHand",
    "upper_leg.R": "rightUpperLeg",
    "lower_leg.R": "rightLowerLeg",
    "foot.R": "rightFoot",
    "upper_leg.L": "leftUpperLeg",
    "lower_leg.L": "leftLowerLeg",
    "foot.L": "leftFoot",
    "eye.R": "rightEye",
    "eye.L": "leftEye",
    "neck": "neck",
    "shoulder.L": "leftShoulder",
    "shoulder.R": "rightShoulder",
    "upper_chest": "upperChest",
    "chest": "chest",
    "toes.R": "rightToes",
    "toes.L": "leftToes",
}

# Biped convention → human bone name
BIPED_TO_HUMAN_BONE = {
    "Pelvis": "hips",
    "Spine": "spine",
    "Spine2": "chest",
    "Neck": "neck",
    "Head": "head",
    "Clavicle": "leftShoulder",
    "UpperArm": "leftUpperArm",
    "Forearm": "leftLowerArm",
    "Hand": "leftHand",
    "Thigh": "leftUpperLeg",
    "Calf": "leftLowerLeg",
    "Foot": "leftFoot",
    "Toe0": "leftToes",
}

# UE4 convention → human bone name
UE4_TO_HUMAN_BONE: dict = {}  # populated dynamically

# All naming conventions as (name, {bone_name: human_bone_name})
NAMED_CONVENTIONS = [
    ("Mixamo", MIXAMO_TO_HUMAN_BONE),
    ("Mixamo→Standard", MIXAMO_TO_STANDARD),
    ("VRM Add-on", VRM_TO_HUMAN_BONE),
]

# ============================================================================
# Normalized armature analysis
# ============================================================================

@dataclass(frozen=True)
class NormalizedBone:
    name: str
    x: float
    y: float
    z: float
    children: tuple["NormalizedBone", ...]
    parent: Optional["NormalizedBone"] = None

    def recursive_len(self) -> int:
        return 1 + sum(c.recursive_len() for c in self.children)

    def all_descendants(self) -> list["NormalizedBone"]:
        result: list[NormalizedBone] = []
        for c in self.children:
            result.append(c)
            result.extend(c.all_descendants())
        return result


def analyze_armature(armature: bpy.types.Object) -> list[NormalizedBone]:
    arm_data = armature.data
    bones = arm_data.bones
    max_x = max((abs((armature.matrix_world @ b.matrix_local).translation.x) for b in bones), default=1)
    max_y = max((abs((armature.matrix_world @ b.matrix_local).translation.y) for b in bones), default=1)
    max_z = max((abs((armature.matrix_world @ b.matrix_local).translation.z) for b in bones), default=1)
    if max_x < 0.001: max_x = 1
    if max_y < 0.001: max_y = 1
    if max_z < 0.001: max_z = 1

    import math
    def _build(bone, parent=None):
        pos = (armature.matrix_world @ bone.matrix_local).translation
        nx = math.copysign(math.sqrt(abs(pos.x) / max_x), pos.x) if max_x > 0 else 0
        ny = math.copysign(math.sqrt(abs(pos.y) / max_y), pos.y) if max_y > 0 else 0
        nz = math.copysign(math.sqrt(abs(pos.z) / max_z), pos.z) if max_z > 0 else 0
        nb = NormalizedBone(
            name=bone.name, x=nx, y=ny, z=nz,
            children=tuple(_build(c, bone) for c in bone.children),
            parent=parent,
        )
        return nb

    roots = [_build(b) for b in bones if not b.parent]
    return roots


# ============================================================================
# Multi-pass bone matching
# ============================================================================

@dataclass
class MatchedPair:
    bone_name: str
    human_bone: str
    is_required: bool
    score: int = 0


def _normalize(name: str) -> str:
    name = name.lower()
    if ":" in name:
        name = name.split(":")[-1]
    return re.sub(r"[^a-z0-9_]", "", name)


def is_mixamo_bone(name: str) -> bool:
    return "mixamorig" in name.lower()


def _match_by_name(
    bone_name: str,
    mapping: dict[str, str],
) -> str | None:
    canon = canonicalize_bone_name(bone_name)
    for mapped_name, human_bone in mapping.items():
        if names_match(mapped_name, bone_name):
            return human_bone
    return None


def _try_convention(
    bone_name: str,
    convention: dict[str, str],
) -> str | None:
    for key, human_bone_name in convention.items():
        if names_match(key, bone_name):
            return human_bone_name
    return None


def _match_by_position(
    bone: NormalizedBone,
    armature: bpy.types.Object,
) -> str | None:
    """Try to guess human bone from position in normalized space.
    Y-axis is up, Z is forward (Blender convention).
    """
    x, y, z = bone.x, bone.y, bone.z

    # Hips: root, around origin, lowest central bone
    if bone.parent is None and y < 0.1:
        desc = bone.all_descendants()
        has_legs = sum(1 for d in desc if d.y < -0.3)
        if has_legs >= 2:
            return "hips"

    # Spine: positive Y above hips
    if bone.parent and y > 0.1 and abs(x) < 0.15 and z > -0.1:
        return "spine"

    # Chest: above spine, slight Y
    if bone.parent and y > 0.3 and abs(x) < 0.2:
        return "chest"

    # Neck: high positive Y, central
    if bone.parent and y > 0.7 and abs(x) < 0.1:
        return "neck"

    # Head: topmost central
    if bone.parent and y > 0.85 and abs(x) < 0.15:
        return "head"

    # Left arm (negative X)
    if x < -0.3:
        if y > -0.1:
            pname = bone.parent.name.lower() if bone.parent else ""
            if any(k in pname for k in ("shoulder", "clavicle", "chest", "spine")):
                return "leftUpperArm"
            if "elbow" in bone.name.lower() or "forearm" in bone.name.lower():
                return "leftLowerArm"
            if "hand" in bone.name.lower() or "wrist" in bone.name.lower():
                return "leftHand"
            return "leftUpperArm"

    # Right arm (positive X)
    if x > 0.3:
        if y > -0.1:
            pname = bone.parent.name.lower() if bone.parent else ""
            if any(k in pname for k in ("shoulder", "clavicle", "chest", "spine")):
                return "rightUpperArm"
            if "elbow" in bone.name.lower() or "forearm" in bone.name.lower():
                return "rightLowerArm"
            if "hand" in bone.name.lower() or "wrist" in bone.name.lower():
                return "rightHand"
            return "rightUpperArm"

    # Left leg (negative X, low Y)
    if x < -0.1 and y < -0.2:
        if "shin" in bone.name.lower() or "calf" in bone.name.lower() or "leg" in bone.name.lower():
            return "leftLowerLeg"
        if "foot" in bone.name.lower() or "ankle" in bone.name.lower():
            return "leftFoot"
        if "toe" in bone.name.lower():
            return "leftToes"
        return "leftUpperLeg"

    # Right leg (positive X, low Y)
    if x > 0.1 and y < -0.2:
        if "shin" in bone.name.lower() or "calf" in bone.name.lower() or "leg" in bone.name.lower():
            return "rightLowerLeg"
        if "foot" in bone.name.lower() or "ankle" in bone.name.lower():
            return "rightFoot"
        if "toe" in bone.name.lower():
            return "rightToes"
        return "rightUpperLeg"

    return None


# ============================================================================
# Main skeleton detection
# ============================================================================

def detect_skeleton(
    armature_obj: bpy.types.Object,
) -> list[tuple[str, str]]:
    """Detect human skeleton from an armature object.
    Returns list of (actual_bone_name, human_bone_name).
    """
    result: list[tuple[str, str]] = []
    used_human_bones: set[str] = set()
    used_bones: set[str] = set()
    bones = armature_obj.data.bones
    norm_roots = analyze_armature(armature_obj)
    norm_map = {nb.name: nb for root in norm_roots for nb in [root] + root.all_descendants()}

    # Pass 1: Try naming conventions
    for bone in bones:
        for convention_name, convention in NAMED_CONVENTIONS:
            human_bone = _try_convention(bone.name, convention)
            if human_bone and human_bone not in used_human_bones and bone.name not in used_bones:
                result.append((bone.name, human_bone))
                used_human_bones.add(human_bone)
                used_bones.add(bone.name)
                break

    # Pass 2: Try matching parent bone names (e.g., "Hips" → "hips")
    for bone in bones:
        if bone.name in used_bones:
            continue
        norm = _normalize(bone.name)
        for hb in HUMAN_BONE_NAMES:
            if hb not in used_human_bones and _normalize(hb) == norm:
                result.append((bone.name, hb))
                used_human_bones.add(hb)
                used_bones.add(bone.name)
                break

    # Pass 3: Try position-based detection for remaining bones
    for root in norm_roots:
        all_bones_norm = [root] + root.all_descendants()
        for nb in all_bones_norm:
            if nb.name in used_bones:
                continue
            hb = _match_by_position(nb, armature_obj)
            if hb and hb not in used_human_bones:
                result.append((nb.name, hb))
                used_human_bones.add(hb)
                used_bones.add(nb.name)

    return result


# ============================================================================
# Bone mapping between source and target armatures
# ============================================================================

def _default_mode_for_human_bone(human_bone_name: str) -> str:
    """Determine the retarget mode for a human bone.
    Hips uses COPY_TRANSFORMS (world-space loc + rot + scale for root motion).
    Finger bones use LOCAL_ROTATION (local-space COPY_ROTATION,
    not CHILD_OF — avoids flying when source/target joint pivots differ).
    All other bones use COPY_ROTATION.
    """
    if human_bone_name == "hips":
        return "COPY_TRANSFORMS"
    if human_bone_name in FINGER_HUMAN_BONES:
        return "LOCAL_ROTATION"
    return "COPY_ROTATION"


def build_mapping_from_human_bones(
    source_arm: bpy.types.Object,
    target_arm: bpy.types.Object,
) -> list[tuple[str, str, str]]:
    """Build bone mapping by detecting human skeleton on both armatures
    and matching them via the human bone specification.
    Returns list of (source_bone_name, target_bone_name, retarget_mode).
    """
    src_detected = detect_skeleton(source_arm)
    tgt_detected = detect_skeleton(target_arm)

    src_by_human = {hb: bn for bn, hb in src_detected}
    tgt_by_human = {hb: bn for bn, hb in tgt_detected}

    result = []
    used_tgt = set()
    for hb in HUMAN_BONE_NAMES:
        src_bn = src_by_human.get(hb)
        tgt_bn = tgt_by_human.get(hb)
        if src_bn and tgt_bn and tgt_bn not in used_tgt:
            result.append((src_bn, tgt_bn, _default_mode_for_human_bone(hb)))
            used_tgt.add(tgt_bn)

    return result


# ============================================================================
# (Legacy) auto_build_mapping — using MIXAMO_BONE_HINTS for backward compat
# ============================================================================

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


def _default_mode_for_hint(hint_name: str) -> str:
    """Determine retarget mode from a MIXAMO_BONE_HINTS name.
    Hips → COPY_TRANSFORMS (world-space loc + rot + scale).
    Finger bones (LeftHand*/RightHand* excluding hand itself) → LOCAL_ROTATION.
    Others → COPY_ROTATION.
    """
    if hint_name == "Hips":
        return "COPY_TRANSFORMS"
    for prefix in ("LeftHand", "RightHand"):
        if hint_name.startswith(prefix) and hint_name != prefix:
            return "LOCAL_ROTATION"
    return "COPY_ROTATION"


def auto_build_mapping(source_arm: bpy.types.Object,
                       target_arm: bpy.types.Object) -> list[tuple[str, str, str]]:
    src_name_list = list(source_arm.data.bones.keys())
    tgt_name_list = list(target_arm.data.bones.keys())
    src_norm_map = {b.name: _normalize(b.name) for b in source_arm.data.bones}
    tgt_norm_map = {b.name: _normalize(b.name) for b in target_arm.data.bones}

    def _find_bone(name: str, norm_map: dict, name_list: list) -> str | None:
        if name in norm_map:
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

        result.append((src_matched, tgt_matched, _default_mode_for_hint(src_hint)))
        mapped_src_names.add(src_matched)
        mapped_tgt_names.add(tgt_matched)

    return result


# ============================================================================
# Constraint-based retargeting
# ============================================================================

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
            _add_copy_transforms(tgt_pbone, source_arm, target_arm, src_name, is_root)
        elif mode == "LOCAL_ROTATION":
            _add_copy_rotation(tgt_pbone, source_arm, src_name, is_root, local_space=True)
        elif mode == "CHILD_OF":
            _add_child_of(tgt_pbone, source_arm, target_arm, src_name, is_root)
        elif mode == "CHILD_OF_ROTATION":
            _add_child_of(tgt_pbone, source_arm, target_arm, src_name, is_root, rotation_only=True)
        else:
            warnings.append(f"Unknown mode '{mode}' for '{tgt_name}' — using Copy Rotation.")
            _add_copy_rotation(tgt_pbone, source_arm, src_name, is_root)

        applied += 1

    return applied, warnings


def _add_copy_rotation(pbone, source_arm, src_name: str,
                       is_root: bool = False,
                       local_space: bool = False) -> None:
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
    if local_space:
        rot.owner_space = 'LOCAL'
        rot.target_space = 'LOCAL'
    else:
        rot.owner_space = 'WORLD'
        rot.target_space = 'WORLD'


def _add_copy_transforms(pbone, source_arm, target_arm, src_name: str, is_root: bool = False) -> None:
    # WORLD-space COPY_ROTATION + rest-pose-offset COPY_LOCATION for root.
    #
    # Why not COPY_TRANSFORMS (LOCAL)?
    #   LOCAL copies relative to parent rest pose. Different rest poses produce
    #   wildly different world transforms → bones "fly away".
    #
    # Why not CHILD_OF?
    #   CHILD_OF makes the source bone the virtual parent, overriding the
    #   target's real hierarchy. The target detaches from its own parent chain.
    #
    # WORLD rotation: absolute, immune to rest-pose differences.
    #
    # For root: TRANSFORM constraint maps source world head to target
    #   world head with a rest-pose offset.  This replaces COPY_LOCATION
    #   + use_offset because Blender computes the use_offset offset
    #   lazily at depsgraph evaluation time — by then the pose may have
    #   been restored, giving a wrong offset.  TRANSFORM embeds the
    #   offset directly in the from→to parameters, so it never depends
    #   on evaluation order.
    if is_root:
        src_rest_world = source_arm.matrix_world @ source_arm.data.bones[src_name].matrix_local
        tgt_rest_world = target_arm.matrix_world @ pbone.bone.matrix_local
        tc = pbone.constraints.new("TRANSFORM")
        tc.name = CONSTRAINT_PREFIX + "Location"
        tc.target = source_arm
        tc.subtarget = src_name
        tc.map_from = 'LOCATION'
        tc.map_to = 'LOCATION'
        tc.target_space = 'WORLD'
        tc.owner_space = 'WORLD'
        tc.use_motion_extrapolate = True
        for axis in ('x', 'y', 'z'):
            s = getattr(src_rest_world.translation, axis)
            t = getattr(tgt_rest_world.translation, axis)
            setattr(tc, f'from_min_{axis}', s)
            setattr(tc, f'from_max_{axis}', s + 1.0)
            setattr(tc, f'to_min_{axis}', t)
            setattr(tc, f'to_max_{axis}', t + 1.0)

    rot = pbone.constraints.new("COPY_ROTATION")
    rot.name = CONSTRAINT_PREFIX + "Rotation"
    rot.target = source_arm
    rot.subtarget = src_name
    rot.mix_mode = 'REPLACE'
    rot.owner_space = 'WORLD'
    rot.target_space = 'WORLD'


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
        tgt_current_world = target_arm.matrix_world @ pbone.bone.matrix_local
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
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')

        # Ensure action exists
        if target_arm.animation_data is None:
            target_arm.animation_data_create()
        action = target_arm.animation_data.action
        if action is None:
            action = bpy.data.actions.new(name=f"{target_arm.name}_Action")
            target_arm.animation_data.action = action

        bones = target_arm.pose.bones

        for frame in range(frame_start, frame_end + 1):
            bpy.context.scene.frame_set(frame)
            for bone in bones:
                prefix = f'pose.bones["{bone.name}"].'
                for idx in range(3):
                    fcu = _ensure_fcurve(action, target_arm, prefix + 'location', index=idx, group_name=bone.name)
                    fcu.keyframe_points.insert(frame, bone.location[idx])
                    fcu.update()
                for idx in range(4):
                    fcu = _ensure_fcurve(action, target_arm, prefix + 'rotation_quaternion', index=idx, group_name=bone.name)
                    fcu.keyframe_points.insert(frame, bone.rotation_quaternion[idx])
                    fcu.update()
                for idx in range(3):
                    fcu = _ensure_fcurve(action, target_arm, prefix + 'scale', index=idx, group_name=bone.name)
                    fcu.keyframe_points.insert(frame, bone.scale[idx])
                    fcu.update()

        # Remove constraints
        for bone in bones:
            for c in list(bone.constraints):
                bone.constraints.remove(c)

        bpy.ops.object.mode_set(mode='OBJECT')
        return True

    except Exception as e:
        print(f"[Mixamo Retarget] Bake error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# Bone Animation Interpolation (补帧)
# ============================================================================


def get_bone_fcurves(armature_obj, action, bone_name):
    """Get all F-curves for a specific bone (read-only, no FCurves created).
    Returns (location_fcurves[3], rotation_fcurves[4], scale_fcurves[3]).
    Each entry is the FCurve or None.
    """
    loc = [None, None, None]
    rot = [None, None, None, None]
    scale = [None, None, None]
    prefix = f'pose.bones["{bone_name}"].'

    for idx in range(3):
        try:
            fcu = _find_fcurve(action, prefix + 'location', index=idx)
            if fcu and fcu.keyframe_points:
                loc[idx] = fcu
        except (AttributeError, TypeError):
            pass
    for idx in range(4):
        try:
            fcu = _find_fcurve(action, prefix + 'rotation_quaternion', index=idx)
            if fcu and fcu.keyframe_points:
                rot[idx] = fcu
        except (AttributeError, TypeError):
            pass
    for idx in range(3):
        try:
            fcu = _find_fcurve(action, prefix + 'scale', index=idx)
            if fcu and fcu.keyframe_points:
                scale[idx] = fcu
        except (AttributeError, TypeError):
            pass
    return loc, rot, scale


def bone_has_fcurves(armature_obj, action, bone_name):
    """Check if a bone has any F-curves with keyframes in the given action."""
    if not action:
        return False
    loc, rot, scale = get_bone_fcurves(armature_obj, action, bone_name)
    return any(fc is not None for fc in loc + rot + scale)


def _mirror_bone_name(name):
    """Try to find the mirror bone name (left <-> right)."""
    import re
    patterns = [
        (re.compile(r"^(left|Left|LEFT)(.*)$"), lambda m: ("Right" if m.group(1)[0].isupper() else "right") + m.group(2)),
        (re.compile(r"^(right|Right|RIGHT)(.*)$"), lambda m: ("Left" if m.group(1)[0].isupper() else "left") + m.group(2)),
        (re.compile(r"^(l|L)_(.*)$"), lambda m: ("R_" if m.group(1).isupper() else "r_") + m.group(2)),
        (re.compile(r"^(r|R)_(.*)$"), lambda m: ("L_" if m.group(1).isupper() else "l_") + m.group(2)),
        (re.compile(r"(.*)(Left|left)(.*)$"), lambda m: m.group(1) + ("Right" if m.group(2)[0].isupper() else "right") + m.group(3)),
        (re.compile(r"(.*)(Right|right)(.*)$"), lambda m: m.group(1) + ("Left" if m.group(2)[0].isupper() else "left") + m.group(3)),
    ]
    for pattern, repl in patterns:
        m = pattern.match(name)
        if m:
            result = repl(m)
            if result != name:
                return result
    return None


def _ensure_action(armature_obj):
    """Ensure the armature has animation data with an action."""
    if armature_obj.animation_data is None:
        armature_obj.animation_data_create()
    if armature_obj.animation_data.action is None:
        existing = next((a for a in bpy.data.actions if not a.users), None)
        action = existing or bpy.data.actions.new(name=f"{armature_obj.name}_Action")
        armature_obj.animation_data.action = action
    return armature_obj.animation_data.action


def _get_bone_keyframe_frames(action, bone_name):
    """Get all frames that have keyframes for this bone across all channels (read-only)."""
    frames = set()
    if not action:
        return []
    props = ['location', 'rotation_quaternion', 'scale']
    dims = [3, 4, 3]
    prefix = f'pose.bones["{bone_name}"].'
    for prop, dim in zip(props, dims):
        for idx in range(dim):
            fcu = _find_fcurve(action, prefix + prop, index=idx)
            if fcu:
                for kp in fcu.keyframe_points:
                    frames.add(int(kp.co.x))
    return sorted(frames)


def _get_rest_local(armature_obj, bone_name):
    """Get the rest-pose local transform for a bone relative to its parent (parent-TAIL to child-HEAD)."""
    bone_edit = armature_obj.data.bones[bone_name]
    if bone_edit.parent:
        parent_rest = bone_edit.parent.matrix_local
        bone_rest = bone_edit.matrix_local
        mat = parent_rest.inverted() @ bone_rest
        mat.translation -= Vector((0, bone_edit.parent.length, 0))
        return mat
    else:
        return bone_edit.matrix_local


def _keyframe_bone(armature_obj, bone_name, frame):
    """Insert location/rotation/scale keyframes for a bone at given frame."""
    bone = armature_obj.pose.bones[bone_name]
    bone.keyframe_insert(data_path='location', frame=frame, group=bone_name)
    bone.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=bone_name)
    bone.keyframe_insert(data_path='scale', frame=frame, group=bone_name)


def fill_missing_bone_animation(armature_obj, bone_name, frame_start, frame_end, step=1):
    """Create identity-matrix keyframes for a bone with no F-curves.
    The bone follows its parent chain at the rest-pose offset (handled by
    Blender's internal armature evaluation via bone.matrix_local).
    All keyframes are identity because the bone has no local animation.
    Returns number of keyframes added.
    """
    action = _ensure_action(armature_obj)
    bone = armature_obj.pose.bones[bone_name]

    if bone_has_fcurves(armature_obj, action, bone_name):
        return 0

    keyframes_added = 0
    for frame in range(frame_start, frame_end + 1, step):
        bpy.context.scene.frame_set(frame)
        bone.location = (0.0, 0.0, 0.0)
        bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)
        _keyframe_bone(armature_obj, bone_name, frame)
        keyframes_added += 1

    return keyframes_added


def derive_from_mirror_bone(armature_obj, bone_name, frame_start, frame_end, step=1):
    """Derive animation for a bone from its mirror counterpart (left <-> right).
    Returns (keyframes_added, error_message_or_None).
    """
    mirror = _mirror_bone_name(bone_name)
    if not mirror or mirror not in armature_obj.pose.bones:
        return 0, "No mirror bone found"

    action = _ensure_action(armature_obj)

    if not bone_has_fcurves(armature_obj, action, mirror):
        return 0, f"Mirror bone '{mirror}' has no F-curves"

    keyframes_added = 0
    for frame in range(frame_start, frame_end + 1, step):
        bpy.context.scene.frame_set(frame)

        mirror_bone = armature_obj.pose.bones[mirror]
        bone = armature_obj.pose.bones[bone_name]

        loc = mirror_bone.location.copy()
        rot = mirror_bone.rotation_quaternion.copy()
        scl = mirror_bone.scale.copy()

        loc.x = -loc.x
        rot.x = -rot.x
        rot.w = -rot.w

        bone.location = loc
        bone.rotation_quaternion = rot
        bone.scale = scl

        bone.keyframe_insert(data_path='location', frame=frame, group=bone_name)
        bone.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=bone_name)
        bone.keyframe_insert(data_path='scale', frame=frame, group=bone_name)
        keyframes_added += 1

    return keyframes_added, None


def fill_keyframe_gaps(armature_obj, bone_name, frame_start, frame_end, step=1):
    """Ensure every Nth frame has a keyframe by sampling current pose values.
    Returns number of new keyframes added.
    """
    action = _ensure_action(armature_obj)
    bone = armature_obj.pose.bones[bone_name]

    if not bone_has_fcurves(armature_obj, action, bone_name):
        return 0

    existing_frames = _get_bone_keyframe_frames(action, bone_name)
    keyframes_added = 0

    for frame in range(frame_start, frame_end + 1, step):
        if frame in existing_frames:
            continue
        bpy.context.scene.frame_set(frame)
        bone.keyframe_insert(data_path='location', frame=frame, group=bone_name)
        bone.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=bone_name)
        bone.keyframe_insert(data_path='scale', frame=frame, group=bone_name)
        keyframes_added += 1

    return keyframes_added


def smooth_bone_fcurves(armature_obj, bone_name, passes=3):
    """Smooth F-curves for a bone using moving average filter.
    Each pass replaces each keyframe's value with the average of itself and its neighbors.
    """
    action = None
    if armature_obj.animation_data:
        action = armature_obj.animation_data.action
    if not action:
        return

    data_paths = [('location', 3), ('rotation_quaternion', 4), ('scale', 3)]
    prefix = f'pose.bones["{bone_name}"].'

    for prop_name, dim in data_paths:
        for idx in range(dim):
            fcurve = _find_fcurve(action, prefix + prop_name, index=idx)
            if fcurve is None or len(fcurve.keyframe_points) < 3:
                continue

            for _ in range(passes):
                points = [(kp.co.x, kp.co.y) for kp in fcurve.keyframe_points]
                n = len(points)
                for j in range(1, n - 1):
                    smoothed = (points[j - 1][1] + points[j][1] + points[j + 1][1]) / 3.0
                    fcurve.keyframe_points[j].co.y = smoothed
                    fcurve.keyframe_points[j].handle_left.y = smoothed
                    fcurve.keyframe_points[j].handle_right.y = smoothed
                if n >= 2:
                    smoothed_first = (points[0][1] + points[1][1]) / 2.0
                    fcurve.keyframe_points[0].co.y = smoothed_first
                    fcurve.keyframe_points[0].handle_left.y = smoothed_first
                    fcurve.keyframe_points[0].handle_right.y = smoothed_first
                    smoothed_last = (points[-2][1] + points[-1][1]) / 2.0
                    fcurve.keyframe_points[-1].co.y = smoothed_last
                    fcurve.keyframe_points[-1].handle_left.y = smoothed_last
                    fcurve.keyframe_points[-1].handle_right.y = smoothed_last

            fcurve.update()


def _clear_bone_fcurves(armature_obj, bone_name):
    """Remove all keyframes for a given bone from the armature's action."""
    action = armature_obj.animation_data.action if armature_obj.animation_data else None
    if not action:
        return
    props = ['location', 'rotation_quaternion', 'scale']
    dims = [3, 4, 3]
    prefix = f'pose.bones["{bone_name}"].'
    for prop, dim in zip(props, dims):
        for idx in range(dim):
            fcu = _find_fcurve(action, prefix + prop, index=idx)
            if fcu and fcu.keyframe_points:
                fcu.keyframe_points.clear()


def _find_related_bones(armature_obj, bone_name, use_mirror=True):
    """Find all bones related to the given bone, ordered by prediction priority.
    Returns list of (relationship_type, bone_name).
    Priority: mirror > parent > grandparent(chain) > sibling > child.
    """
    data_bones = armature_obj.data.bones
    bone = data_bones.get(bone_name)
    if not bone:
        return []

    related = []
    seen = {bone_name}

    if use_mirror:
        mirror = _mirror_bone_name(bone_name)
        if mirror and mirror in data_bones:
            related.append(('mirror', mirror))
            seen.add(mirror)

    if bone.parent and bone.parent.name not in seen:
        related.append(('parent', bone.parent.name))
        seen.add(bone.parent.name)

    ancestor = bone.parent.parent if bone.parent else None
    while ancestor and ancestor.name not in seen:
        related.append(('chain_ancestor', ancestor.name))
        seen.add(ancestor.name)
        ancestor = ancestor.parent

    if bone.parent:
        for sibling in bone.parent.children:
            if sibling.name not in seen:
                related.append(('sibling', sibling.name))
                seen.add(sibling.name)

    for child in bone.children:
        if child.name not in seen:
            related.append(('child', child.name))
            seen.add(child.name)

    return related


def _predict_bone_from_source(armature_obj, bone_name, source_name, rel_type, frame_start, frame_end, step=1):
    """Derive bone animation from a related source bone using the appropriate transform.
    Returns (keyframes_added, error_message_or_None).
    """
    bone = armature_obj.pose.bones.get(bone_name)
    source = armature_obj.pose.bones.get(source_name)
    if not bone or not source:
        return 0, f"Bone or source not found"

    _ensure_action(armature_obj)
    action = armature_obj.animation_data.action

    source_edit = armature_obj.data.bones[source_name]

    if rel_type == 'mirror':
        if not bone_has_fcurves(armature_obj, action, source_name):
            return 0, f"Mirror source '{source_name}' has no F-curves"
        _clear_bone_fcurves(armature_obj, bone_name)
        keyframes_added = 0
        for frame in range(frame_start, frame_end + 1, step):
            bpy.context.scene.frame_set(frame)
            loc = source.location.copy()
            rot = source.rotation_quaternion.copy()
            scl = source.scale.copy()
            loc.x = -loc.x
            rot.x = -rot.x
            rot.w = -rot.w
            bone.location = loc
            bone.rotation_quaternion = rot
            bone.scale = scl
            _keyframe_bone(armature_obj, bone_name, frame)
            keyframes_added += 1
        return keyframes_added, None

    elif rel_type == 'parent':
        if not bone_has_fcurves(armature_obj, action, source_name):
            return 0, f"Parent source '{source_name}' has no F-curves"
        _clear_bone_fcurves(armature_obj, bone_name)
        # Child follows parent at rest — identity matrix_basis.
        # Blender's armature evaluation (bone.matrix = parent.matrix @
        # bone.matrix_local @ bone.matrix_basis) handles the rest-pose
        # offset internally; we don't write it into the animation.
        keyframes_added = 0
        for frame in range(frame_start, frame_end + 1, step):
            bpy.context.scene.frame_set(frame)
            bone.location = (0.0, 0.0, 0.0)
            bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            bone.scale = (1.0, 1.0, 1.0)
            _keyframe_bone(armature_obj, bone_name, frame)
            keyframes_added += 1
        return keyframes_added, None

    elif rel_type == 'chain_ancestor':
        if not bone_has_fcurves(armature_obj, action, source_name):
            return 0, f"Ancestor source '{source_name}' has no F-curves"
        _clear_bone_fcurves(armature_obj, bone_name)
        # The chain between ancestor and descendant has intermediate bones
        # whose animation is unknown — the safest prediction is identity
        # (descendant follows its direct parent at rest).
        keyframes_added = 0
        for frame in range(frame_start, frame_end + 1, step):
            bpy.context.scene.frame_set(frame)
            bone.location = (0.0, 0.0, 0.0)
            bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            bone.scale = (1.0, 1.0, 1.0)
            _keyframe_bone(armature_obj, bone_name, frame)
            keyframes_added += 1
        return keyframes_added, None

    elif rel_type in ('sibling', 'child'):
        if not bone_has_fcurves(armature_obj, action, source_name):
            return 0, f"Source '{source_name}' has no F-curves"
        _clear_bone_fcurves(armature_obj, bone_name)
        parent_edit = armature_obj.data.bones[bone_name].parent

        if rel_type == 'child':
            # Derive parent from child:
            # parent_pose = child.matrix @ child.matrix_basis^-1 @ child_rest_local^-1
            # child_rest_local = rest offset from parent tail to child head
            child_rest_local = _get_rest_local(armature_obj, source_name)
            child_rest_inv = child_rest_local.inverted()
            keyframes_added = 0
            for frame in range(frame_start, frame_end + 1, step):
                bpy.context.scene.frame_set(frame)
                desired = source.matrix @ source.matrix_basis.inverted() @ child_rest_inv
                if bone.parent:
                    desired = bone.parent.matrix.inverted() @ desired
                loc, rot, scl = desired.decompose()
                bone.location = loc
                bone.rotation_quaternion = rot
                bone.scale = scl
                _keyframe_bone(armature_obj, bone_name, frame)
                keyframes_added += 1
            return keyframes_added, None

        else:  # sibling — follow shared parent at rest
            # Target bone has no direct animation; it follows its parent at the
            # rest-pose offset (Blender handles this via bone.matrix_local).
            # sibling case only runs when direct parent has no FCurves,
            # so there's nothing meaningful to derive.
            keyframes_added = 0
            for frame in range(frame_start, frame_end + 1, step):
                bpy.context.scene.frame_set(frame)
                bone.location = (0.0, 0.0, 0.0)
                bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
                bone.scale = (1.0, 1.0, 1.0)
                _keyframe_bone(armature_obj, bone_name, frame)
                keyframes_added += 1
            return keyframes_added, None

    return 0, f"Unknown relationship type '{rel_type}'"


def predict_bone_from_related(armature_obj, bone_name, frame_start, frame_end, step=1, use_mirror=True):
    """Predict a bone's animation by scanning all related bones for animation data.
    Priority order: mirror > parent > chain ancestor > sibling > child.
    The first related bone that has F-curves is used for derivation.

    Returns (keyframes_added, source_name, relationship_type, error_or_None).
    """
    related = _find_related_bones(armature_obj, bone_name, use_mirror)
    if not related:
        return 0, None, None, "No related bones found"

    for rel_type, rel_name in related:
        n, err = _predict_bone_from_source(
            armature_obj, bone_name, rel_name, rel_type,
            frame_start, frame_end, step,
        )
        if err is None and n > 0:
            return n, rel_name, rel_type, None

    return 0, None, None, "No related bones with animation"





def temporal_predict_frames(armature_obj, bone_name, frame_start, frame_end, step=1):
    """Fill missing frames using temporal prediction from existing keyframes.
    Uses cubic (bezier) interpolation between surrounding keyframes.
    Only fills frames between existing keyframes (does not extrapolate).

    Returns number of keyframes added.
    """
    action = armature_obj.animation_data.action if armature_obj.animation_data else None
    if not action:
        return 0

    bone = armature_obj.pose.bones[bone_name]
    if not bone_has_fcurves(armature_obj, action, bone_name):
        return 0

    existing = _get_bone_keyframe_frames(action, bone_name)
    if len(existing) < 2:
        return 0

    keyframes_added = 0
    for frame in range(frame_start, frame_end + 1, step):
        if frame in existing:
            continue
        if frame < existing[0] or frame > existing[-1]:
            continue

        bpy.context.scene.frame_set(frame)

        bone.keyframe_insert(data_path='location', frame=frame, group=bone_name)
        bone.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=bone_name)
        bone.keyframe_insert(data_path='scale', frame=frame, group=bone_name)
        keyframes_added += 1

    return keyframes_added


def interpolate_armature_animation(
    armature_obj: bpy.types.Object,
    frame_start: int,
    frame_end: int,
    fill_missing: bool = True,
    fill_gaps: bool = True,
    smooth: bool = True,
    smoothing_passes: int = 3,
    step: int = 1,
    use_mirror: bool = True,
    predict: bool = False,
    progress_callback: callable = None,
    bone_names: list[str] = None,
) -> dict:
    """Comprehensive bone animation in-betweening (补帧) for an armature.

    Pipeline per bone:
      1. No F-curves → try mirror → try related prediction → rest-pose fallback (if fill_missing)
      2. Fill gaps at regular intervals (if fill_gaps)
      3. Smooth F-curves (if smooth)

    progress_callback(steps_done, total_steps, current_bone_name) is called
    after each bone is processed.

    If bone_names is given, only process those bones.

    Returns dict of per-bone stats: {bone_name: {'keyframes_added': int, 'actions': [str]}}
    """
    if not armature_obj or armature_obj.type != 'ARMATURE':
        return {}

    original_frame = bpy.context.scene.frame_current
    bpy.context.view_layer.objects.active = armature_obj

    candidates = list(armature_obj.pose.bones)
    if bone_names is not None:
        name_set = set(bone_names)
        candidates = [b for b in candidates if b.name in name_set]
    total = len(candidates)
    stats = {}

    for i, bone in enumerate(candidates):
        bone_name = bone.name
        bone_stats = {'keyframes_added': 0, 'actions': []}

        # Phase 1: Ensure bone has base keyframes
        _ensure_action(armature_obj)
        action = armature_obj.animation_data.action
        has_fcurves = bone_has_fcurves(armature_obj, action, bone_name)

        if not has_fcurves and fill_missing:
            filled = False
            # 1a: Derive from mirror
            if use_mirror:
                n, err = derive_from_mirror_bone(
                    armature_obj, bone_name, frame_start, frame_end, step
                )
                if err is None and n > 0:
                    bone_stats['keyframes_added'] += n
                    bone_stats['actions'].append("mirror")
                    filled = True
                    has_fcurves = True

            # 1b: Predict from related bones (parent/chain/sibling/child)
            if not filled and predict:
                n, src_name, rel_type, err = predict_bone_from_related(
                    armature_obj, bone_name, frame_start, frame_end, step,
                    use_mirror=False,
                )
                if err is None and n > 0:
                    bone_stats['keyframes_added'] += n
                    bone_stats['actions'].append(f"predict:{rel_type}")
                    filled = True
                    has_fcurves = True

            # 1c: Fallback — rest-pose keyframes
            if not filled:
                n = fill_missing_bone_animation(
                    armature_obj, bone_name, frame_start, frame_end, step
                )
                if n > 0:
                    bone_stats['keyframes_added'] += n
                    bone_stats['actions'].append("rest_pose")
                    has_fcurves = True

        # Phase 2: Fill gaps at regular intervals
        if fill_gaps and has_fcurves:
            n = fill_keyframe_gaps(
                armature_obj, bone_name, frame_start, frame_end, step
            )
            if n > 0:
                bone_stats['keyframes_added'] += n
                bone_stats['actions'].append("gaps")

        # Phase 3: Smooth F-curves
        if smooth and has_fcurves:
            smooth_bone_fcurves(armature_obj, bone_name, smoothing_passes)
            bone_stats['actions'].append("smooth")

        stats[bone_name] = bone_stats

        if progress_callback:
            progress_callback(i + 1, total, bone_name)

    bpy.context.scene.frame_set(original_frame)
    return stats


import os

_PRESETS_DIR = os.path.join(os.path.dirname(__file__), "presets")


def _preset_path(name: str) -> str:
    if not name.endswith(".json"):
        name += ".json"
    return os.path.join(_PRESETS_DIR, name)


def save_preset(prefs, preset_name: str, bone_pairs: list[dict]) -> None:
    import json
    path = _preset_path(preset_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bone_pairs, f, indent=2, ensure_ascii=False)


def load_preset(prefs, preset_name: str) -> list[dict] | None:
    import json
    path = _preset_path(preset_name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def list_presets(prefs) -> list[str]:
    if not os.path.isdir(_PRESETS_DIR):
        return []
    files = sorted(f for f in os.listdir(_PRESETS_DIR) if f.endswith(".json"))
    return [os.path.splitext(f)[0] for f in files]


def delete_preset_file(preset_name: str) -> bool:
    path = _preset_path(preset_name)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
