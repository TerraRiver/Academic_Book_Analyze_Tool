import sys
import os
import json
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QFileDialog,
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QDialog,
    QProgressBar,
    QStackedWidget, # Added for main content area
    QComboBox, # Added for book group selection
)
from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QIcon, QFont, QTextCursor
from core.book_manager import BookManager
from core.pdf_processor import get_bookmarks
from core.api_handler import APIHandler
from ui.settings_dialog import SettingsDialog


class MinerUWorker(QThread):
    """MinerU处理工作线程"""
    finished = Signal(bool)
    log_message = Signal(str)
    
    def __init__(self, book_path, chapters):
        super().__init__()
        self.book_path = book_path
        self.chapters = chapters
        self.api_handler = APIHandler()
    
    def run(self):
        """在后台线程中执行MinerU处理"""
        try:
            def log_callback(message):
                self.log_message.emit(message)
            
            success = self.api_handler.process_book_chapters(
                self.book_path, 
                self.chapters,
                log_callback=log_callback
            )
            
            self.finished.emit(success)
            
        except Exception as e:
            self.log_message.emit(f"MinerU处理过程中发生错误：{str(e)}")
            self.finished.emit(False)


class LLMAnalysisWorker(QThread):
    """LLM分析工作线程"""
    finished = Signal(bool)
    log_message = Signal(str)
    
    def __init__(self, book_path, chapters):
        super().__init__()
        self.book_path = book_path
        self.chapters = chapters
        self.api_handler = APIHandler()
    
    def run(self):
        """在后台线程中执行LLM分析"""
        try:
            def log_callback(message):
                self.log_message.emit(message)
            
            success = self.api_handler.analyze_chapters(
                self.book_path, 
                self.chapters,
                log_callback=log_callback
            )
            
            self.finished.emit(success)
            
        except Exception as e:
            self.log_message.emit(f"LLM分析过程中发生错误：{str(e)}")
            self.finished.emit(False)


