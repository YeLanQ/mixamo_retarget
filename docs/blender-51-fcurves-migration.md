# Blender 5.1 F-Curves API Migration

## Background

Blender 4.4 introduced the **Layered Action** system, replacing the legacy flat F-curve storage. In Blender 5.0 the legacy `Action.fcurves` property was removed entirely. All F-curves must now be accessed through the layered API.

This document describes how the Mixamo Retarget addon handles this change.

## Key API Changes

| Blender < 5.0 | Blender 5.1+ |
|---|---|
| `action.fcurves` (direct access) | Removed — raises `AttributeError` |
| `action.fcurves.new(data_path, index)` | `action.fcurve_ensure_for_datablock(ob, path, index=)` |
| `action.fcurves.find(data_path, index)` | N/A — use `fcurve_ensure_for_datablock` (always creates if missing) |
| `action.groups.new(name)` | Group name passed as `group_name=` parameter |
| Flat F-curve list | Layered: `action.layers[].strips[].channelbag(slot).fcurves` |

## Our Approach

### `_ensure_fcurve()` (compatibility layer)

```python
def _ensure_fcurve(action, armature_obj, data_path, index=0, group_name=''):
```

Unified accessor used everywhere instead of direct `action.fcurves` access:

1. **Blender 5.1+**: Calls `action.fcurve_ensure_for_datablock(armature_obj, data_path, index=index, group_name=group_name)` — this CREATES the F-curve if it doesn't exist, using the proper layered action structure.
2. **Blender < 5.0 (legacy)**: Falls back to `action.fcurves.find()` / `action.fcurves.new()`.
3. **Unknown**: Returns `None`.

### Reading F-curves (checking existence)

Since `fcurve_ensure_for_datablock` always creates, we check `keyframe_points` to distinguish "has animation" from "no animation":

```python
fcu = _ensure_fcurve(action, armature_obj, data_path, index=idx)
if fcu and fcu.keyframe_points:   # falsy when empty collection
    # F-curve exists AND has keyframes
```

Functions using this pattern:
- `get_bone_fcurves()` — returns FCurve only if it has keyframes
- `bone_has_fcurves()` — True if any channel has keyframes
- `_get_bone_keyframe_frames()` — collects frame numbers from keyframes
- `smooth_bone_fcurves()` — skips if `< 3 keyframes`
- `_clear_bone_fcurves()` — clears keyframe_points from each channel

### Writing F-curves (baking)

The new `bake_retargeted_animation()` no longer uses `nla.bake`. Instead:

```python
for frame in range(frame_start, frame_end + 1):
    for bone in bones:
        fcu = _ensure_fcurve(action, armature_obj, data_path, index=idx)
        fcu.keyframe_points.insert(frame, value)
        fcu.update()
```

This guarantees F-curves are created in the correct layered format.

## Current Blocker

**Symptom**: After Bake + Smooth/Predict/Gaps, console shows `(0 kf, pred 0, smooth 0)`.

**Root cause hypothesis**: `bone_has_fcurves()` returns `False` for all bones, so no interpolation code runs.

**Possible causes being investigated**:
1. `fcurve_ensure_for_datablock` creates F-curves but they don't contain keyframes (bake writes elsewhere)
2. `armature_obj` argument is incorrect type for `fcurve_ensure_for_datablock`
3. `bone.keyframe_insert()` (used in non-bake paths) writes to legacy format not visible to `fcurve_ensure_for_datablock`
4. `animation_data` or `animation_data.action` is `None` after bake

**Debug needed**: Add print after `fcurve_ensure_for_datablock` to confirm F-curve creation and keyframe count.

<｜｜DSML｜｜parameter name="filePath" string="true">D:\blender-addon\mixamo_retarget\docs\blender-51-fcurves-migration.md