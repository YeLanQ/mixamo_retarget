# Bone Editor 骨骼变换增量编辑器

## 概述

Bone Editor 面板允许用户在**姿态模式 (Pose Mode)** 下对选中的骨骼进行**增量加减**变换操作，支持**单帧**和**多帧范围**执行。

面板位于 `View3D > Sidebar > Mixamo Retarget > Bone Editor`，仅在 `context.mode == 'POSE'` 时显示。

## 界面布局

```
┌─────────────────────────────────────┐
│  Bone Editor                        │
│  ┌───────────────────────────────┐  │
│  │  BoneName                     │  │
│  │  Loc  X:1.0000  Y:0.0000  .. │  │
│  │  Rot  X:0.0000  Y:0.0000  .. │  │
│  │  Scl  X:1.0000  Y:1.0000  .. │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌─Channels──────────────────────┐  │
│  │  [X] [Y] [Z]  Rot:[X][Y][Z]  │  │
│  │  [All] [None]                 │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌─Operation─────────────────────┐  │
│  │  [Add (+)] [Increment 0.1000] │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌─Apply To──────────────────────┐  │
│  │  [Current Frame]              │  │
│  └───────────────────────────────┘  │
│                                     │
│  [ ⏵ Execute ]                      │
└─────────────────────────────────────┘
```

## 功能说明

### 1. 骨骼选择与实时数值显示

选中姿态骨骼后，面板自动显示其当前帧的 **Location (X/Y/Z)**、**Rotation Euler (X/Y/Z)**、**Scale (X/Y/Z)** 数值。数值随帧变化实时刷新。

### 2. 通道选择 (Channels)

通过 toggle 按钮选择需要操作的通道：

| 组 | 通道 | 对应数据路径 |
|----|------|-------------|
| Loc | X / Y / Z | `bone.location[0/1/2]` |
| Rot | X / Y / Z | `bone.rotation_euler[0/1/2]` |
| Scl | X / Y / Z | `bone.scale[0/1/2]` |

- **All** — 选中全部 9 个通道
- **None** — 清空所有通道

### 3. 增量运算 (Operation)

- **Add (+)** — `新值 = 旧值 + Increment`
- **Subtract (-)** — `新值 = 旧值 - Increment`
- **Snap (📋)** — 将第一个已选通道的当前值复制到 Increment 输入框

### 4. 应用范围 (Apply To)

- **Current Frame** — 仅修改当前帧
- **Frame Range** — 修改指定帧范围（含头尾），每一帧都执行运算并打关键帧

### 5. 执行

点击 **Execute** 后：
1. 遍历所有指定帧
2. 对每个已选通道读取当前值 → 计算 ±Increment → 写入新值 → 打关键帧
3. 报告修改的通道数和帧数

## 架构

### PropertyGroup: `MIXAMO_BoneEditSettings`

文件: `properties.py:38-72`

定义在 `MIXAMO_SceneSettings` 之前，被其通过 `PointerProperty(type=MIXAMO_BoneEditSettings)` 引用。

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `increment` | FloatProperty | 0.1 | 增量值，precision=4 |
| `operation` | EnumProperty | ADD | ADD / SUB |
| `apply_mode` | EnumProperty | CURRENT | CURRENT / RANGE |
| `frame_start` | IntProperty | 1 | 起始帧 |
| `frame_end` | IntProperty | 250 | 结束帧 |
| `use_loc_x/y/z` | BoolProperty | False | Location 通道开关 |
| `use_rot_x/y/z` | BoolProperty | False | Rotation 通道开关 |
| `use_scale_x/y/z` | BoolProperty | False | Scale 通道开关 |

### Operators

#### `MIXAMO_OT_BoneTransformEdit`
- bl_idname: `mixamo_retarget.bone_transform_edit`
- bl_options: `REGISTER, UNDO`
- 核心逻辑：遍历帧 → 遍历通道 → `getattr(bone, data_path)[index]` → 加减 → `keyframe_insert`

#### `MIXAMO_OT_BoneEditChannelsToggle`
- bl_idname: `mixamo_retarget.bone_edit_channels_toggle`
- 参数 `state: BoolProperty` — True=全开, False=全关

#### `MIXAMO_OT_BoneEditSnapValues`
- bl_idname: `mixamo_retarget.bone_edit_snap_values`
- 将第一个已选通道的当前值复制到 `increment`

### Panel: `MIXAMO_PT_BoneEditor`

文件: `panels.py:11-92`

- bl_idname: `MIXAMO_PT_BoneEditor`
- bl_order: 5（位于侧栏顶部）
- poll: `context.mode == 'POSE'`
- draw: 显示数值、通道开关、运算设置、帧范围、执行按钮

### 注册顺序

```python
# properties.py
_classes = [
    MIXAMO_BoneMappingItem,
    MIXAMO_BoneEditSettings,    # 必须在 SceneSettings 之前
    MIXAMO_SceneSettings,       # 引用 MIXAMO_BoneEditSettings
    MIXAMO_AddonPreferences,
]
```

## 使用示例

### 示例 1：将骨骼沿 X 轴移动 0.5 单位

1. 进入 Pose Mode，选择骨骼
2. 勾选 `Loc: [X]`
3. Operation: `Add (+)`, Increment: `0.5`
4. Apply To: `Current Frame`
5. 点击 Execute → 骨骼 X 位置 +0.5，当前帧打关键帧

### 示例 2：批量调整整个动画的旋转

1. 选择骨骼
2. 勾选 `Rot: [X] [Y] [Z]`
3. Operation: `Add (+)`, Increment: `0.1`
4. Apply To: `Frame Range`, Start: `1`, End: `100`
5. 点击 Execute → 第 1-100 帧的 Rotation 各通道均 +0.1

### 示例 3：精确还原某个姿势值

1. 选择骨骼
2. 只勾选 `Loc: [Y]`
3. 点击 Snap (📋) → Increment 变为当前 Y 值
4. Operation: `Subtract (-)`
5. 点击 Execute → Y 位置归零

## 注意事项

- Rotation 使用 Euler 模式 (`bone.rotation_euler`)，Quaternion 骨骼会自动转换
- 多帧模式下会逐帧 `frame_set()`，大量帧范围内执行可能会有短暂卡顿
- 操作支持 Undo（`bl_options = {"REGISTER", "UNDO"}`）
- 面板仅在 Pose Mode 下可见，其他模式下隐藏
