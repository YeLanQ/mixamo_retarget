# Mixamo Retarget

A Blender add-on for retargeting Mixamo FBX animations between Mixamo-rigged characters. Supports constraint-driven retargeting, animation baking, and bone in-betweening (补帧).

## Installation

1. Download the latest `.zip` from the releases page
2. In Blender: `Edit > Preferences > Add-ons > Install from Disk`
3. Enable the add-on: search for "Mixamo Retarget" and tick the checkbox
4. The panel appears in `View3D > Sidebar (N-panel) > Mixamo Retarget`

## Quick Start

### Basic Retargeting Workflow

1. **Import a Mixamo FBX** — `Import Mixamo FBX` button, or manually import and click `Select as Source`
2. **Select your character armature** — click `Select as Target`
3. **Auto-match bones** — click `Auto-Match Bones`, or manually add bone pairs
4. **Apply constraints** — click `Apply Constraints` to drive the target rig
5. **Bake animation** — set frame range and click `Bake & Remove Constraints`

### Bone In-Betweening (补帧)

After baking, use the **Bake & Interpolate** panel (Pose Mode only):

| Mode | Description |
|------|-------------|
| Predict (预测) | Generate animation for bones without F-curves + smooth everything |
| Smooth | Moving-average smoothing for jerky F-curves |
| Fill Gaps | Fill missing keyframes on existing F-curves |

### Bone Editor (Pose Mode only)

Fine-tune individual bone transforms with incremental value changes:

1. Enter **Pose Mode** and select a bone
2. Toggle the transform channels you want to modify (Loc/Rot/Scale X/Y/Z)
3. Set an **Increment** value and choose **Add (+)** or **Subtract (-)**
4. Choose **Current Frame** or a **Frame Range**
5. Click **Execute**

See `docs/bone-editor.md` for details.

## Panels

| Panel | Order | Pose Mode Required | Description |
|-------|-------|-------------------|-------------|
| Bone Editor | 5 | Yes | Incremental bone transform editing |
| Import Mixamo FBX | 10 | No | FBX import & Mixamo skeleton creation |
| Retarget | 20 | No | Armature selection, bone mapping, constraints |
| Bake & Interpolate | 30 | Yes | Baking, smoothing, prediction, gap filling |
| Presets | 40 | No | Save/load/export/import bone mappings |

## Documentation

- `docs/bone-editor.md` — Bone Editor technical reference
- `docs/interpolation-system.md` — In-betweening pipeline architecture
- `docs/blender-51-fcurves-migration.md` — Blender 5.1 F-curves API migration notes
- `docs/faq.md` — Frequently asked questions
- `docs/debug-notes.md` — Debugging notes

## License

GPL-3.0-or-later — see `LICENSE`.
