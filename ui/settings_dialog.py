import sys
import os
import configparser
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QTabWidget,
    QWidget,
    QFormLayout,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QMessageBox,
    QGroupBox,
    QFileDialog
)

DEFAULT_MINERU_BASE_URL = "https://mineru.net/api/v4"
DEFAULT_MINERU_LANGUAGE = "ch"
MINERU_LANGUAGE_OPTIONS = ["ch", "en", "auto"]
DEFAULT_MINERU_MODEL_VERSION = "pipeline"
MINERU_MODEL_VERSION_OPTIONS = ["pipeline", "vlm", "MinerU-HTML"]
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_ZENMUX_BASE_URL = "https://zenmux.ai/api/v1"
DEFAULT_ZENMUX_MODEL_NAME = "google/gemini-3.1-pro-preview"
ZENMUX_MODEL_OPTIONS = [
    "gemini-3.1-pro-preview",
]


def normalize_mineru_language(language: str) -> str:
    """兼容旧配置中的zh值。"""
    normalized = (language or DEFAULT_MINERU_LANGUAGE).strip().lower()
    if normalized == "zh":
        return DEFAULT_MINERU_LANGUAGE
    if normalized in MINERU_LANGUAGE_OPTIONS:
        return normalized
    return DEFAULT_MINERU_LANGUAGE


