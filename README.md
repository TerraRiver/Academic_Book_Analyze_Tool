# TR_book_read_tool

面向学术研究场景的 PDF 书籍阅读与分析桌面工具。它将整本书的处理流程串成一条流水线：

`PDF 章节整理 → OCR / 结构解析 → Markdown 转换 → LLM 分析 → Word 报告输出`

适合需要对学术著作、理论书、研究型材料做分章节阅读、摘录和结构化总结的场景。

## 功能概览

- **多级章节管理**
  - 自动读取 PDF 书签。
  - 支持 `L1 / L2 / L3` 三级章节结构。
  - 支持手动增删章节、调整层级、编辑起始页和结束页。
  - 标题可按层级自动编号：`第X章 / 第X节 / 第X目`。

- **按叶子章节切分**
  - 真正参与 PDF 切分、OCR、Markdown 转换和基础 LLM 分析的是最里层叶子章节。
  - 例如：
    - 如果某个 `L2` 下没有 `L3`，则这个 `L2` 是分析单元。
    - 如果某个 `L2` 下有 `L3`，则实际分析单元是这些 `L3`。

- **章节页码编辑更灵活**
  - 系统会提供默认结束页推算，但不会强制覆盖你手动修改过的结束页。
  - 多级目录下，父章节的默认结束页会跟随最后一个子孙章节的结束页。

- **MinerU OCR / 结构解析**
  - 支持公式、表格识别。
  - 对已处理过的章节自动命中本地缓存，避免重复调用。

- **带页码 Markdown 输出**
  - 将解析结果转换为带原书页码标记的 Markdown。
  - 便于后续溯源、人工检查和二次加工。

- **LLM 分析**
  - 兼容任意 OpenAI 兼容接口。
  - 支持并发分析。
  - 叶子章节分析日志会显示完整层级路径，便于定位。

- **父级章节补充分析**
  - 可选功能，默认开启。
  - 当存在多级章节时，会自动把下级叶子章节 Markdown 聚合后，再对父级章节做补充分析：
    - `L1`：输出整体摘要 + 作者思维逻辑链条
    - `L2`：输出整体摘要
  - 该功能可在设置中关闭。

- **层级化 Word 报告**
  - Word 报告按 `L1 / L2 / L3` 结构输出，不再只是叶子章节平铺。
  - 父级章节补充分析会插入到对应章节标题下。

- **状态追踪**
  - 通过 `metadata.json` 记录书籍处理状态和章节信息。
  - 支持断点续处理。

## 处理流程

```text
上传 PDF
  ↓
读取 PDF 书签并整理章节结构
  ↓
按叶子章节切分 PDF → chapters_pdf/
  ↓
MinerU 解析 → MinerU_json/
  ↓
JSON 转带页码 Markdown → chapters_markdown/
  ↓
LLM 分析
  ├─ 叶子章节分析
  └─ 父级章节补充分析（可开关）
      ↓
    LLM_result/
  ↓
按章节树生成 Word 报告
```

## 环境要求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)

## 安装与运行

```bash
git clone <repo_url>
cd TR_book_read_tool

uv sync

cp keys.example.ini keys.ini
# 填入你的 API Key

uv run python main.py
```

如果在 WSL 下运行 Qt 界面：

```bash
sudo apt install libxcb-cursor0
QT_QPA_PLATFORM=xcb uv run python main.py
```

## 打包

```bash
python build.py
```

打包后可执行文件位于 `dist/`。

## 配置说明

配置分为两个文件：

| 文件 | 用途 | 是否应提交 |
|---|---|---|
| `config.ini` | 非敏感配置：URL、模型参数、Prompt、功能开关等 | 是 |
| `keys.ini` | API Key | 否 |

### keys.ini

```ini
[MinerU]
api_key = <your_mineru_api_key>

[LLM]
api_key = <your_llm_api_key>
```

### config.ini 关键项

```ini
[MinerU]
base_url = https://mineru.net/api/v4
enable_ocr = True
enable_formula = True
enable_table = False
language = ch
model_version = pipeline
poll_interval = 15
max_attempts = 60

[LLM]
base_url = https://api.deepseek.com/v1
model_name = deepseek-chat
temperature = 0.2
max_tokens = 8000
max_concurrent_llm_calls = 5
enable_parent_summary_analysis = True
prompt = <your_system_prompt>

[General]
report_output_path = C:/Users/YourName/Desktop
```

说明：

- `prompt` 用于叶子章节分析。
- `enable_parent_summary_analysis` 控制是否启用父级章节补充分析，默认 `True`。
- 父级章节补充分析所用 prompt 写在代码中，不在设置页暴露编辑。

## 设置页

程序内可通过“设置”对话框修改配置，当前支持：

- MinerU API 配置
- LLM API 配置
- 并发请求数
- 叶子章节分析 Prompt
- 父级章节补充分析开关
- Word 报告输出路径

保存后：

- API Key 写入 `keys.ini`
- 其他配置写入 `config.ini`

## 章节规则说明

### 1. 哪些章节会真正参与切分和分析

只有**叶子章节**会参与：

- PDF 切分
- MinerU 解析
- JSON 转 Markdown
- 叶子章节 LLM 分析

父章节本身不会单独切 PDF，但可以基于下级 Markdown 做聚合分析。

### 2. 结束页默认推算规则

- 叶子章节：默认取下一叶子章节起始页减 1，末尾叶子章节默认到文档总页数。
- 父章节：默认取最后一个子孙章节的结束页。
- 一旦手动修改结束页，后续自动推算不会强制覆盖。

### 3. 默认标题规则

- `L1`：`第X章`
- `L2`：`第X节`
- `L3`：`第X目`

编号规则：

- `L1` 全书递增。
- `L2` 在所属 `L1` 内从 1 开始。
- `L3` 在所属 `L2` 内从 1 开始。

## 输出目录结构

```text
data/
└── <书籍组>/
    └── <书名>/
        ├── original.pdf
        ├── metadata.json
        ├── chapters_pdf/
        ├── MinerU_json/
        ├── chapters_markdown/
        └── LLM_result/
```

其中：

- `chapters_pdf/`：按叶子章节切分后的 PDF
- `chapters_markdown/`：叶子章节 Markdown
- `LLM_result/`：
  - `01_analysis.md`、`02_analysis.md`：叶子章节分析结果
  - `parent_XX_analysis.md`：父级章节补充分析结果

## Word 报告说明

最终 Word 报告按章节层级组织：

- `L1 / L2 / L3` 保留结构标题
- 叶子章节正文分析写在对应叶子标题下
- 父级章节补充分析写在对应父级标题下

因此最终报告会同时体现：

- 书籍章节树结构
- 最里层分析单元的详细内容
- 外层章节的整体摘要 / 逻辑链条

## 项目结构

```text
main.py
core/
├── api_handler.py
├── book_manager.py
├── json_to_markdown.py
├── pdf_processor.py
└── report_generator.py
ui/
├── main_window.py
└── settings_dialog.py
config.ini
keys.ini
keys.example.ini
build.py
build_config.spec
```

## 主要依赖

| 依赖 | 用途 |
|---|---|
| `PySide6` | GUI |
| `pypdf` | PDF 书签读取与切分 |
| `requests` | 调用 MinerU / LLM API |
| `python-docx` | 生成 Word 报告 |

