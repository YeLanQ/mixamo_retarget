# FAQ — Mixamo Retarget Blender 5.1 Migration

## Q: Blender 5.1 为什么 action.fcurves 没了？

Blender 4.4 开始引入 Layered Action 系统，`action.fcurves` 被标记为 deprecated。Blender 5.0 正式移除。

新的 F-curves 访问方式：

```
action.layers[0].strips[0].channelbag(slot).fcurves
```

但不需要手动遍历层级——用 `action.fcurve_ensure_for_datablock(ob, path, index=)` 一行搞定。

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