def normalize_mineru_model_version(model_version: str) -> str:
    """兼容空值或历史配置中的无效模型版本。"""
    normalized = (model_version or DEFAULT_MINERU_MODEL_VERSION).strip()
    if normalized in MINERU_MODEL_VERSION_OPTIONS:
        return normalized
    return DEFAULT_MINERU_MODEL_VERSION


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(600, 500)
        
        self.config_file = "config.ini"
        self.keys_file = "keys.ini"
        self.config = configparser.ConfigParser()
        self.keys_config = configparser.ConfigParser()

        self.init_ui()
        self.setup_styles()
        self.load_settings()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 通用设置标签页
        self.create_general_tab()
        
        # MinerU设置标签页
        self.create_mineru_tab()
        
        # LLM设置标签页
        self.create_llm_tab()
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.test_connections)
        
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_settings)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.test_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)

    def setup_styles(self):
        """设置对话框专用样式，避免受主窗口全局样式影响。"""
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
                color: #1a202c;
            }

            QLabel {
                color: #2d3748;
                font-size: 13px;
                font-weight: 600;
            }

            QTabWidget::pane {
                background-color: #ffffff;
                border: 1px solid #d9e2ec;
                border-radius: 12px;
                margin-top: 8px;
            }
            QTabBar::tab {
                background-color: #e9eef5;
                color: #4a5568;
                border: 1px solid #d9e2ec;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 10px 18px;
                margin-right: 6px;
                min-width: 96px;
                font-size: 13px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #1a202c;
            }
            QTabBar::tab:hover {
                background-color: #dde6f0;
                color: #1a202c;
            }

            QGroupBox {
                background-color: #ffffff;
                color: #1a202c;
                border: 1px solid #d9e2ec;
                border-radius: 12px;
                margin-top: 12px;
                padding: 16px 14px 14px 14px;
                font-size: 13px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #2d3748;
                background-color: #f8fafc;
            }

            QLineEdit, QTextEdit, QComboBox, QAbstractSpinBox {
                background-color: #ffffff;
                color: #1a202c;
                border: 1px solid #cbd5e0;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 13px;
                selection-background-color: #bee3f8;
                selection-color: #1a202c;
            }
            QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QAbstractSpinBox:hover {
                border-color: #a0aec0;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QAbstractSpinBox:focus {
                border-color: #3182ce;
            }
            QTextEdit {
                background-color: #fcfdff;
            }

            QComboBox {
                padding-right: 32px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
                width: 26px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #4a5568;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #1a202c;
                border: 1px solid #d9e2ec;
                border-radius: 8px;
                padding: 4px;
                selection-background-color: #d9f3ee;
                selection-color: #1a202c;
                outline: 0;
            }
            QComboBox QAbstractItemView::item {
                min-height: 28px;
                padding: 6px 10px;
                color: #1a202c;
                background-color: #ffffff;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #edf2f7;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #bfeee2;
                color: #1a202c;
            }

            QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
                width: 18px;
                border: none;
                background: transparent;
            }

            QCheckBox {
                color: #2d3748;
                spacing: 8px;
                font-size: 13px;
                font-weight: 500;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #a0aec0;
                border-radius: 5px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #319795;
                border-color: #319795;
            }

            QPushButton {
                background-color: #2b6cb0;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 600;
                min-height: 18px;
            }
            QPushButton:hover {
                background-color: #2c5282;
            }
            QPushButton:pressed {
                background-color: #1a365d;
            }

            QMessageBox {
                background-color: #ffffff;
                color: #1a202c;
            }
        """)
    
    def create_mineru_tab(self):
        """创建MinerU设置标签页"""
        mineru_widget = QWidget()
        layout = QVBoxLayout(mineru_widget)
        
        # API配置组
        api_group = QGroupBox("API配置")
        api_layout = QFormLayout(api_group)
        
        self.mineru_api_key = QLineEdit()
        self.mineru_api_key.setEchoMode(QLineEdit.Password)
        self.mineru_api_key.setPlaceholderText("请输入MinerU API Key")
        api_layout.addRow("API Key:", self.mineru_api_key)
        
        self.mineru_base_url = QLineEdit()
        self.mineru_base_url.setPlaceholderText(DEFAULT_MINERU_BASE_URL)
        self.mineru_base_url.setText(DEFAULT_MINERU_BASE_URL)
        api_layout.addRow("Base URL:", self.mineru_base_url)
        
        layout.addWidget(api_group)
        
        # 解析选项组
        options_group = QGroupBox("解析选项")
        options_layout = QFormLayout(options_group)
        
        self.enable_ocr = QCheckBox("启用OCR识别")
        self.enable_ocr.setChecked(True)
        options_layout.addRow("OCR:", self.enable_ocr)
        
        self.enable_formula = QCheckBox("启用公式识别")
        self.enable_formula.setChecked(True)
        options_layout.addRow("公式识别:", self.enable_formula)
        
        self.enable_table = QCheckBox("启用表格识别")
        self.enable_table.setChecked(True)
        options_layout.addRow("表格识别:", self.enable_table)
        
        self.language = QComboBox()
        self.language.addItems(MINERU_LANGUAGE_OPTIONS)
        self.language.setCurrentText(DEFAULT_MINERU_LANGUAGE)
        options_layout.addRow("文档语言:", self.language)

        self.model_version = QComboBox()
        self.model_version.addItems(MINERU_MODEL_VERSION_OPTIONS)
        self.model_version.setCurrentText(DEFAULT_MINERU_MODEL_VERSION)
        self.model_version.setToolTip("PDF 推荐使用 pipeline 或 vlm；HTML 文件需使用 MinerU-HTML")
        options_layout.addRow("模型版本:", self.model_version)
        
        layout.addWidget(options_group)
        
        # 高级设置组
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QFormLayout(advanced_group)
        
        self.poll_interval = QSpinBox()
        self.poll_interval.setRange(5, 60)
        self.poll_interval.setValue(10)
        self.poll_interval.setSuffix(" 秒")
        advanced_layout.addRow("轮询间隔:", self.poll_interval)
        
        self.max_attempts = QSpinBox()
        self.max_attempts.setRange(10, 200)
        self.max_attempts.setValue(60)
        advanced_layout.addRow("最大尝试次数:", self.max_attempts)
        
        layout.addWidget(advanced_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(mineru_widget, "MinerU设置")
    
    def create_llm_tab(self):
        """创建LLM设置标签页"""
        llm_widget = QWidget()
        layout = QVBoxLayout(llm_widget)

        # 模型提供商配置组
        provider_group = QGroupBox("模型提供商 (LLM Provider)")
        provider_layout = QFormLayout(provider_group)

        self.llm_provider_combo = QComboBox()
        self.llm_provider_combo.addItems(["DeepSeek", "Gemini", "中转站"])
        self.llm_provider_combo.currentTextChanged.connect(self._on_llm_provider_changed)
        provider_layout.addRow("选择模型提供商:", self.llm_provider_combo)

        # DeepSeek API Key (initially hidden)
        self.deepseek_api_key_label = QLabel("DeepSeek API Key:")
        self.deepseek_api_key = QLineEdit()
        self.deepseek_api_key.setEchoMode(QLineEdit.Password)
        self.deepseek_api_key.setPlaceholderText("请输入DeepSeek API Key")
        provider_layout.addRow(self.deepseek_api_key_label, self.deepseek_api_key)

        # Gemini API Key (initially hidden)
        self.gemini_api_key_label = QLabel("Gemini API Key:")
        self.gemini_api_key = QLineEdit()
        self.gemini_api_key.setEchoMode(QLineEdit.Password)
        self.gemini_api_key.setPlaceholderText("请输入Gemini API Key")
        provider_layout.addRow(self.gemini_api_key_label, self.gemini_api_key)

        # Zenmux API Key (initially hidden)
        self.zenmux_api_key_label = QLabel("中转站 API Key:")
        self.zenmux_api_key = QLineEdit()
        self.zenmux_api_key.setEchoMode(QLineEdit.Password)
        self.zenmux_api_key.setPlaceholderText("请输入中转站 API Key")
        provider_layout.addRow(self.zenmux_api_key_label, self.zenmux_api_key)

        self.llm_base_url = QLineEdit()
        self.llm_base_url.setPlaceholderText("将根据模型提供商自动填充")
        provider_layout.addRow("Base URL:", self.llm_base_url)

        self.llm_model_name = QComboBox()
        self.llm_model_name.setEditable(True)
        provider_layout.addRow("模型名称:", self.llm_model_name)

        layout.addWidget(provider_group)
        
        # 模型参数组
        params_group = QGroupBox("模型参数")
        params_layout = QFormLayout(params_group)
        
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(0.7)
        params_layout.addRow("Temperature:", self.temperature)
        
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(100, 8000)
        self.max_tokens.setValue(2000)
        params_layout.addRow("Max Tokens:", self.max_tokens)

        self.max_concurrent_llm_calls = QSpinBox()
        self.max_concurrent_llm_calls.setRange(1, 20) # Set a reasonable range for concurrency
        self.max_concurrent_llm_calls.setValue(5) # Default value
        params_layout.addRow("最大并发请求数:", self.max_concurrent_llm_calls)
        
        layout.addWidget(params_group)
        
        # 提示词设置组
        prompt_group = QGroupBox("分析提示词")
        prompt_layout = QVBoxLayout(prompt_group)
        
        prompt_label = QLabel("系统提示词（用于指导AI分析章节内容）:")
        prompt_layout.addWidget(prompt_label)
        
        self.system_prompt = QTextEdit()
        self.system_prompt.setPlaceholderText("请输入用于分析章节的系统提示词...")
        default_prompt = """你是一个专业的学术文献分析助手。请仔细分析提供的章节内容，并按照以下要求进行总结：

