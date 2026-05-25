# TransPic

截图翻译 + 考研英语解析工具。框选屏幕上的英文文字，通过大模型识别并翻译，同时给出考研重点词汇解析。

## 功能

- **截图翻译**：按 `Alt+Shift+T` 或点击桌面宠物，框选区域即可翻译
- **考研模式**：输出原文、标准中文翻译、考研重点词汇（含音标）
- **桌面宠物**：可爱的悬浮小宠物，拖拽移动，翻译面板跟随
- **多模型支持**：兼容所有 OpenAI 接口格式的视觉大模型

## 安装

```bash
git clone https://github.com/BruceLi007/TransPic.git
cd TransPic
pip install -r requirements.txt
```

## 配置

首次运行后右键系统托盘图标 → 设置：

| 配置项 | 说明 | 示例 |
|---|---|---|
| Endpoint | API 完整地址 | `https://api.siliconflow.cn/v1/chat/completions` |
| API Key | 密钥 | `sk-xxxxxxxx` |
| Model | 视觉模型名称 | `Qwen/Qwen3-VL-8B-Instruct` |
| 热键 | 全局截图快捷键 | `alt+shift+t` |

## 使用

```bash
python main.py
```

1. 按全局热键或点击桌面上的小宠物
2. 鼠标框选屏幕上的英文文字区域
3. 弹出确认工具条 → 点击 ✓ 确认
4. 翻译结果面板在宠物上方显示

## 依赖

- PySide6 ≥ 6.5.0
- mss ≥ 9.0.0
- Pillow ≥ 10.0.0
- httpx ≥ 0.25.0
- keyboard ≥ 0.13.5
- pyperclip ≥ 1.8.2

## 项目结构

```
TransPic/
├── main.py                     # 入口，主控制器，热键桥接，翻译线程
├── app/
│   ├── pet_widget.py           # 桌面宠物
│   ├── screenshot_overlay.py   # 全屏截图覆盖层
│   ├── bubble_widget.py        # 翻译结果面板
│   ├── llm_client.py           # LLM API 客户端
│   ├── settings_dialog.py      # 设置弹窗
│   └── tray_manager.py         # 系统托盘
├── utils/
│   └── config.py               # 配置持久化
└── requirements.txt
```
