# Changelog

## [2.0.2] - 2026-06-29

### Added
- `MIXAMO_OT_FillMappingBone` — `→` button in Retarget panel fills source/target bone name from the selected bone in the viewport
- Presets stored as `.json` files in `presets/` directory (instead of addon preferences), enabling manual editing and sharing
- `MIXAMO_OT_DeletePreset` now removes the preset file from disk
- 新增 `→` 按钮：从视口选中骨骼自动填入映射行
- 预设改为 `presets/` 目录中的 `*.json` 文件存储（取代 addon prefs），支持手动编辑和分享

### Changed
- `Remove Constraints` now only removes constraints from mapped (enabled) bones, not all constraints on the armature
- Presets panel lists files from `presets/` directory with improved UI
- `package.ps1` includes the `presets/` directory in the zip
- 移除约束仅作用于已映射骨骼，不再清理骨架上的全部约束

### Removed
- Panel→viewport bone selection sync (removed `_select_bone_in_viewport` and Direction 2 logic in `__init__.py`)
- Redundant `_sync_bone_selection` handler in `ui_list.py` (logic consolidated into `__init__.py`)
- `BONE_DATA` icon buttons from each mapping row in `ui_list.py`
- 移除面板→视口的骨骼选中反向同步
- 移除 `ui_list.py` 中冗余的同步 handler 和每行的骨骼图标按钮

## [2.0.1] - 2026-06-29

### Added
- Editable X/Y/Z rotation fields for skeleton creation (default X=90°, Y=0°, Z=0°)
- "Apply Rotation" toggle (default on) — when enabled, rotation is baked into bone data (equivalent to Ctrl+A > Apply Rotation); when off, rotation stays on the armature object
- 创建骨骼时增加 X/Y/Z 可编辑旋转值（默认 X=90°, Y=0°, Z=0°）
- "Apply Rotation" 开关（默认开启）—— 开启时将旋转写入骨骼数据（等效 Ctrl+A > 应用旋转）；关闭时旋转保留在骨架对象上
- Bidirectional bone selection sync between viewport and mapping panel (click bone → highlight row, click bone icon in row → select bone)
- 视口与映射面板双向骨骼选择同步（选中骨骼 → 高亮行，点击行中骨骼图标 → 选中骨骼）

### Changed
- Hips defaults to `COPY_TRANSFORMS` (root motion), finger bones default to `CHILD_OF` (joint position), others `COPY_ROTATION`
- Hips 默认使用 `COPY_TRANSFORMS`（根运动），手指骨默认 `CHILD_OF`（关节位置），其余 `COPY_ROTATION`

### Fixed
- Finger joints now properly synchronize position during retargeting — uses `CHILD_OF` constraint instead of `COPY_ROTATION` for finger bones
- 手指重定向后关节位置同步问题 —— 手指骨骼改用 `CHILD_OF` 约束替代 `COPY_ROTATION`
- `FINGER_HUMAN_BONES` slice index was wrong (81→25) causing finger bones to default to `COPY_ROTATION`
- `FINGER_HUMAN_BONES` 切片索引错误（81→25）导致手指骨默认使用了 `COPY_ROTATION`

## [2.0.0] - Initial release