class ReportGenerationWorker(QThread):
    """Word报告生成工作线程"""
    finished = Signal(bool, str)  # success, report_path
    log_message = Signal(str)
    
    def __init__(self, book_path):
        super().__init__()
        self.book_path = book_path
        self.book_manager = BookManager()
    
    def run(self):
        """在后台线程中执行Word报告生成"""
        try:
            def log_callback(message):
                self.log_message.emit(message)
            
            report_path = self.book_manager.generate_book_report(
                self.book_path,
                log_callback=log_callback
            )
            
            success = report_path is not None
            self.finished.emit(success, report_path or "")
            
        except Exception as e:
            self.log_message.emit(f"Word报告生成过程中发生错误：{str(e)}")
            self.finished.emit(False, "")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("国际关系研究阅读助手")
        self.setGeometry(100, 100, 1200, 800)

        self.book_manager = BookManager()
        self.current_book_path = None
        self.mineru_worker = None
        self.llm_worker = None
        self.report_worker = None

        # 创建菜单栏
        self.create_menu_bar()

        # 设置UI样式
        self.setup_ui_styles()

        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0) # 移除主布局边距
        main_layout.setSpacing(0) # 移除主布局间距

        # --- 左侧面板 (书籍列表) ---
        left_panel = QWidget()
        left_panel.setObjectName("left_panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        # 左侧工具栏
        left_toolbar_layout = QHBoxLayout()
        self.add_group_button = QPushButton("创建书籍组")
        self.add_group_button.setIcon(QIcon("assets/icons/add_folder.png")) # 假设有这个图标
        self.add_group_button.clicked.connect(self.create_book_group)
        left_toolbar_layout.addWidget(self.add_group_button)
        left_layout.addLayout(left_toolbar_layout)

        # 书籍组选择下拉框
        left_layout.addWidget(QLabel("书籍组"))
        self.book_group_combo = QComboBox()
        self.book_group_combo.setObjectName("book_group_combo")
        self.book_group_combo.currentIndexChanged.connect(self.on_book_group_selected)
        left_layout.addWidget(self.book_group_combo)

        left_layout.addWidget(QLabel("书籍列表"))
        self.book_table_widget = QTableWidget()
        self.book_table_widget.setObjectName("book_table_widget")
        self.book_table_widget.setColumnCount(2)
        self.book_table_widget.setHorizontalHeaderLabels(["状态", "书籍名称"])
        self.book_table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.book_table_widget.setSelectionBehavior(QTableWidget.SelectRows) # 整行选中
        self.book_table_widget.setEditTriggers(QTableWidget.NoEditTriggers) # 不可编辑
        self.book_table_widget.setSelectionMode(QTableWidget.SingleSelection) # 单选模式
        self.book_table_widget.setFocusPolicy(Qt.NoFocus) # 移除焦点框
        self.book_table_widget.itemSelectionChanged.connect(self.on_book_selected)
        self.book_table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.book_table_widget.customContextMenuRequested.connect(self.show_book_context_menu)
        # 设置行高
        self.book_table_widget.verticalHeader().setDefaultSectionSize(50)
        left_layout.addWidget(self.book_table_widget)
        main_layout.addWidget(left_panel, 2)

        # --- 中央内容区域 (使用 QStackedWidget 管理不同视图) ---
        self.central_stacked_widget = QStackedWidget()
        main_layout.addWidget(self.central_stacked_widget, 4) # 中央区域占更多空间

        # 1. 欢迎页面
        welcome_page = QWidget()
        welcome_layout = QVBoxLayout(welcome_page)
        welcome_layout.setAlignment(Qt.AlignCenter)
        welcome_layout.setContentsMargins(40, 40, 40, 40)
        welcome_layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("国际关系研究阅读助手")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(title_label)
        
        # 欢迎信息
        welcome_label = QLabel("欢迎使用本工具！\n\n📚 请在左侧创建书籍组或选择书籍进行操作\n🔧 支持PDF章节切分、MinerU解析、LLM分析等功能\n📊 可生成结构化的Word分析报告")
        welcome_label.setObjectName("welcome")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(welcome_label)
        
        self.central_stacked_widget.addWidget(welcome_page)

        # 2. 书籍组选择页面 (显示上传按钮)
        self.book_group_page = QWidget()
        book_group_layout = QVBoxLayout(self.book_group_page)
        book_group_layout.setContentsMargins(10, 10, 10, 10)
        book_group_layout.setSpacing(10)
        book_group_layout.setAlignment(Qt.AlignCenter)
        
        # 书籍组信息显示
        self.group_info_label = QLabel("请选择书籍组进行上传操作")
        self.group_info_label.setAlignment(Qt.AlignCenter)
        self.group_info_label.setFont(QFont("Arial", 14))
        book_group_layout.addWidget(self.group_info_label)
        
        # 上传按钮
        self.upload_book_button = QPushButton("上传书籍到此书籍组")
        self.upload_book_button.setIcon(QIcon("assets/icons/upload.png"))
        self.upload_book_button.clicked.connect(self.upload_book)
        self.upload_book_button.setEnabled(False)
        book_group_layout.addWidget(self.upload_book_button)
        
        self.central_stacked_widget.addWidget(self.book_group_page)

        # 3. 书籍详情/章节管理页面
        self.book_detail_page = QWidget()
        book_detail_layout = QVBoxLayout(self.book_detail_page)
        book_detail_layout.setContentsMargins(10, 10, 10, 10)
        book_detail_layout.setSpacing(10)

        # 右侧工具栏 (书籍详情页面不需要上传书籍按钮)
        right_toolbar_layout = QHBoxLayout()
        right_toolbar_layout.addStretch()
        book_detail_layout.addLayout(right_toolbar_layout)

        book_detail_layout.addWidget(QLabel("章节管理"))

        self.chapter_table = QTableWidget()
        self.chapter_table.setObjectName("chapter_table")
        self.chapter_table.setColumnCount(3)
        self.chapter_table.setHorizontalHeaderLabels(["章节标题", "起始页", "结束页"])
        self.chapter_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.chapter_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chapter_table.customContextMenuRequested.connect(self.show_chapter_context_menu)
        # 设置表格为可编辑
        self.chapter_table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        # 设置行高
        self.chapter_table.verticalHeader().setDefaultSectionSize(50)
        book_detail_layout.addWidget(self.chapter_table)

        button_layout = QHBoxLayout()
        self.add_chapter_button = QPushButton("添加章节")
        self.add_chapter_button.setIcon(QIcon("assets/icons/add.png"))
        self.add_chapter_button.clicked.connect(self.add_chapter)
        self.save_chapters_button = QPushButton("保存章节")
        self.save_chapters_button.setIcon(QIcon("assets/icons/save.png"))
        self.save_chapters_button.clicked.connect(self.save_chapters)
        button_layout.addWidget(self.add_chapter_button)
        button_layout.addWidget(self.save_chapters_button)
        book_detail_layout.addLayout(button_layout)

        # 添加章节切分按钮
        split_layout = QHBoxLayout()
        self.split_chapters_button = QPushButton("章节切分")
        self.split_chapters_button.setIcon(QIcon("assets/icons/split.png"))
        self.split_chapters_button.clicked.connect(self.split_chapters)
        self.split_chapters_button.setEnabled(False)
        split_layout.addWidget(self.split_chapters_button)
        book_detail_layout.addLayout(split_layout)

        # 添加处理按钮
        process_layout = QHBoxLayout()
        
        # MinerU处理按钮
        self.mineru_process_button = QPushButton("MinerU解析")
        self.mineru_process_button.setIcon(QIcon("assets/icons/process.png"))
        self.mineru_process_button.clicked.connect(self.process_with_mineru)
        self.mineru_process_button.setEnabled(False)
        process_layout.addWidget(self.mineru_process_button)
        
        # LLM分析按钮
        self.llm_analyze_button = QPushButton("LLM分析")
        self.llm_analyze_button.setIcon(QIcon("assets/icons/analyze.png"))
        self.llm_analyze_button.clicked.connect(self.analyze_with_llm)
        self.llm_analyze_button.setEnabled(False)
        process_layout.addWidget(self.llm_analyze_button)
        
        # 生成Word报告按钮
        self.generate_report_button = QPushButton("生成Word报告")
        self.generate_report_button.setIcon(QIcon("assets/icons/report.png"))
        self.generate_report_button.clicked.connect(self.generate_word_report)
        self.generate_report_button.setEnabled(False)
        process_layout.addWidget(self.generate_report_button)
        
        book_detail_layout.addLayout(process_layout)
        self.central_stacked_widget.addWidget(self.book_detail_page)

        # --- 日志面板 ---
        self.log_panel = QWidget()
        self.log_panel.setObjectName("log_panel")
        log_layout = QVBoxLayout(self.log_panel)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(10)

        # 日志输出区域
        log_layout.addWidget(QLabel("操作日志"))
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setObjectName("log_text_edit")
        self.log_text_edit.setReadOnly(True)
        log_layout.addWidget(self.log_text_edit)
        
        # 清空日志按钮
        clear_log_button = QPushButton("清空日志")
        clear_log_button.setIcon(QIcon("assets/icons/clear.png"))
        clear_log_button.clicked.connect(self.clear_log)
        log_layout.addWidget(clear_log_button)
        
        main_layout.addWidget(self.log_panel, 2)

        self.load_books()

    def setup_ui_styles(self):
        """设置UI的整体样式"""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #f5f7fa, stop:1 #c3cfe2);
                font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
            }
            
            QMenuBar {
                background-color: #2c3e50;
                color: white;
                border: none;
                padding: 4px;
                font-size: 14px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 16px;
                margin: 2px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #34495e;
            }
            QMenuBar::item:pressed {
                background-color: #1abc9c;
            }
            
            #left_panel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border-right: 2px solid #e9ecef;
                border-radius: 0px 8px 8px 0px;
                margin: 8px 0px 8px 8px;
            }
            
            #log_panel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border-left: 2px solid #e9ecef;
                border-radius: 8px 0px 0px 8px;
                margin: 8px 8px 8px 0px;
            }
            
            QStackedWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ffffff, stop:1 #f1f3f4);
                border-radius: 12px;
                margin: 8px 4px;
                border: 1px solid #dee2e6;
            }

            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                padding: 12px 20px;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                min-height: 16px;
                text-align: center;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #5a67d8, stop:1 #6b46c1);
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #4c51bf, stop:1 #553c9a);
                transform: translateY(1px);
            }
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #e2e8f0, stop:1 #cbd5e0);
                color: #a0aec0;
            }
            
            QPushButton#danger {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #fc8181, stop:1 #e53e3e);
            }
            QPushButton#danger:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #f56565, stop:1 #c53030);
            }
            
            QPushButton#success {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #68d391, stop:1 #38a169);
            }
            QPushButton#success:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #48bb78, stop:1 #2f855a);
            }

            QLabel {
                font-weight: 600;
                color: #2d3748;
                margin-bottom: 8px;
                font-size: 14px;
            }
            
            QLabel#title {
                font-size: 18px;
                font-weight: 700;
                color: #1a202c;
                margin: 12px 0px;
            }
            
            QLabel#welcome {
                font-size: 16px;
                font-weight: 500;
                color: #4a5568;
                line-height: 1.6;
                padding: 20px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #e6fffa, stop:1 #b2f5ea);
                border-radius: 12px;
                border: 1px solid #81e6d9;
            }

            QTreeWidget, QTableWidget {
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                background-color: #ffffff;
                selection-background-color: #e6fffa;
                selection-color: #1a202c;
                font-size: 13px;
                gridline-color: #f7fafc;
            }
            QTreeWidget::item, QTableWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #f7fafc;
                min-height: 40px;
            }
            QTreeWidget::item:hover, QTableWidget::item:hover {
                background-color: #f0fff4;
            }
            QTreeWidget::item:selected, QTableWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #e6fffa, stop:1 #b2f5ea);
                color: #1a202c;
                border: none;
            }
            QTreeWidget::branch:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #e6fffa, stop:1 #b2f5ea);
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #edf2f7, stop:1 #e2e8f0);
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid #cbd5e0;
                font-weight: 600;
                color: #2d3748;
                font-size: 13px;
            }

            QComboBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: #2d3748;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #cbd5e0;
            }
            QComboBox:focus {
                border-color: #667eea;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #4a5568;
                width: 0;
                height: 0;
            }

            #log_text_edit {
                background-color: #1a202c;
                border: 2px solid #4a5568;
                border-radius: 8px;
                color: #e2e8f0;
                font-family: "Consolas", "Monaco", monospace;
                font-size: 12px;
                padding: 8px;
                line-height: 1.5;
            }

            QProgressBar {
                border: 2px solid #cbd5e0;
                border-radius: 8px;
                text-align: center;
                background-color: #f7fafc;
                color: #2d3748;
                font-weight: 600;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 6px;
                margin: 2px;
            }
            
            QScrollBar:vertical {
                background-color: #f7fafc;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #cbd5e0, stop:1 #a0aec0);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #a0aec0, stop:1 #718096);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QInputDialog {
                background-color: #ffffff;
            }
            
            QMessageBox {
                background-color: #ffffff;
                color: #2d3748;
            }
            
            QDialog {
                background-color: #ffffff;
            }
        """)

    def process_with_mineru(self):
        """使用MinerU处理章节"""
        if not self.current_book_path:
            QMessageBox.warning(self, "错误", "请先选择一本书")
            return

        # 检查是否已完成章节切分
        chapters_pdf_dir = os.path.join(self.current_book_path, "chapters_pdf")
        if not os.path.exists(chapters_pdf_dir):
            QMessageBox.warning(self, "错误", "请先完成章节切分")
            return

        # 确认操作
        reply = QMessageBox.question(self, "确认处理", 
                                   f"确定要使用MinerU处理章节PDF吗？\n这可能会花费较长时间。",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # 禁用按钮，防止重复点击
        self.mineru_process_button.setEnabled(False)
        self.mineru_process_button.setText("处理中...")

        # 获取章节信息
        chapters = []
        for i in range(self.chapter_table.rowCount()):
            try:
                title = self.chapter_table.item(i, 0).text()
                chapters.append({"title": title})
            except AttributeError:
                QMessageBox.warning(self, "输入错误", f"第 {i+1} 行的章节标题无效，请检查。")
                return

        # 创建并启动工作线程
        self.mineru_worker = MinerUWorker(self.current_book_path, chapters)
        self.mineru_worker.log_message.connect(self.log_message)
        self.mineru_worker.finished.connect(self.on_mineru_processing_finished)
        self.mineru_worker.start()

    def on_mineru_processing_finished(self, success):
        """MinerU处理完成的回调"""
        # 恢复按钮状态
        self.mineru_process_button.setEnabled(True)
        self.mineru_process_button.setText("MinerU解析")

        if success:
            # 更新元数据状态
            metadata = self.book_manager.get_book_metadata(self.current_book_path) or {}
            metadata["status"] = "已完成MinerU解析"
            self.book_manager.save_book_metadata(self.current_book_path, metadata)
            
            # 刷新书籍列表显示状态
            self.load_books()
            
            QMessageBox.information(self, "成功", "MinerU处理完成！")
        else:
            QMessageBox.warning(self, "错误", "MinerU处理失败，请查看日志了解详情")

        # 清理工作线程
        if self.mineru_worker:
            self.mineru_worker.deleteLater()
            self.mineru_worker = None

    def analyze_with_llm(self):
        """使用LLM分析章节"""
        if not self.current_book_path:
            QMessageBox.warning(self, "错误", "请先选择一本书")
            return

        # 检查是否已完成MinerU解析
        chapters_markdown_dir = os.path.join(self.current_book_path, "chapters_markdown")
        if not os.path.exists(chapters_markdown_dir):
            QMessageBox.warning(self, "错误", "请先完成MinerU解析")
            return

        # 确认操作
        reply = QMessageBox.question(self, "确认分析", 
                                   f"确定要使用LLM分析章节内容吗？\n这可能会花费较长时间。",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # 禁用按钮，防止重复点击
        self.llm_analyze_button.setEnabled(False)
        self.llm_analyze_button.setText("分析中...")

        # 获取章节信息
        chapters = []
        for i in range(self.chapter_table.rowCount()):
            try:
                title = self.chapter_table.item(i, 0).text()
                chapters.append({"title": title})
            except AttributeError:
                QMessageBox.warning(self, "输入错误", f"第 {i+1} 行的章节标题无效，请检查。")
                return

        # 创建并启动工作线程
        self.llm_worker = LLMAnalysisWorker(self.current_book_path, chapters)
        self.llm_worker.log_message.connect(self.log_message)
        self.llm_worker.finished.connect(self.on_llm_analysis_finished)
        self.llm_worker.start()

    def on_llm_analysis_finished(self, success):
        """LLM分析完成的回调"""
        self.llm_analyze_button.setEnabled(True)
        self.llm_analyze_button.setText("LLM分析")

        if success:
            QMessageBox.information(self, "成功", "LLM分析完成！")
        else:
            QMessageBox.warning(self, "错误", "LLM分析失败，请查看日志了解详情")

        if self.llm_worker:
            self.llm_worker.deleteLater()
            self.llm_worker = None

    def generate_word_report(self):
        """生成Word报告"""
        if not self.current_book_path:
            QMessageBox.warning(self, "错误", "请先选择一本书")
            return

        # 确认操作
        reply = QMessageBox.question(self, "确认生成报告", 
                                   f"确定要生成Word报告吗？",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # 禁用按钮，防止重复点击
        self.generate_report_button.setEnabled(False)
        self.generate_report_button.setText("生成中...")

        # 创建并启动工作线程
        self.report_worker = ReportGenerationWorker(self.current_book_path)
        self.report_worker.log_message.connect(self.log_message)
        self.report_worker.finished.connect(self.on_report_generation_finished)
        self.report_worker.start()

    def on_report_generation_finished(self, success, report_path):
        """报告生成完成的回调"""
        self.generate_report_button.setEnabled(True)
        self.generate_report_button.setText("生成Word报告")

        if success:
            QMessageBox.information(self, "成功", f"报告生成完成！路径：{report_path}")
        else:
            QMessageBox.warning(self, "错误", "报告生成失败，请查看日志了解详情")

        if self.report_worker:
            self.report_worker.deleteLater()
            self.report_worker = None

    def log_message(self, message):
        """记录日志信息"""
        self.log_text_edit.append(message)
        self.log_text_edit.moveCursor(QTextCursor.End)

    def clear_log(self):
        """清空日志"""
        self.log_text_edit.clear()

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 设置菜单项
        settings_action = file_menu.addAction("设置")
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.open_settings)
        
        file_menu.addSeparator()
        
        # 退出菜单项
        exit_action = file_menu.addAction("退出")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        # 批量处理菜单项
        batch_process_action = tools_menu.addAction("批量处理")
        batch_process_action.triggered.connect(self.batch_process)
        batch_process_action.setEnabled(False)  # 暂时禁用
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        # 关于菜单项
        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(self.show_about)

    def open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.log_message("设置已更新")

    def batch_process(self):
        """批量处理功能（待实现）"""
        QMessageBox.information(self, "提示", "批量处理功能将在后续版本中实现")

    def show_about(self):
        """显示关于对话框"""
        about_text = """
