# Changelog

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