1. 提取章节的核心观点和主要论述
2. 识别关键概念、理论和方法
3. 总结重要的数据、案例或实证证据
4. 指出作者的主要结论和建议
5. 标注重要信息的页码位置

请保持客观、准确，并确保分析结果结构清晰、逻辑严密。"""
        self.system_prompt.setPlainText(default_prompt)
        self.system_prompt.setMaximumHeight(150)
        prompt_layout.addWidget(self.system_prompt)
        
        layout.addWidget(prompt_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(llm_widget, "LLM设置")

    def create_general_tab(self):
        """创建通用设置标签页"""
        general_widget = QWidget()
        layout = QVBoxLayout(general_widget)

        # 报告输出路径组
        report_group = QGroupBox("报告设置")
        report_layout = QFormLayout(report_group)

        # 创建一个水平布局来放置输入框和按钮
        path_layout = QHBoxLayout()
        self.report_output_path = QLineEdit()
        self.report_output_path.setPlaceholderText("默认为书籍所在目录")
        path_layout.addWidget(self.report_output_path)

        self.select_path_button = QPushButton("选择...")
        self.select_path_button.clicked.connect(self.select_report_path)
        path_layout.addWidget(self.select_path_button)

        report_layout.addRow("Word报告输出路径:", path_layout)
        
        layout.addWidget(report_group)
        layout.addStretch()
        
        self.tab_widget.insertTab(0, general_widget, "通用设置")

    def select_report_path(self):
        """选择报告输出路径"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择文件夹",
            self.report_output_path.text() or os.getcwd()
        )
        if directory:
            self.report_output_path.setText(directory)

    def _on_llm_provider_changed(self, provider):
        """当LLM提供商变化时更新UI"""
        is_deepseek = provider == "DeepSeek"
        is_gemini = provider == "Gemini"
        is_zenmux = provider == "中转站"

        # 控制API Key输入框的可见性
        self.deepseek_api_key_label.setVisible(is_deepseek)
        self.deepseek_api_key.setVisible(is_deepseek)
        self.gemini_api_key_label.setVisible(is_gemini)
        self.gemini_api_key.setVisible(is_gemini)
        self.zenmux_api_key_label.setVisible(is_zenmux)
        self.zenmux_api_key.setVisible(is_zenmux)

        # 更新URL和模型列表
        self.llm_model_name.clear()
        if is_deepseek:
            self.llm_base_url.setText(self.config.get('DeepSeek', 'base_url', fallback=DEFAULT_DEEPSEEK_BASE_URL))
            self.llm_model_name.addItems(["deepseek-chat"])
            self.llm_model_name.setCurrentText(self.config.get('LLM', 'model_name', fallback='deepseek-chat'))
        elif is_gemini:
            self.llm_base_url.setText(self.config.get('Gemini', 'base_url', fallback=DEFAULT_GEMINI_BASE_URL))
            self.llm_model_name.addItems(["gemini-2.5-pro","gemini-2.5-flash"])
            self.llm_model_name.setCurrentText(self.config.get('LLM', 'model_name', fallback='gemini-2.5-flash'))
        elif is_zenmux:
            self.llm_base_url.setText(self.config.get('中转站', 'base_url', fallback=DEFAULT_ZENMUX_BASE_URL))
            self.llm_model_name.addItems(ZENMUX_MODEL_OPTIONS)
            self.llm_model_name.setCurrentText(
                self.config.get('LLM', 'model_name', fallback=DEFAULT_ZENMUX_MODEL_NAME)
            )
    
    def _get_api_key(self, section: str) -> str:
        """从 keys.ini 读取 API Key，若不存在则回退到 config.ini（兼容旧配置）。"""
        key = self.keys_config.get(section, 'api_key', fallback='')
        if not key:
            key = self.config.get(section, 'api_key', fallback='')
        return key

    def load_settings(self):
        """从配置文件加载设置"""
        if not os.path.exists(self.config_file):
            self._on_llm_provider_changed(self.llm_provider_combo.currentText())
            return

        self.config.read(self.config_file, encoding='utf-8')
        self.keys_config.read(self.keys_file, encoding='utf-8')

        # 加载通用设置
        if self.config.has_section('General'):
            general_section = self.config['General']
            self.report_output_path.setText(general_section.get('report_output_path', ''))
        
        # 加载MinerU设置
        if self.config.has_section('MinerU'):
            mineru_section = self.config['MinerU']
            self.mineru_api_key.setText(self._get_api_key('MinerU'))
            self.mineru_base_url.setText(mineru_section.get('base_url', DEFAULT_MINERU_BASE_URL))
            self.enable_ocr.setChecked(mineru_section.getboolean('enable_ocr', True))
            self.enable_formula.setChecked(mineru_section.getboolean('enable_formula', True))
            self.enable_table.setChecked(mineru_section.getboolean('enable_table', True))
            self.language.setCurrentText(
                normalize_mineru_language(mineru_section.get('language', DEFAULT_MINERU_LANGUAGE))
            )
            self.model_version.setCurrentText(
                normalize_mineru_model_version(
                    mineru_section.get('model_version', DEFAULT_MINERU_MODEL_VERSION)
                )
            )
            self.poll_interval.setValue(mineru_section.getint('poll_interval', 10))
            self.max_attempts.setValue(mineru_section.getint('max_attempts', 60))
        
        # 加载LLM提供商的独立设置
        self.deepseek_api_key.setText(self._get_api_key('DeepSeek'))
        self.gemini_api_key.setText(self._get_api_key('Gemini'))
        self.zenmux_api_key.setText(self._get_api_key('中转站'))

        # 加载LLM通用设置
        if self.config.has_section('LLM'):
            llm_section = self.config['LLM']
            provider = llm_section.get('provider', 'DeepSeek')
            self.llm_provider_combo.setCurrentText(provider)
            
            # 手动触发一次更新，以确保UI状态正确
            self._on_llm_provider_changed(provider)
            
            self.llm_model_name.setCurrentText(llm_section.get('model_name', 'deepseek-chat'))
            self.temperature.setValue(llm_section.getfloat('temperature', 0.7))
            self.max_tokens.setValue(llm_section.getint('max_tokens', 2000))
            prompt = llm_section.get('prompt', '')
            if prompt:
                self.system_prompt.setPlainText(prompt)
            self.max_concurrent_llm_calls.setValue(llm_section.getint('max_concurrent_llm_calls', 5))
        else:
            # 如果没有LLM部分，手动触发默认值
            self._on_llm_provider_changed(self.llm_provider_combo.currentText())
    
    def save_settings(self):
        """保存设置到配置文件"""
        # 确保配置文件有必要的节
        for section in ['General', 'MinerU', 'DeepSeek', 'Gemini', '中转站', 'LLM']:
            if not self.config.has_section(section):
                self.config.add_section(section)

        # 保存通用设置
        self.config['General']['report_output_path'] = self.report_output_path.text()
        
        # 保存MinerU设置
        mineru_section = self.config['MinerU']
        mineru_section['base_url'] = self.mineru_base_url.text().strip() or DEFAULT_MINERU_BASE_URL
        mineru_section['enable_ocr'] = str(self.enable_ocr.isChecked())
        mineru_section['enable_formula'] = str(self.enable_formula.isChecked())
        mineru_section['enable_table'] = str(self.enable_table.isChecked())
        mineru_section['language'] = normalize_mineru_language(self.language.currentText())
        mineru_section['model_version'] = normalize_mineru_model_version(self.model_version.currentText())
        mineru_section['poll_interval'] = str(self.poll_interval.value())
        mineru_section['max_attempts'] = str(self.max_attempts.value())
        
        # API Key 单独保存到 keys.ini（不写入 config.ini）
        for section in ['MinerU', 'DeepSeek', 'Gemini', '中转站']:
            if not self.keys_config.has_section(section):
                self.keys_config.add_section(section)
        self.keys_config['MinerU']['api_key'] = self.mineru_api_key.text().strip()
        self.keys_config['DeepSeek']['api_key'] = self.deepseek_api_key.text().strip()
        self.keys_config['Gemini']['api_key'] = self.gemini_api_key.text().strip()
        self.keys_config['中转站']['api_key'] = self.zenmux_api_key.text().strip()
        
        # 根据当前选择保存URL
        provider = self.llm_provider_combo.currentText()
        if provider == "DeepSeek":
            self.config['DeepSeek']['base_url'] = self.llm_base_url.text().strip() or DEFAULT_DEEPSEEK_BASE_URL
        elif provider == "Gemini":
            self.config['Gemini']['base_url'] = self.llm_base_url.text().strip() or DEFAULT_GEMINI_BASE_URL
        elif provider == "中转站":
            self.config['中转站']['base_url'] = self.llm_base_url.text().strip() or DEFAULT_ZENMUX_BASE_URL

        # 保存LLM通用设置
        llm_section = self.config['LLM']
        llm_section['provider'] = self.llm_provider_combo.currentText()
        llm_section['model_name'] = self.llm_model_name.currentText()
        llm_section['temperature'] = str(self.temperature.value())
        llm_section['max_tokens'] = str(self.max_tokens.value())
        llm_section['prompt'] = self.system_prompt.toPlainText()
        llm_section['max_concurrent_llm_calls'] = str(self.max_concurrent_llm_calls.value())
        
        # 写入文件
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            with open(self.keys_file, 'w', encoding='utf-8') as f:
                self.keys_config.write(f)
            QMessageBox.information(self, "成功", "设置已保存")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存设置失败：{str(e)}")
    
    def test_connections(self):
        """测试API连接"""
        # 这里可以添加实际的连接测试逻辑
        QMessageBox.information(self, "测试连接", "连接测试功能将在后续版本中实现")
    
    def get_mineru_config(self):
        """获取MinerU配置"""
        return {
            'api_key': self.mineru_api_key.text(),
            'base_url': self.mineru_base_url.text(),
            'enable_ocr': self.enable_ocr.isChecked(),
            'enable_formula': self.enable_formula.isChecked(),
            'enable_table': self.enable_table.isChecked(),
            'language': self.language.currentText(),
            'model_version': self.model_version.currentText(),
            'poll_interval': self.poll_interval.value(),
            'max_attempts': self.max_attempts.value()
        }
    
    def get_deepseek_config(self):
        """获取DeepSeek配置"""
        return {
            'api_key': self.deepseek_api_key.text(),
            'base_url': self.llm_base_url.text(),
            'model_name': self.llm_model_name.currentText(),
            'temperature': self.temperature.value(),
            'max_tokens': self.max_tokens.value()
        }
    
    def get_llm_config(self):
        """获取LLM配置"""
        return {
            'prompt': self.system_prompt.toPlainText(),
            'max_concurrent_llm_calls': self.max_concurrent_llm_calls.value()
        }


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = SettingsDialog()
    dialog.show()
    sys.exit(app.exec())
