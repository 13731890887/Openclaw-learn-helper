# OpenClaw Learn Helper

[English](./README.md)

## 1. 定位

`OpenClaw Learn Helper` 是一个面向智能体使用的本地学习辅助项目。当前实现形态更接近一个运行在 macOS 上的 `skill / plugin-style workflow`，核心职责是把“截图中的学习内容”转成“可继续处理的结构化文本和简要学习分析”。

它当前不是一个跨平台通用插件包，也不是一个完整的 OpenClaw 官方插件发布物。  
当前版本只保证 **macOS** 工作流可用，**不确保 Windows 可用**。

## 2. 目标

本项目当前阶段的目标是：

- 让智能体或用户通过快捷键快速截图
- 在 OCR 前先压缩图片，降低运行时内存占用
- 提取题干、材料或笔记中的文字
- 输出适合学习场景继续处理的结构化结果
- 给出一段轻量、hint-first 的学习分析

## 3. 当前能力边界

### 3.1 已实现

- macOS 交互式截图
- 截图后自动缩放
- PaddleOCR 文字识别
- 简单题型判断
- 学科粗分类
- 轻量学习分析
- 终端可读输出
- JSON 结果落盘
- 通过快捷指令/热键触发

### 3.2 暂未实现

- 真正的 LLM 深度解题
- OpenClaw 官方 skill / plugin 打包与分发
- Windows 端兼容保证
- 稳定的 GUI 进度条或原生结果窗口
- 完整错题本自动写回

## 4. 运行环境约束

### 4.1 支持平台

- `macOS`: 当前支持并已验证
- `Windows`: 当前不保证可用
- `Linux`: 当前未验证

### 4.2 依赖

- Python 虚拟环境：`.venv`
- `paddleocr`
- `paddlepaddle`
- `Pillow`
- `mss` 可选，仅实时 OCR 路径可能使用

### 4.3 系统权限

运行截图链路需要：

- 屏幕录制权限
- 对触发方的权限放行
  例如 `Shortcuts`、`Terminal`、`iTerm` 或你实际使用的启动器

## 5. 工作流规范

### 5.1 主工作流

标准调用链：

1. 用户或智能体触发热键
2. macOS 进入交互截图
3. 截图保存到本地临时路径
4. 图片按内存策略缩放
5. 运行 OCR
6. 进行轻量学习分析
7. 生成终端输出和 JSON 结果

### 5.2 主入口

- Shell 启动器：`study-companion/scripts/run_snap_question.sh`
- Python 工作流：`study-companion/scripts/snap_question.py`
- OCR 解析器：`study-companion/scripts/ocr_parse.py`
- 实时 OCR：`study-companion/scripts/screen_ocr.py`

## 6. 输入输出规范

### 6.1 输入

支持两类输入：

- 交互截图
- 已存在的图片文件

### 6.2 输出

每次截图运行会在 `memory/snaps/` 下生成：

- `*-scaled.png`
- `*-analysis.json`

### 6.3 JSON 输出结构

结果 JSON 主要包含：

- `image`
  截图尺寸、缩放尺寸、内存模式、文件路径
- `ocr`
  OCR 行结果、置信度、完整文本、结构化分类
- `analysis`
  学科判断、题型判断、简要分析、学习提示、下一步建议

## 7. 内存与压缩策略

这个项目降低内存占用的主要手段不是“压缩 PNG 文件大小”，而是“在 OCR 前先降低图片分辨率”。

当前支持的模式：

- `auto`
- `low`
- `balanced`
- `high`

### 7.1 动态模式

`auto` 模式会先读取当前机器的可用内存，再决定压缩档位：

- 可用内存较低：优先缩小图片
- 可用内存中等：使用平衡尺寸
- 可用内存较高：保留更多细节

### 7.2 当前默认行为

当前默认启动器使用：

- `--memory-mode auto`
- 并叠加最大尺寸上限

这意味着即使当前可用内存较高，也不会无限放大 OCR 输入图像。

## 8. 状态与目录规范

### 8.1 源码目录

- `study-companion/scripts/`
- `study-companion/references/`
- `study-companion/data/`
- `study-companion/SKILL.md`

### 8.2 运行态目录

- `memory/`
- `memory/snaps/`

这些目录默认视为本地状态或生成产物，不应作为稳定源码的一部分提交。

## 9. 智能体阅读规则

如果一个智能体要接手这个仓库，应优先遵守下面这些规则：

- 这是一个学习场景项目，不是通用 OCR demo
- 优先走“截图后分析”，不要默认切到全屏持续 OCR
- 先保留本地优先原则，再考虑外部服务接入
- OCR 结果不确定时，要显式提示置信度风险
- 分析输出优先 hint-first，不要默认直接给完整答案
- 不要默认提交 `memory/` 下的生成截图和 JSON 结果
- macOS 集成链路可以继续迭代，Windows 兼容性不要擅自承诺

## 10. 与 OpenClaw 的关系

当前仓库更适合作为：

- OpenClaw 的本地 skill 原型
- OpenClaw 的外部辅助工作流
- 一个未来可被插件化封装的学习 OCR 子系统

当前还不是：

- 官方标准插件格式
- 完整可安装的 OpenClaw Marketplace 插件
- 已完成跨平台适配的通用组件

## 11. 推荐扩展方向

优先级较高的下一步包括：

- 增加截图后的进度展示
- 增加更强的题型结构化
- 接入 LLM / OpenClaw agent 做更深层分析
- 自动把题目写入错题本或复习队列
- 把当前工作流整理成正式的 OpenClaw skill / plugin spec

## 12. 快速启动

### 12.1 快捷键工作流

```bash
cd /Users/seqi/projects/Openclaw-learn-helper
bash study-companion/scripts/run_snap_question.sh
```

### 12.2 使用已有图片测试

```bash
cd /Users/seqi/projects/Openclaw-learn-helper
source .venv/bin/activate
python study-companion/scripts/snap_question.py --input /path/to/image.png
```

### 12.3 实时 OCR

```bash
cd /Users/seqi/projects/Openclaw-learn-helper
source .venv/bin/activate
python study-companion/scripts/screen_ocr.py --interval 1.0 --show-empty
```
