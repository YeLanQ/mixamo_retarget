# 补帧系统架构文档 (Interpolation System)

## 概述

补帧系统是 Mixamo Retarget 的核心后处理功能，解决三个问题：

| 模式 | 目标 | 管线 |
|------|------|------|
| **Predict (预测)** | 为无动画骨骼生成动画 + 平滑 | fill → gaps → smooth |
| **Smooth** | 平滑抖动曲线 | fill → smooth |
| **Fill Gaps** | 补齐间隔关键帧 | fill → gaps |

三个模式共享一个 `fill_missing=True` 的保底策略：**任何没有 FCurve 的骨骼都会先被赋予基础关键帧**，之后才执行各自的特化操作。

## 管线设计（三阶段 Pipeline）

### Phase 1: 基础关键帧创建 (`fill_missing=True`)

对所有没有 FCurve 的骨骼，按优先级尝试三种策略：

```
No FCurve? ──→ 1a. Mirror 镜像推导
              ──→ 1b. Predict from related (parent/chain/sibling/child)
              ──→ 1c. Rest-pose 回退（必保底）
```

- **1a Mirror**: 如果骨骼有 left/right 镜像骨骼且镜像有动画，将镜像动画镜像复制过来
- **1b Related Predict**: 扫描相关骨骼（父级→链祖先→兄弟→子级），找到有动画的骨骼，推导本骨骼的变换
- **1c Rest-pose 回退**: 以上都失败时，在每帧插入骨骼的 Rest Pose 本地变换作为关键帧

### Phase 2: 补齐间隔 (`fill_gaps=True`)

在已有的 FCurve 上，按 `Frame Step` 间隔补插关键帧。

### Phase 3: 平滑 (`smooth=True`)

对已有的 FCurve 进行 Moving Average 平滑，`Smoothing Passes` 控制迭代次数。

## 关键 Bug 修复

### Bug 1: `_ensure_fcurve` 误用于只读检测

```python
# BEFORE — 错误
def get_bone_fcurves(armature_obj, action, bone_name):
    fcu = _ensure_fcurve(action, armature_obj, prefix + 'location', index=idx)
    if fcu and fcu.keyframe_points:
        loc[idx] = fcu
```

Blender 5.1 中 `fcurve_ensure_for_datablock` 会**自动创建 FCurve**（如果不存在），导致每次只读检测都产生空 FCurve 垃圾，污染 Action。同时 `bone_has_fcurves()` 永远返回 `True`（有空曲线），导致后续"无 FCurve 才执行"的逻辑全部跳过。

```python
# AFTER — 修复
def _find_fcurve(action, data_path, index=0):
    """只查找,不创建。遍历 action.fcurves 匹配 data_path + array_index"""
    if hasattr(action, 'fcurves'):
        for fcu in action.fcurves:
            if fcu.data_path == data_path and fcu.array_index == index:
                return fcu
    return None

def get_bone_fcurves(armature_obj, action, bone_name):
    fcu = _find_fcurve(action, prefix + 'location', index=idx)
    if fcu and fcu.keyframe_points:
        loc[idx] = fcu
```

所有只读函数已替换为 `_find_fcurve`：
- `get_bone_fcurves()`
- `bone_has_fcurves()`
- `_get_bone_keyframe_frames()`
- `_clear_bone_fcurves()`
- `smooth_bone_fcurves()`

`_ensure_fcurve` 保留，仅用于写入场景（`bake_retargeted_animation`）。

### Bug 2: 模式标志无保底

```python
# BEFORE — predict 模式只设 predict=True
fill_missing = self.mode in ("missing", "all")
fill_gaps = self.mode in ("gaps", "all")
smooth     = self.mode in ("smooth", "all")
predict    = self.mode in ("predict", "all")

# AFTER — 每个模式的 fill_missing 都 = True
fill_missing = True  # 总是先确保基础关键帧
fill_gaps = self.mode in ("gaps", "predict")
smooth    = self.mode in ("smooth", "predict")
predict   = self.mode == "predict"
```

### Bug 3: 无回退机制

旧代码中，无 FCurve 骨骼依次尝试 mirror → predict，如果全部失败（例如没有任何相关骨骼有动画），**没有兜底代码**，骨骼最终仍然 0 关键帧。

新增 Phase 1c `rest_pose` 回退：在每帧写入骨骼 Rest Pose 的本地变换（`location`/`rotation_quaternion`/`scale`），确保每个骨骼至少有基础动画数据可被后续 gaps + smooth 处理。

