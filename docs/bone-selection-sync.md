# 骨骼选中同步架构 (Bone Selection Sync)

## 概述

实现 3D 视口骨骼选中 → UI Mapping 行高亮的**单向**同步。

| 方向 | 触发方式 | 机制 |
|------|---------|------|
| 视口 → UI | 在 3D Viewport 点击骨骼 | `depsgraph_update_post` handler |

**不包含** UI → 视口方向：点击行不会自动选中骨骼。`MIXAMO_OT_SelectMappingBone`（🦴 图标）是一个独立 Operator，已于 `ui_list.py` 中移除，不再显示在行上；如需从面板定位到视口骨骼，请使用 `MIXAMO_OT_FillMappingBone`（`→` 按钮）反向填入。

## 架构图

```
3D Viewport              depsgraph_update_post        UI template_list
┌──────────────┐       ──────────────────────────►    ┌──────────────┐
│ select bone  │                                      │ highlight    │
│ (pose mode)  │                                      │ matching row │
└──────┬───────┘                                      └──────┬───────┘
       │                                                     │
       │  _sync_selection()                                   │ bone_mapping_index
       │  finds bone_name in bone_mappings                    │ (IntProperty)
       ▼                                                     ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  bone_mapping_index  (唯一共享状态)                           │
   └─────────────────────────────────────────────────────────────┘
```

## 代码位置

- `__init__.py` — `_sync_selection()` handler （`depsgraph_update_post`）
- `ui_list.py` — `MIXAMO_UL_BoneMappings` UIList（仅渲染，不含同步逻辑）

## 触发链路

```
用户在 3D Viewport 中点击骨骼 (Pose Mode)
  └→ 骨骼选中状态变化
    └→ Depsgraph 重新求值
      └→ depsgraph_update_post handler 触发
        └→ _sync_selection() 执行
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
_last_selected_bone = ""
_last_mapping_index = -1

@persistent
def _sync_selection(scene):
    context = bpy.context
    s = context.scene.mixamo_retarget
    arm = context.active_object
    if not arm or arm.type != 'ARMATURE' or context.mode != 'POSE':
        return

    current_index = s.bone_mapping_index
    selected = context.selected_pose_bones
    current_bone = selected[0].name if selected else ""

    if current_bone and current_bone != _last_selected_bone:
        for i, item in enumerate(s.bone_mappings):
            if item.target_bone == current_bone or item.source_bone == current_bone:
                if current_index != i:
                    s.bone_mapping_index = i
                _last_selected_bone = current_bone
                _last_mapping_index = i
                return

    if current_bone:
        _last_selected_bone = current_bone
    _last_mapping_index = current_index
```

## 缓存防抖

`depsgraph_update_post` 每帧可能被多次触发（动画播放、视口操作等）。

使用 `_last_selected_bone` + `_last_mapping_index` 模块级变量记录上一次同步的状态：

- 骨骼未变化 → 直接 return，零开销
- 变化后更新缓存再继续，避免同一骨骼反复搜索映射表

## 设计决策

### 为什么只做单向同步？

- **视口选中骨骼 → 行高亮**：用户定位骨骼后，需要快速在 Mapping 面板找到对应行
- 反过来（行点击 → 选中骨骼）原本通过 `_select_bone_in_viewport()` 实现，但会与用户手动操作骨骼相互干扰，已移除

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
    ...
    bpy.app.handlers.depsgraph_update_post.append(_sync_selection)

def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(_sync_selection)
    ...
```

- handler 在 `__init__.register()` 中追加到全局列表
- 卸载时 remove，避免 dangling handler 导致 Blender 崩溃

## 验证方法

1. 打开 Bone Mapping 面板（Retarget 标签页）
2. 在 3D Viewport 中 Pose Mode 下点击骨骼
3. 观察 template_list 中对应行是否同步高亮
4. 点击某行，确认视口骨骼选中状态不变（无反向同步）
