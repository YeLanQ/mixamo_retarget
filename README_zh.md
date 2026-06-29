# Mixamo Retarget — 使用手册

Blender 插件，用于在 Mixamo 骨骼角色之间重定向 Mixamo FBX 动画。支持约束驱动重定向、动画烘焙和骨骼补帧。

## 安装

1. 下载最新 `.zip` 包
2. Blender 中: `编辑 > 偏好设置 > 插件 > 从磁盘安装`
3. 搜索 "Mixamo Retarget" 并勾选启用
4. 面板出现在 `3D视图 > 侧栏 (N键) > Mixamo Retarget`

## 快速上手

### 基本重定向流程

1. **导入 Mixamo FBX** — 点击 `Import Mixamo FBX`，或手动导入后点击 `Select as Source`
2. **选择目标角色骨骼** — 点击 `Select as Target`
3. **自动匹配骨骼** — 点击 `Auto-Match Bones`，或手动添加骨骼映射对（选中骨骼后点击 `→` 按钮自动填入名称）
4. **应用约束** — 点击 `Apply Constraints` 驱动目标骨骼
5. **烘焙动画** — 设置帧范围后点击 `Bake & Remove Constraints`

### 骨骼补帧

烘焙动画后，使用 **Bake & Interpolate** 面板（需姿态模式）：

| 模式 | 说明 |
|------|------|
| Predict (预测) | 为无动画骨骼生成动画 + 全部平滑 |
| Smooth | 移动平均平滑抖动曲线 |
| Fill Gaps | 补齐现有 FCurve 上的间隔关键帧 |

### 骨骼编辑器（姿态模式）

对单个骨骼进行增量微调：

1. 进入 **姿态模式**，选中一个骨骼
2. 勾选要修改的变换通道（位置/旋转/缩放 X/Y/Z）
3. 设置 **增量值** 和运算方式 **加 (+)** 或 **减 (-)**
4. 选择 **当前帧** 或 **帧范围**
5. 点击 **Execute**

详见 `docs/bone-editor.md`。

## 面板一览

| 面板 | 顺序 | 姿态模式 | 说明 |
|------|------|---------|------|
| Bone Editor | 5 | 必须 | 骨骼变换增量编辑 |
| Import Mixamo FBX | 10 | 否 | FBX 导入 & Mixamo 骨骼创建 |
| Retarget | 20 | 否 | 骨骼选择、骨骼映射、约束 |
| Bake & Interpolate | 30 | 必须 | 烘焙、平滑、预测、补帧 |
| Presets | 40 | 否 | 保存/加载/导出/导入骨骼映射（以 `.json` 文件存储在 `presets/` 目录中） |

### 骨骼映射技巧

- 在视口（姿态模式）中选中骨骼后，点击 `→` 按钮自动填入源/目标骨骼名
- 在 3D 视口中选中骨骼时，对应的映射行会自动高亮（单向同步）

## 技术文档

- `docs/bone-editor.md` — 骨骼编辑器详细说明
- `docs/interpolation-system.md` — 补帧系统架构
- `docs/blender-51-fcurves-migration.md` — Blender 5.1 FCurves API 迁移
- `docs/faq.md` — 常见问题
- `docs/debug-notes.md` — 调试笔记

## 许可证

GPL-3.0-or-later — 详见 `LICENSE`。