## 核心函数层级

```
operators.py
  MIXAMO_OT_InterpolateBones.execute()
    └─ 设置模式标志 → 逐骨骼调用

retarget.py
  interpolate_armature_animation()
    ├─ Phase 1: 基础关键帧
    │   ├─ derive_from_mirror_bone()
    │   ├─ predict_bone_from_related()
    │   │   └─ _find_related_bones() → 按优先级排序
    │   │   └─ _predict_bone_from_source() → mirror/parent/chain/sibling/child
    │   └─ fill_missing_bone_animation() → rest pose fallback
    ├─ Phase 2: 补齐间隔
    │   └─ fill_keyframe_gaps()
    └─ Phase 3: 平滑
        └─ smooth_bone_fcurves()
```

## 关键数据结构

```python
# 每骨骼统计
stats = {
    bone_name: {
        'keyframes_added': int,   # 新插入的关键帧数
        'actions': [str],         # 执行的操作: "mirror"|"predict:parent"|"rest_pose"|"gaps"|"smooth"
    }
}

# 相关骨骼查找优先级
related = [
    ('mirror', mirror_bone_name),
    ('parent', parent_bone_name),
    ('chain_ancestor', grandparent_name),
    ('sibling', sibling_bone_name),
    ('child', child_bone_name),
]
```

## Bug 4: Child/Sibling 推导缺少 Rest-Pose Offset 抵消

### 问题

`_predict_bone_from_source` 在 `child` 和 `sibling` 推导中，计算 `source.matrix @ source.matrix_basis⁻¹` 得到的是 `parent_matrix @ child_rest_local`（父级矩阵 × 子级的骨骼偏移），而不是纯 `parent_matrix`。

对于 Hips（根骨骼），`child_rest_local` 包含子级骨骼（Spine）相对 Hips Tail 的偏移（约 10 单位 Y 轴平移 + 可能的旋转），导致 Hips 位置凭空上移，动画奇怪。

### 修复

**child 推导**（按优先级最高，用于根骨骼等）：

```
# BEFORE
desired = child.matrix @ child.matrix_basis⁻¹
→ parent_matrix @ child_rest_offset  (含骨骼长度)

# AFTER
child_rest_local = _get_rest_local(armature_obj, source_name)
desired = child.matrix @ child.matrix_basis⁻¹ @ child_rest_local⁻¹
→ parent_matrix  (纯父级矩阵)
```

**sibling 推导**（左右对称骨骼互推）：

```
# BEFORE
shared_parent = sibling.matrix @ sibling.matrix_basis⁻¹  ← 含 sibling 自身 rest offset
desired = shared_parent @ target_rest_local              ← 叠加 target 的 rest offset

# AFTER
shared_parent = sibling.matrix @ sibling.matrix_basis⁻¹ @ sibling_rest_local⁻¹
desired = shared_parent @ target_rest_local
```

**chain_ancestor 推导**：移除错误的 `parent_edit.length` 尾部调整（原用于抵消 parent length，但在链式推导中不适用）。

## 向后兼容性

- 所有对外接口签名未变（`interpolate_armature_animation` 参数列表不变）
- 新增 `_find_fcurve` 内部函数，不影响外部调用
- 模式标志的含义已改变：之前 `predict=True` 只预测不保底，现在 `predict=True` 隐含保底 + gaps + smooth。但 GUI 按钮始终按新模式工作，不影响用户体验。

## 常见问题

### Q: 为什么 Hips 动画预测后位置偏移？

**原因**：Child 推导未抵消子骨骼的 Rest-Pose Offset。`spine.matrix @ spine.matrix_basis⁻¹` 得到的是 `hips_pose @ spine_rest_local`，其中 `spine_rest_local` 包含从 Hips Tail 到 Spine Head 的偏移（约 10 单位 + 旋转）。该偏移错误地被当作 Hips 的 Pose 写入。

**修复**：在公式右侧乘以 `spine_rest_local⁻¹` 抵消该偏移。

### Q: 多个子骨骼（Spine + LeftUpLeg + RightUpLeg）如何选择？

按 `_find_related_bones` 的优先级顺序，遍历到第一个有 FCurve 的子骨骼即停止。通常在 Mixamo 骨骼中 Spine 最先被命中。如果需要更精确的推导（如多子骨骼加权平均），属于未来增强方向。
