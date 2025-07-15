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


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(600, 500)
        
        self.config_file = "config.ini"
        self.config = configparser.ConfigParser()
        
        self.init_ui()
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
        self.mineru_base_url.setPlaceholderText("https://api.mineru.com")
        self.mineru_base_url.setText("https://api.mineru.com")
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
        self.language.addItems(["ch", "en", "auto"])
        self.language.setCurrentText("ch")
        options_layout.addRow("文档语言:", self.language)
        
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
        
        # DeepSeek API配置组
        api_group = QGroupBox("DeepSeek API配置")
        api_layout = QFormLayout(api_group)
        
        self.deepseek_api_key = QLineEdit()
        self.deepseek_api_key.setEchoMode(QLineEdit.Password)
        self.deepseek_api_key.setPlaceholderText("请输入DeepSeek API Key")
        api_layout.addRow("API Key:", self.deepseek_api_key)
        
        self.deepseek_base_url = QLineEdit()
        self.deepseek_base_url.setPlaceholderText("https://api.deepseek.com")
        self.deepseek_base_url.setText("https://api.deepseek.com")
        api_layout.addRow("Base URL:", self.deepseek_base_url)
        
        self.model_name = QComboBox()
        self.model_name.setEditable(True)
        self.model_name.addItems([
            "deepseek-chat",
            "deepseek-coder",
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo"
        ])
        self.model_name.setCurrentText("deepseek-chat")
        api_layout.addRow("模型名称:", self.model_name)
        
        layout.addWidget(api_group)
        
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
    
    def load_settings(self):
        """从配置文件加载设置"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')

            # 加载通用设置
            if self.config.has_section('General'):
                general_section = self.config['General']
                self.report_output_path.setText(general_section.get('report_output_path', ''))
            
            # 加载MinerU设置
            if self.config.has_section('MinerU'):
                mineru_section = self.config['MinerU']
                self.mineru_api_key.setText(mineru_section.get('api_key', ''))
                self.mineru_base_url.setText(mineru_section.get('base_url', 'https://api.mineru.com'))
                self.enable_ocr.setChecked(mineru_section.getboolean('enable_ocr', True))
                self.enable_formula.setChecked(mineru_section.getboolean('enable_formula', True))
                self.enable_table.setChecked(mineru_section.getboolean('enable_table', True))
                self.language.setCurrentText(mineru_section.get('language', 'zh'))
                self.poll_interval.setValue(mineru_section.getint('poll_interval', 10))
                self.max_attempts.setValue(mineru_section.getint('max_attempts', 60))
            
            # 加载DeepSeek设置
            if self.config.has_section('DeepSeek'):
                deepseek_section = self.config['DeepSeek']
                self.deepseek_api_key.setText(deepseek_section.get('api_key', ''))
                self.deepseek_base_url.setText(deepseek_section.get('base_url', 'https://api.deepseek.com'))
                self.model_name.setCurrentText(deepseek_section.get('model_name', 'deepseek-chat'))
                self.temperature.setValue(deepseek_section.getfloat('temperature', 0.7))
                self.max_tokens.setValue(deepseek_section.getint('max_tokens', 2000))
            
            # 加载LLM设置
            if self.config.has_section('LLM'):
                llm_section = self.config['LLM']
                prompt = llm_section.get('prompt', '')
                if prompt:
                    self.system_prompt.setPlainText(prompt)
                self.max_concurrent_llm_calls.setValue(llm_section.getint('max_concurrent_llm_calls', 5))
    
    def save_settings(self):
        """保存设置到配置文件"""
        # 确保配置文件有必要的节
        if not self.config.has_section('General'):
            self.config.add_section('General')
        if not self.config.has_section('MinerU'):
            self.config.add_section('MinerU')
        if not self.config.has_section('DeepSeek'):
            self.config.add_section('DeepSeek')
        if not self.config.has_section('LLM'):
            self.config.add_section('LLM')

        # 保存通用设置
        general_section = self.config['General']
        general_section['report_output_path'] = self.report_output_path.text()
        
        # 保存MinerU设置
        mineru_section = self.config['MinerU']
        mineru_section['api_key'] = self.mineru_api_key.text()
        mineru_section['base_url'] = self.mineru_base_url.text()
        mineru_section['enable_ocr'] = str(self.enable_ocr.isChecked())
        mineru_section['enable_formula'] = str(self.enable_formula.isChecked())
        mineru_section['enable_table'] = str(self.enable_table.isChecked())
        mineru_section['language'] = self.language.currentText()
        mineru_section['poll_interval'] = str(self.poll_interval.value())
        mineru_section['max_attempts'] = str(self.max_attempts.value())
        
        # 保存DeepSeek设置
        deepseek_section = self.config['DeepSeek']
        deepseek_section['api_key'] = self.deepseek_api_key.text()
        deepseek_section['base_url'] = self.deepseek_base_url.text()
        deepseek_section['model_name'] = self.model_name.currentText()
        deepseek_section['temperature'] = str(self.temperature.value())
        deepseek_section['max_tokens'] = str(self.max_tokens.value())
        
        # 保存LLM设置
        llm_section = self.config['LLM']
        llm_section['prompt'] = self.system_prompt.toPlainText()
        llm_section['max_concurrent_llm_calls'] = str(self.max_concurrent_llm_calls.value())
        
        # 写入文件
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
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
            'poll_interval': self.poll_interval.value(),
            'max_attempts': self.max_attempts.value()
        }
    
    def get_deepseek_config(self):
        """获取DeepSeek配置"""
        return {
            'api_key': self.deepseek_api_key.text(),
            'base_url': self.deepseek_base_url.text(),
            'model_name': self.model_name.currentText(),
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
