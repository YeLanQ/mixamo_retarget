# 骨骼选中同步架构 (Bone Selection Sync)

## 概述

实现 3D 视口骨骼选中 → UI Mapping 行高亮的**单向**同步。

| 方向 | 触发方式 | 机制 |
|------|---------|------|
| 视口 → UI | 在 3D Viewport 点击骨骼 | `depsgraph_update_post` handler |

不包含 UI → 视口方向：点击行不会自动选中骨骼。🦴 图标按钮 (`MIXAMO_OT_SelectMappingBone`) 是一个独立的 Operator，不属于自动同步体系。

## 架构图

```
3D Viewport              depsgraph_update_post        UI template_list
┌──────────────┐       ──────────────────────────►    ┌──────────────┐
│ select bone  │                                      │ highlight    │
│ (pose mode)  │                                      │ matching row │
└──────┬───────┘                                      └──────┬───────┘
       │                                                     │
       │  _sync_bone_selection()                              │ bone_mapping_index
       │  finds bone_name in bone_mappings                    │ (IntProperty)
       ▼                                                     ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  bone_mapping_index  (唯一共享状态)                           │
   └─────────────────────────────────────────────────────────────┘
```

## 代码位置

- `ui_list.py` — `_sync_bone_selection()` handler + `MIXAMO_UL_BoneMappings` UIList

## 触发链路

```
用户在 3D Viewport 中点击骨骼 (Pose Mode)
  └→ 骨骼选中状态变化
    └→ Depsgraph 重新求值
      └→ depsgraph_update_post handler 触发
        └→ _sync_bone_selection() 执行
          ├─ 检查 armature / mode / 场景属性
          ├─ 获取第一个 selected_pose_bone 名称
          ├─ 与缓存比较，相同则 return（防抖）
          ├─ 更新缓存
          └─ 遍历 bone_mappings
               └─ 匹配 source_bone 或 target_bone
                    └─ 更新 bone_mapping_index → 对应行高亮
```

## 实现

```python
_cache_armature = ""
_cache_bone = ""

def _sync_bone_selection(*_args):
    context = bpy.context
    scene = context.scene
    arm = context.active_object
    if not arm or arm.type != 'ARMATURE':
        return
    if context.mode != 'POSE':
        return

    s = getattr(scene, "mixamo_retarget", None)
    if not s:
        return

    global _cache_armature, _cache_bone

    selected = context.selected_pose_bones
    if not selected:
        return

    arm_name = arm.name
    selected_name = selected[0].name
    if (arm_name, selected_name) == (_cache_armature, _cache_bone):
        return
    _cache_armature, _cache_bone = arm_name, selected_name

    for idx, item in enumerate(s.bone_mappings):
        if item.source_bone == selected_name or item.target_bone == selected_name:
            if s.bone_mapping_index != idx:
                s.bone_mapping_index = idx
            break
```

## 缓存防抖

`depsgraph_update_post` 每帧可能被多次触发（动画播放、视口操作等）。

使用 `(_cache_armature, _cache_bone)` 模块级元组记录上一次同步的状态：

- 骨骼未变化 → 直接 return，零开销
- 变化后更新缓存再继续，避免同一骨骼反复搜索映射表

## 设计决策

### 为什么只做单向同步？

- **视口选中骨骼 → 行高亮**：用户定位骨骼后，需要快速在 Mapping 面板找到对应行
- 反过来（行点击 → 选中骨骼）是显式操作，应由 🦴 图标按钮触发，不属于自动同步范畴

### 为什么不使用 `bone_mapping_index` 的 msgbus 订阅？

Blender 的 `msgbus.subscribe_rna` 可以监听属性变化，但：

- 触发时机在 RNA 写入时，可能在 UI 构建中途
- 无法区分"用户点击行"和"代码写回"——需要额外 flag 区分
- 调试复杂度大于 depsgraph handler

### 为什么 handler 在 `depsgraph_update_post` 而不是 `scene_update_post`？

| handler | 触发时机 | 问题 |
|---------|---------|------|
| `scene_update_post` | 每帧场景更新后 | Blender 4.0+ 不再保证触发 |
| `depsgraph_update_post` | Depsgraph 求值完成后 | 骨骼选中变化必然触发 depsgraph 重求值 |

## 注册与生命周期

```python
def register():
    for cls in _classes:
        _safe_register_class(cls)
    bpy.app.handlers.depsgraph_update_post.append(_sync_bone_selection)

def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(_sync_bone_selection)
    for cls in reversed(_classes):
        _safe_unregister_class(cls)
```

- handler 在 `ui_list.register()` 中追加到全局列表
- 卸载时 remove，避免 dangling handler 导致 Blender 崩溃

## 验证方法

1. 打开 Bone Mapping 面板（Retarget 标签页）
2. 在 3D Viewport 中 Pose Mode 下点击骨骼
3. 观察 template_list 中对应行是否同步高亮
4. 点击某行（不点 🦴 图标），确认视口骨骼选中状态不变
5. 在 `source_bone` / `target_bone` Search 字段输入改名，确认不会干扰视口选中同步