<h3>国际关系研究阅读助手</h3>
<p>版本: 1.0.0</p>
<p>这是一个专为国际关系研究人员设计的PDF文献处理工具。</p>
<p><b>主要功能：</b></p>
<ul>
<li>PDF章节切分</li>
<li>MinerU智能解析</li>
<li>LLM内容分析</li>
<li>结构化报告生成</li>
</ul>
<p>作者: TR开发团队</p>
        """
        QMessageBox.about(self, "关于", about_text)

    def load_books(self):
        """加载书籍列表"""
        # 在更新期间禁用信号，防止不必要的操作
        self.book_group_combo.blockSignals(True)
        
        # 加载书籍组到下拉框
        book_groups = self.book_manager.scan_book_groups()
        current_group = self.book_group_combo.currentText()
        
        self.book_group_combo.clear()
        self.book_group_combo.addItems(book_groups)
        
        # 尝试恢复之前选择的书籍组
        if current_group and current_group in book_groups:
            index = book_groups.index(current_group)
            self.book_group_combo.setCurrentIndex(index)
        elif book_groups:
            self.book_group_combo.setCurrentIndex(0)
        
        # 重新启用信号
        self.book_group_combo.blockSignals(False)
        
        # 更新书籍列表
        if book_groups:
            self.update_book_list(self.book_group_combo.currentText())
        else:
            self.book_table_widget.setRowCount(0)

    def create_book_group(self):
        """创建书籍组"""
        group_name, ok = QInputDialog.getText(self, "创建书籍组", "请输入书籍组名称:")
        if ok and group_name:
            success, message = self.book_manager.create_book_group(group_name)
            if success:
                self.load_books()
                QMessageBox.information(self, "成功", "书籍组创建成功")
            else:
                QMessageBox.warning(self, "错误", message)

    def on_book_group_selected(self):
        """书籍组选择变化时的处理"""
        selected_group = self.book_group_combo.currentText()
        if selected_group:
            self.update_book_list(selected_group)
            # 启用上传按钮并更新信息
            self.upload_book_button.setEnabled(True)
            self.upload_book_button.setText(f"上传书籍到 {selected_group}")
            self.group_info_label.setText(f"已选择书籍组: {selected_group}\n\n点击下方按钮上传PDF文件到此书籍组")
            self.central_stacked_widget.setCurrentIndex(1)  # 显示书籍组页面
        else:
            self.upload_book_button.setEnabled(False)
            self.central_stacked_widget.setCurrentIndex(0)  # 显示欢迎页面

    def update_book_list(self, group_name):
        """根据选择的书籍组更新书籍列表"""
        self.book_table_widget.setRowCount(0)  # 清空当前书籍列表
        
        if not group_name:
            return

        try:
            books = self.book_manager.scan_books_in_group(group_name)
            for book_title in books:
                book_path = os.path.join(self.book_manager.data_path, group_name, book_title)
                metadata = self.book_manager.get_book_metadata(book_path)
                status = metadata.get("status", "未知") if metadata else "未知"

                row_position = self.book_table_widget.rowCount()
                self.book_table_widget.insertRow(row_position)
                self.book_table_widget.setItem(row_position, 0, QTableWidgetItem(status))
                self.book_table_widget.setItem(row_position, 1, QTableWidgetItem(book_title))
                self.book_table_widget.item(row_position, 1).setData(Qt.UserRole, book_path)  # 存储书籍路径
        except Exception as e:
            self.log_message(f"加载书籍列表时出错: {str(e)}")

    def on_book_selected(self):
        """书籍选择变化时的处理"""
        selected_row = self.book_table_widget.currentRow()
        if selected_row >= 0:
            book_path = self.book_table_widget.item(selected_row, 1).data(Qt.UserRole)
            self.current_book_path = book_path
            # 切换到书籍详情页面
            self.central_stacked_widget.setCurrentIndex(2)
            # 加载章节信息
            self.load_chapters()
        else:
            self.current_book_path = None
            # 切换回书籍组页面或欢迎页面
            if self.book_group_combo.currentText():
                self.central_stacked_widget.setCurrentIndex(1)  # 书籍组页面
            else:
                self.central_stacked_widget.setCurrentIndex(0)  # 欢迎页面

    def upload_book(self):
        """上传书籍"""
        selected_group = self.book_group_combo.currentText()
        if not selected_group:
            QMessageBox.warning(self, "错误", "请先选择一个书籍组")
            return

        file_paths, _ = QFileDialog.getOpenFileNames(self, "选择 PDF 文件", "", "PDF Files (*.pdf)")
        if file_paths:
            try:
                start_index = len(self.book_manager.scan_books_in_group(selected_group))
            except Exception:
                start_index = 0

            success_count = 0
            error_messages = []
            for i, file_path in enumerate(file_paths):
                success, result = self.book_manager.upload_book(selected_group, file_path, start_index + i)
                if success:
                    success_count += 1
                    formatted_title = result
                    self.log_message(f"成功上传书籍: {formatted_title}")
                else:
                    error_messages.append(f"上传 {os.path.basename(file_path)} 失败: {result}")
                    self.log_message(f"上传 {os.path.basename(file_path)} 失败: {result}")

            self.load_books()
            if success_count > 0:
                QMessageBox.information(self, "上传完成", f"成功上传 {success_count} 本书籍。")
            if error_messages:
                QMessageBox.warning(self, "上传失败", "\n".join(error_messages))

    def show_book_context_menu(self, position):
        """显示书籍上下文菜单"""
        item = self.book_table_widget.itemAt(position)
        if not item:
            return

        menu = QMenu()
        delete_book_action = menu.addAction("删除书籍")
        action = menu.exec(self.book_table_widget.mapToGlobal(position))
        
        if action == delete_book_action:
            self.delete_book()

    def delete_book(self):
        """删除选中的书籍"""
        selected_row = self.book_table_widget.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "错误", "请先选择一本书籍")
            return
            
        book_path = self.book_table_widget.item(selected_row, 1).data(Qt.UserRole)
        book_title = self.book_table_widget.item(selected_row, 1).text()
        
        reply = QMessageBox.question(self, "确认删除", f"确定要删除书籍 '{book_title}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            success, message = self.book_manager.delete_book(book_path)
            if success:
                self.load_books()
                QMessageBox.information(self, "成功", "书籍已删除")
            else:
                QMessageBox.warning(self, "错误", message)

    def show_chapter_context_menu(self, position):
        """显示章节上下文菜单"""
        item = self.chapter_table.itemAt(position)
        if not item:
            return

        menu = QMenu()
        
        delete_action = menu.addAction("删除此章节")
        delete_before_action = menu.addAction("删除之前所有章节")
        delete_after_action = menu.addAction("删除之后所有章节")
        menu.addSeparator()
        insert_before_action = menu.addAction("在此章节前插入")
        insert_after_action = menu.addAction("在此章节后插入")
        menu.addSeparator()
        save_action = menu.addAction("保存章节")

        action = menu.exec(self.chapter_table.mapToGlobal(position))
        
        current_row = item.row()

        if action == delete_action:
            self.delete_selected_chapter()
        elif action == delete_before_action:
            self.delete_before_chapters()
        elif action == delete_after_action:
            self.delete_after_chapters()
        elif action == insert_before_action:
            self.add_chapter(current_row)
        elif action == insert_after_action:
            self.add_chapter(current_row + 1)
        elif action == save_action:
            self.save_chapters()

    def delete_selected_chapter(self):
        """删除选中的章节"""
        current_row = self.chapter_table.currentRow()
        if current_row >= 0:
            self.chapter_table.removeRow(current_row)

    def delete_before_chapters(self):
        """删除当前章节之前的所有章节"""
        current_row = self.chapter_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "错误", "请先选择一个章节")
            return
        
        reply = QMessageBox.question(self, "确认删除", f"确定要删除第 {current_row + 1} 章之前的所有章节吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            for i in range(current_row - 1, -1, -1):
                self.chapter_table.removeRow(i)

    def delete_after_chapters(self):
        """删除当前章节之后的所有章节"""
        current_row = self.chapter_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "错误", "请先选择一个章节")
            return

        reply = QMessageBox.question(self, "确认删除", f"确定要删除第 {current_row + 1} 章之后的所有章节吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            for i in range(self.chapter_table.rowCount() - 1, current_row, -1):
                self.chapter_table.removeRow(i)

    def add_chapter(self, row=-1):
        """添加章节"""
        if row == -1:
            row = self.chapter_table.rowCount()
        self.chapter_table.insertRow(row)
        self.chapter_table.setItem(row, 0, QTableWidgetItem("新章节"))
        self.chapter_table.setItem(row, 1, QTableWidgetItem("0"))
        self.chapter_table.setItem(row, 2, QTableWidgetItem("0"))

    def save_chapters(self):
        """保存章节"""
        if not self.current_book_path:
            QMessageBox.warning(self, "错误", "请先选择一本书")
            return

        chapters = []
        for i in range(self.chapter_table.rowCount()):
            try:
                title = self.chapter_table.item(i, 0).text()
                start_page = int(self.chapter_table.item(i, 1).text())
                end_page = int(self.chapter_table.item(i, 2).text())
                chapters.append({"title": title, "start_page": start_page, "end_page": end_page})
            except (ValueError, AttributeError):
                QMessageBox.warning(self, "输入错误", f"第 {i+1} 行的页码无效，请检查。")
                return

        metadata = {"status": "完成章节编辑", "chapters": chapters}
        
        if self.book_manager.save_book_metadata(self.current_book_path, metadata):
            QMessageBox.information(self, "成功", "章节信息保存成功")
            self.load_books()
        else:
            QMessageBox.warning(self, "错误", "保存失败")

    def split_chapters(self):
        """章节切分功能"""
        if not self.current_book_path:
            QMessageBox.warning(self, "错误", "请先选择一本书")
            return

        # 获取章节信息
        chapters = []
        for i in range(self.chapter_table.rowCount()):
            try:
                title = self.chapter_table.item(i, 0).text()
                start_page = int(self.chapter_table.item(i, 1).text())
                end_page = int(self.chapter_table.item(i, 2).text())
                chapters.append({"title": title, "start_page": start_page, "end_page": end_page})
            except (ValueError, AttributeError):
                QMessageBox.warning(self, "输入错误", f"第 {i+1} 行的页码无效，请检查。")
                return

        if not chapters:
            QMessageBox.warning(self, "错误", "没有章节信息，请先添加章节")
            return

        # 确认操作
        reply = QMessageBox.question(self, "确认切分", f"确定要将PDF切分成 {len(chapters)} 个章节吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self.log_message("开始章节切分...")
        
        # 执行切分
        from core.pdf_processor import split_pdf_by_chapters
        
        original_pdf_path = os.path.join(self.current_book_path, "original.pdf")
        chapters_pdf_dir = os.path.join(self.current_book_path, "chapters_pdf")
        
        try:
            success, error_msg = split_pdf_by_chapters(original_pdf_path, chapters, chapters_pdf_dir)
            
            if success:
                self.log_message(f"章节切分完成！共生成 {len(chapters)} 个章节PDF文件")
                
                # 更新元数据状态
                metadata = self.book_manager.get_book_metadata(self.current_book_path) or {}
                metadata["status"] = "已完成章节切分"
                metadata["chapters"] = chapters
                self.book_manager.save_book_metadata(self.current_book_path, metadata)
                
                # 刷新书籍列表显示状态
                self.load_books()
                
                QMessageBox.information(self, "成功", "章节切分完成！")
            else:
                self.log_message(f"章节切分失败：{error_msg}")
                QMessageBox.warning(self, "错误", f"章节切分失败：{error_msg}")
                
        except Exception as e:
            error_msg = f"章节切分过程中发生错误：{str(e)}"
            self.log_message(error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    def load_chapters(self):
        """加载章节信息"""
        if not self.current_book_path:
            return

        metadata = self.book_manager.get_book_metadata(self.current_book_path)
        
        # 如果有元数据且状态不是"未处理"，则从元数据中读取章节信息
        if metadata and metadata.get("status") != "未处理" and metadata.get("chapters"):
            self.update_chapter_table(metadata.get("chapters", []))
            self.update_button_states()
            return

        # 只有在"未处理"状态或没有章节信息时，才从PDF书签获取
        pdf_path = os.path.join(self.current_book_path, "original.pdf")
        if not os.path.exists(pdf_path):
            self.update_chapter_table([])
            self.update_button_states()
            return
            
        bookmarks = get_bookmarks(pdf_path)
        for i, bookmark in enumerate(bookmarks):
            if i + 1 < len(bookmarks):
                bookmark["end_page"] = bookmarks[i+1]["page"] - 1
            else:
                bookmark["end_page"] = bookmark["page"]
        
        chapters = [{"title": b["title"], "start_page": b["page"], "end_page": b["end_page"]} for b in bookmarks]
        self.update_chapter_table(chapters)
        self.update_button_states()

    def update_chapter_table(self, chapters):
        """更新章节表格"""
        self.chapter_table.setRowCount(len(chapters))
        for i, chapter in enumerate(chapters):
            self.chapter_table.setItem(i, 0, QTableWidgetItem(chapter["title"]))
            self.chapter_table.setItem(i, 1, QTableWidgetItem(str(chapter["start_page"])))
            self.chapter_table.setItem(i, 2, QTableWidgetItem(str(chapter["end_page"])))

    def update_button_states(self):
        """更新按钮的启用状态"""
        if not self.current_book_path:
            self.split_chapters_button.setEnabled(False)
            self.mineru_process_button.setEnabled(False)
            self.llm_analyze_button.setEnabled(False)
            return

        # 检查是否有章节信息且PDF文件存在
        has_chapters = self.chapter_table.rowCount() > 0
        pdf_exists = os.path.exists(os.path.join(self.current_book_path, "original.pdf"))
        
        self.split_chapters_button.setEnabled(has_chapters and pdf_exists)

        # MinerU解析按钮状态
        chapters_pdf_dir = os.path.join(self.current_book_path, "chapters_pdf")
        mineru_ready = os.path.exists(chapters_pdf_dir) and len(os.listdir(chapters_pdf_dir)) > 0
        self.mineru_process_button.setEnabled(mineru_ready)

        # LLM分析按钮状态
        chapters_markdown_dir = os.path.join(self.current_book_path, "chapters_markdown")
        llm_ready = os.path.exists(chapters_markdown_dir) and len(os.listdir(chapters_markdown_dir)) > 0
        self.llm_analyze_button.setEnabled(llm_ready)

        # 生成Word报告按钮状态
        llm_result_exists = os.path.exists(os.path.join(self.current_book_path, "llm_result"))
        self.generate_report_button.setEnabled(llm_result_exists)

        # 更新上传按钮状态
        self.upload_book_button.setEnabled(bool(self.book_group_combo.currentText()))
