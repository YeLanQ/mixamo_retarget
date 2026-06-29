# Retargeting Debug Notes

## Constraint Pipeline

```
apply_retargeting_constraints()
  ├─ For each bone pair:
  │   ├─ Remove existing MIXAMO_RETARGET_* constraints
  │   ├─ Determine is_root (auto or user-specified root bone)
  │   └─ Create constraints based on mode:
  │       ├─ COPY_ROTATION  → COPY_ROTATION (WORLD→WORLD) + optional COPY_LOCATION
  │       ├─ COPY_TRANSFORMS → COPY_ROTATION (WORLD→WORLD) + TRANSFORM location (root)
  │       ├─ CHILD_OF        → CHILD_OF (location + rotation)
  │       └─ CHILD_OF_ROTATION → CHILD_OF (rotation only)
  └─ Return (applied_count, warnings)
```

## Constraint Names

All constraints use prefix `MIXAMO_RETARGET_`:

| Name | Type | Created by |
|------|------|-----------|
| `MIXAMO_RETARGET_Location` | COPY_LOCATION or TRANSFORM | COPY_ROTATION (root) or COPY_TRANSFORMS (root) |
| `MIXAMO_RETARGET_Rotation` | COPY_ROTATION | All modes |
| `MIXAMO_RETARGET_ChildOf` | CHILD_OF | CHILD_OF mode |
| `MIXAMO_RETARGET_ChildOfRotation` | CHILD_OF (rotation only) | CHILD_OF_ROTATION mode |

## is_root Detection

```python
if root_bone:   # user-specified via UI field
    is_root = (tgt_name == root_bone)
else:
    src_name_lower = src_name.lower()
    is_root = any(k in src_name_lower for k in ("hips", "pelvis", "root"))
```

- Hips auto-detected from source bone name containing "hips", "pelvis", or "root"
- User can override by setting a custom root bone name in the UI
- Only root bones receive location tracking (COPY_LOCATION or TRANSFORM)

## Root Location: TRANSFORM Constraint

Used by `COPY_TRANSFORMS` mode for the root bone:

```
from_min = src_rest_world.translation
from_max = src_rest_world.translation + (1, 1, 1)
to_min   = tgt_rest_world.translation
to_max   = tgt_rest_world.translation + (1, 1, 1)
```

Result: `target_pos = tgt_rest + (source_pos - src_rest)`

This keeps the target at its rest position when the source is at rest, and tracks source motion with the same offset.

## Hips Location Pitfalls

| Issue | Cause | Effect |
|-------|-------|--------|
| Target Hips off in XZ | Source frame 0 ≠ source rest pose | Frame 0 target off by (source_0 - source_rest) |
| Target Hips off in Z | Different world transforms between skeletons | Offset direction includes bone rotation |
| Target Hips floating | Source Hips elevated at frame 0 | Entire character shifted up |

## Retarget Mode Summary

| Mode | Root Location | Root Rotation | Non-root Location | Non-root Rotation |
|------|--------------|--------------|-------------------|-------------------|
| COPY_ROTATION | COPY_LOCATION (direct) | WORLD→WORLD | — | WORLD→WORLD |
| COPY_TRANSFORMS | TRANSFORM (offset) | WORLD→WORLD | — | WORLD→WORLD |
| CHILD_OF | CHILD_OF | CHILD_OF | CHILD_OF | CHILD_OF |
| CHILD_OF_ROTATION | — | CHILD_OF (rot) | — | CHILD_OF (rot) |

## Human Bone Hierarchy (HUMAN_BONE_NAMES)

```
hips → spine → chest → upperChest → neck → head
                                    → leftEye / rightEye / jaw
         leftUpperLeg → leftLowerLeg → leftFoot → leftToes
         rightUpperLeg → rightLowerLeg → rightFoot → rightToes
         leftShoulder → leftUpperArm → leftLowerArm → leftHand
                     → finger bones (leftThumb/Index/Middle/Ring/Little × 3)
         rightShoulder → rightUpperArm → rightLowerArm → rightHand
                      → finger bones (rightThumb/Index/Middle/Ring/Little × 3)
```

FINGER_HUMAN_BONES = `HUMAN_BONE_NAMES[25:]` (30 finger bones)

Required bones (minimum for detection): hips, spine, head, both upper/lower legs, feet, both upper/lower arms, hands.

## Detection Passes

```
detect_skeleton()
  Pass 1: Named conventions (Mixamo, VRM, Standard)
  Pass 2: Normalized name comparison
  Pass 3: Position-based heuristic (_match_by_position)
```

Finger bones are detected by naming convention only (Pass 1 or 2). Position-based detection does not identify individual finger bones.
