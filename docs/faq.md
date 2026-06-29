# FAQ — Mixamo Retarget Blender 5.1 Migration

## Q: Blender 5.1 为什么 action.fcurves 没了？

Blender 4.4 开始引入 Layered Action 系统，`action.fcurves` 被标记为 deprecated。Blender 5.0 正式移除。

新的 F-curves 访问方式：

```
action.layers[0].strips[0].channelbag(slot).fcurves
```

但不需要手动遍历层级——用 `action.fcurve_ensure_for_datablock(ob, path, index=)` 一行搞定。

## Q: 各重定向模式有什么区别？

| 模式 | 约束 | 位置处理 | 旋转处理 |
|------|------|---------|---------|
| `COPY_ROTATION` | COPY_ROTATION + COPY_LOCATION（根部） | 根部：直接复制源世界位置；非根部：不处理 | WORLD→WORLD |
| `COPY_TRANSFORMS` | COPY_ROTATION + TRANSFORM（根部） | 根部：TRANSFORM 映射（休息姿势偏移）；非根部：不处理 | WORLD→WORLD |
| `CHILD_OF` | CHILD_OF（位置+旋转） | 源骨骼成为虚拟父级（带逆矩阵抵消休息差异） | 从源骨骼继承 |
| `CHILD_OF_ROTATION` | CHILD_OF（仅旋转） | 不处理（位置由目标骨架层级决定） | 从源骨骼继承，逆矩阵抵消休息差异 |

## Q: Hips 的 COPY_TRANSFORMS 为什么会改变播放原点？

TRANSFORM 约束使用公式 `目标位置 = 目标休息姿势 + (源动画位置 - 源休息姿势)`。当源动画第 0 帧的 Hips 位置不等于休息姿势时，目标在第 0 帧也会偏离休息姿势；如果源和目标骨架的世界空间位置不同，也会产生偏移。

这是**约束创建时记录的偏移基准**决定的——如果需要在特定帧保持目标静止，请在目标处于期望位置的那一帧创建约束。

## Q: 为什么手指骨骼蜷缩/粘在一起？

手指骨骼在不同骨架之间通常有**完全不同的休息姿势方向**（例如 Mixamo 的手指平伸 vs 其他骨架的微曲）。

WORLD→WORLD COPY_ROTATION 无法补偿休息姿势差异。手指应使用 `CHILD_OF_ROTATION` 模式，该模式通过自动逆矩阵抵消源/目标之间的休息姿势差异，仅复制相对旋转。

## Q: 如何让手指正确重定向？

1. 确保源和目标的手指骨骼已正确映射
2. 在映射表中将所有手指骨骼的模式设为 `CHILD_OF_ROTATION`
3. 点击 Apply Constraints
4. `CHILD_OF_ROTATION` 使用 `CHILD_OF` 约束（仅旋转），自动计算 `inverse_matrix` 抵消休息姿势偏移

## Q: fcurve_ensure_for_datablock 和原来的 fcurves 有什么不同？

- `action.furves` 是**只读迭代**，找不到就返回空
- `fcurve_ensure_for_datablock` 是**确保存在**，找不到就自动创建（含 layer/strip/slot/channelbag）
- 所以不能用它来"检查是否有 F-curves"——它永远会返回一个 FCurve 对象
- 正确方式是检查返回的 FCurve 是否有 `keyframe_points`（关键帧）

## Q: 为什么 bone.keyframe_insert() 还能用？

`bone.keyframe_insert()` 是 `bpy.types.ID` 的方法，走的是 Blender 内部动画管线，与 `action.fcurves` 无关。Blender 5.1 内部已适配 layered action，所以 `keyframe_insert` 仍然正常工作。

但不能通过 `action.fcurves` 读取它创建的关键帧——必须用 `fcurve_ensure_for_datablock`。

## Q: 旧的 nla.bake 还能用吗？

Blender 5.1 的 `nla.bake` 参数和功能未变，但存在一些兼容性问题：

- 开启 `use_current_action=True` 时，baked 数据存储位置可能不在 standard layered 结构中
- 某些 Blender 5.1 版本中，bake 后 `action.is_empty=True` 且 `layers_count=0`
- 建议使用新的手动 bake 函数替代

当前代码已替换为基于 `fcurve_ensure_for_datablock` + `keyframe_points.insert` 的手动 bake。

## Q: 当前插帧/预测/平滑功能为什么不生效？

所有插帧功能（Smooth/Predict/Gaps）都依赖 `bone_has_fcurves()` 判断骨骼是否有动画。如果返回 `False`，函数直接跳过该骨骼。

当前 `bone_has_fcurves()` 对所有骨骼返回 `False`，即使已经通过新 Bake 创建了关键帧。

## Q: 正在排查什么问题？

1. `fcurve_ensure_for_datablock` 返回的 FCurve 是否真的有 keyframe_points
2. Bake 循环是否真的写入了关键帧
3. `keyframe_points` 空集合在 `if fcu.keyframe_points:` 中是否为 falsy

详见 `docs/debug-notes.md`

## Q: 为什么 5.1 的 Action.is_action_legacy=True 且 is_action_layered=True？

这是 Blender 5.1 的版本特性——所有空 Action 同时标记为 legacy 和 layered。Legacy = True 不代表它是旧格式，而是表示"还没有 layer/slot 数据"。一旦添加 layer 或 slot，is_action_legacy 变为 False，is_action_layered 保持 True。

## Q: Bone Editor 的面板在哪？为什么看不到？

Bone Editor 面板位于 `View3D > Sidebar > Mixamo Retarget > Bone Editor`（列表第一项）。

**仅在姿态模式 (Pose Mode) 下显示**。如果处于 Object/Edit/Weight Paint 等其他模式，面板会自动隐藏。

## Q: Bone Editor 支持修改哪些属性？

支持 9 个通道的增量编辑：

| 通道 | 数据路径 | 说明 |
|------|---------|------|
| Loc X/Y/Z | `bone.location` | 位置，索引 0/1/2 |
| Rot X/Y/Z | `bone.rotation_euler` | 欧拉旋转，索引 0/1/2 |
| Scale X/Y/Z | `bone.scale` | 缩放，索引 0/1/2 |

Rotation 使用 Euler 模式，Quaternion 骨骼会自动转换。

## Q: Bone Editor 能否批量修改多帧？

可以。在 **Apply To** 中选择：
- **Current Frame** — 只修改当前帧
- **Frame Range** — 修改指定帧范围，每一帧都执行运算并打关键帧

## Q: Execute 按钮点击后没有反应？

检查以下几点：
1. 确保处于 **Pose Mode**
2. 确保选中了一个 **骨骼**
3. 确保至少勾选了 **一个通道**（Loc/Rot/Scl 中至少一个 X/Y/Z）
4. 检查 Blender 的系统控制台（Window > Toggle System Console）查看报错信息

## Q: Bone Editor 支持 Undo 吗？

支持。操作注册了 `bl_options = {"REGISTER", "UNDO"}`，可以通过 Ctrl+Z 撤销。

## Q: 增量运算的具体公式是什么？

- **Add (+)**: `新值 = 当前值 + 增量`
- **Subtract (-)**: `新值 = 当前值 - 增量`

每一帧独立计算，逐通道打关键帧。

## Q: Snap 按钮有什么用？

点击 Snap（📋 图标）会将当前选中的第一个通道的数值填入 Increment 输入框。例如只勾选了 Loc X，点击 Snap 后 Increment 自动变为当前帧的 X 值，方便做精确还原。

详见 `docs/bone-editor.md`。
