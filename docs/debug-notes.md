# Current Debug Status — F-curves Not Found

## Problem

After baking animation (via the new `fcurve_ensure_for_datablock`-based bake), all Interpolate operations (Smooth, Predict, Gaps) report `0 kf, pred 0, smooth 0`, meaning no bones are found to have F-curves.

## Investigation Steps

### Step 1 — Confirm fcurve_ensure_for_datablock works

Add right after the `fcurve_ensure_for_datablock` call in `_ensure_fcurve()`:

```python
print(f"[ENSURE] fcu={fcu} kf_count={len(fcu.keyframe_points) if fcu else -1}")
```

### Step 2 — Confirm bake created animation data

In `bake_retargeted_animation`, after the loop, add:

```python
action = target_arm.animation_data.action if target_arm.animation_data else None
print(f"[BAKE] anim_data={target_arm.animation_data is not None}")
print(f"[BAKE] action={action}")
if action:
    print(f"[BAKE] action.name={action.name} is_empty={action.is_empty}")
    print(f"[BAKE] layers={action.layers_count} slots={action.slots_count}")
```

### Step 3 — Check bone data_path

In `get_bone_fcurves`, before the try block, add:

```python
print(f"[GETFCU] bone={bone_name} path={prefix + 'location'} action={action.name if action else 'NONE'}")
```

### Step 4 — List all actions in scene

In `interpolate_armature_animation`, after obtaining action, add:

```python
print(f"[INTERP] actions in scene:")
for a in bpy.data.actions:
    print(f"  name={a.name} users={a.users} is_empty={a.is_empty}")
```

## Possible Outcomes

| Output | Meaning | Next Step |
|---|---|---|
| `fcu is not None, kf_count > 0` but `has_fcurves=False` | `keyframe_points` truthiness wrong | Change check to `len(fcu.keyframe_points) > 0` |
| `fcu is None` | `fcurve_ensure_for_datablock` not available | Check Blender version |
| `fcu is not None, kf_count = 0` | Bake loop didn't insert keyframes | Check `keyframe_points.insert()` return |
| `anim_data=False` or `action=None` | Bake didn't set action | Check `animation_data_create()` call |
| `action is not None, is_empty=True` | Bake wrote somewhere unexpected | Search NLA tracks, other actions |

## Environment

- Blender 5.1 (specific build unknown)
- Action type: `is_action_legacy=True`, `is_action_layered=True`
- `action.fcurve_ensure_for_datablock` exists but was called with str initially
- Windows 10

## Known Safe Assumptions

- `action.fcurve_ensure_for_datablock(ob, path, index=, group_name=)` exists and accepts `bpy.types.Object` as datablock
- `FCurve.keyframe_points.insert(frame, value)` returns `Keyframe`
- `fcurve.update()` recalculates handles
- `bone.keyframe_insert(data_path, frame=, group=)` works in 5.1
- `len(fcurve.keyframe_points)` works on empty collections
