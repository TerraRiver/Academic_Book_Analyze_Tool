# TR_book_read_tool — 学术书籍阅读分析助手

面向学术研究人员的 PDF 智能分析桌面工具。自动化完成从 PDF 章节切分、OCR 解析、LLM 深度分析到生成结构化 Word 报告的完整流水线。

## 功能特性

- **PDF 章节管理**：自动读取 PDF 书签提取章节结构，支持手动编辑与删除
- **MinerU OCR 解析**：调用 MinerU API 对各章节 PDF 进行高质量解析，支持公式、表格识别；相同章节自动命中本地缓存，跳过重复解析
- **带页码 Markdown 转换**：将解析结果重组为带原书页码标注的 Markdown，便于溯源
- **LLM 深度分析**：支持 DeepSeek / Gemini / 自定义中转站，统一采用 OpenAI 兼容接口，支持并发分析，可配置并发数
- **Word 报告生成**：汇总所有章节分析结果，一键输出高可读性的 `.docx` 报告
- **状态追踪**：通过 `metadata.json` 精确追踪每本书每个章节的处理状态，支持断点续处理

## 处理流水线

```
上传 PDF
   ↓
读取书签 → 章节切分 → chapters_pdf/
   ↓
MinerU API 解析（自动缓存）→ MinerU_json/
   ↓
JSON → 带页码 Markdown → chapters_markdown/
   ↓
LLM 并发分析 → LLM_result/
   ↓
汇总 → Word 报告
```

## 环境要求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) 包管理器

## 安装与运行

```bash
# 克隆仓库
git clone <repo_url>
cd TR_book_read_tool

# 安装依赖
uv sync

# 配置 API Key（见下方"配置"章节）
cp keys.example.ini keys.ini
# 编辑 keys.ini，填入你的各项 API Key

# 运行程序
uv run python main.py

# WSL 环境下运行（需先安装 libxcb-cursor0）
# sudo apt install libxcb-cursor0
QT_QPA_PLATFORM=xcb uv run python main.py
```

## 打包为独立可执行文件

```bash
python build.py
```

打包完成后，可执行文件位于 `dist/` 目录，`config.ini`、`keys.ini` 和 `data/` 目录会自动复制到其旁边。

## 配置

配置分为两个文件：

| 文件 | 说明 | 是否提交 git |
|---|---|---|
| `config.ini` | 非敏感配置（URL、模型参数、Prompt 等） | ✅ |
| `keys.ini` | API Key（从 `keys.example.ini` 复制后填写） | ❌ 已 gitignore |

### keys.ini

```ini
[MinerU]
api_key = <your_mineru_api_key>

[DeepSeek]
api_key = <your_deepseek_api_key>

[Gemini]
api_key = <your_gemini_api_key>

[中转站]
api_key = <your_relay_api_key>
```

### config.ini 主要配置项

```ini
[MinerU]
base_url = https://mineru.net/api/v4
enable_ocr = True
enable_formula = True
enable_table = False
language = ch          # ch | en | auto
model_version = pipeline   # pipeline | vlm | MinerU-HTML
poll_interval = 15     # 轮询间隔（秒）
max_attempts = 60      # 最大轮询次数

[DeepSeek]
base_url = https://api.deepseek.com/v1
model_name = deepseek-chat

[Gemini]
base_url = https://generativelanguage.googleapis.com/v1beta/openai
model_name = gemini-2.5-pro

[中转站]
base_url = <your_relay_base_url>   # 任意 OpenAI 兼容中转地址

[LLM]
provider = DeepSeek         # DeepSeek | Gemini | 中转站
model_name = deepseek-chat
temperature = 0.2
max_tokens = 8000
max_concurrent_llm_calls = 5
prompt = <your_system_prompt>

[General]
report_output_path = C:/Users/YourName/Desktop
```

所有配置项也可在程序内通过「设置」对话框修改，保存时 API Key 自动写入 `keys.ini`，其余配置写入 `config.ini`。

## 数据目录结构

```
data/
└── <书籍组>/
    └── <书名>/
        ├── original.pdf
        ├── metadata.json          # 状态追踪文件
        ├── chapters_pdf/          # 按章节切分的 PDF
        ├── MinerU_json/           # MinerU 解析原始输出（含缓存哈希）
        ├── chapters_markdown/     # 带页码的 Markdown
        └── LLM_result/            # 每章 LLM 分析结果
```

## 项目结构

```
├── main.py                  # 程序入口
├── core/
│   ├── api_handler.py       # ConfigManager、LLMAPI、MinerUAPI、APIHandler
│   ├── book_manager.py      # 书籍组 CRUD、PDF 上传、metadata 读写
│   ├── pdf_processor.py     # 书签提取、按章节切分 PDF
│   ├── json_to_markdown.py  # MinerU JSON → 带页码 Markdown
│   └── report_generator.py  # LLM Markdown → Word 报告
├── ui/
│   ├── main_window.py       # 主窗口及所有 Worker 线程
│   └── settings_dialog.py   # 设置对话框
├── config.ini               # 非敏感配置（提交 git）
├── keys.ini                 # API Key（本地私有，已 gitignore）
├── keys.example.ini         # keys.ini 模板
├── build.py                 # 打包脚本
└── build_config.spec        # PyInstaller 配置
```

## 依赖

| 包 | 用途 |
|---|---|
| `PySide6` | GUI 框架 |
| `pypdf` | PDF 书签读取与页面切分 |
| `requests` | HTTP 请求（MinerU / LLM API） |
| `python-docx` | Word 报告生成 |
