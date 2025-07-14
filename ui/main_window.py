# 主窗口UI实现
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTreeView, QTableWidget, QTextBrowser, QLabel, QLineEdit,
    QPushButton, QSplitter, QStatusBar, QStackedWidget, QHeaderView,
    QTableWidgetItem, QFormLayout
)
from PySide6.QtGui import QIcon, QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QSize

# 为了方便演示，我们先创建一个简单的函数来获取标准图标
# 在实际项目中，你会从文件中加载图标：QIcon("assets/icons/complete.png")
def get_std_icon(name):
    """从Qt标准库中获取一个图标，用于演示"""
    style = QApplication.style()
    return style.standardIcon(getattr(style.StandardPixmap, name))

class MainWindow(QMainWindow):
    """
    应用程序的主窗口类
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aide de Lecture for IR - 国际关系研究阅读助手")
        self.setGeometry(100, 100, 1200, 800)

        # --- 创建主布局和中央控件 ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 创建一个可调节的分割器
        splitter = QSplitter(Qt.Horizontal)

        # --- 创建各个面板 ---
        self.left_pane = self._create_left_pane()
        self.center_pane = self._create_center_pane()
        self.right_pane = self._create_right_pane()

        # 将面板添加到分割器中
        splitter.addWidget(self.left_pane)
        splitter.addWidget(self.center_pane)
        splitter.addWidget(self.right_pane)

        # 设置初始大小比例
        splitter.setSizes([250, 650, 300])

        main_layout.addWidget(splitter)

        # --- 创建状态栏 ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("准备就绪")

        # --- 连接信号 ---
        # 当左侧树状视图的选择变化时，触发一个函数
        self.tree_view.selectionModel().selectionChanged.connect(self.on_book_selected)

    def _create_left_pane(self):
        """创建左侧的书籍列表面板"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0) # 布局无边距

        # 添加操作按钮
        toolbar_layout = QHBoxLayout()
        add_group_btn = QPushButton("新建组")
        add_book_btn = QPushButton("添加书籍")
        toolbar_layout.addWidget(add_group_btn)
        toolbar_layout.addWidget(add_book_btn)
        
        layout.addLayout(toolbar_layout)

        # 创建树状视图
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True) # 隐藏表头
        
        # 创建数据模型
        self.tree_model = QStandardItemModel()
        root_node = self.tree_model.invisibleRootItem()

        # --- 添加假数据用于演示 ---
        group1 = QStandardItem("国际关系理论")
        group1.setIcon(get_std_icon("SP_DirIcon"))
        root_node.appendRow(group1)

        book_a = QStandardItem("Book A: The Tragedy of Great Power Politics")
        book_a.setIcon(get_std_icon("SP_DialogOkButton")) # 绿色勾 -> 已完成
        book_a.setData("complete", Qt.UserRole) # 存储状态信息
        group1.appendRow(book_a)

        book_b = QStandardItem("Book B: Man, the State, and War")
        book_b.setIcon(get_std_icon("SP_BrowserReload")) # 旋转箭头 -> 处理中
        book_b.setData("processing", Qt.UserRole)
        group1.appendRow(book_b)

        group2 = QStandardItem("中国外交政策")
        group2.setIcon(get_std_icon("SP_DirIcon"))
        root_node.appendRow(group2)

        book_c = QStandardItem("Book C: On China")
        book_c.setIcon(get_std_icon("SP_MessageBoxCritical")) # 红色叉 -> 出错
        book_c.setData("error", Qt.UserRole)
        group2.appendRow(book_c)

        book_d = QStandardItem("Book D: Has China Won?")
        book_d.setIcon(get_std_icon("SP_TimeLink")) # 时钟 -> 待处理
        book_d.setData("pending", Qt.UserRole)
        group2.appendRow(book_d)
        
        self.tree_view.setModel(self.tree_model)
        layout.addWidget(self.tree_view)

        return container

    def _create_center_pane(self):
        """创建中心的主工作区面板"""
        # QStackedWidget 允许多个"页面"存在，我们可以根据选择来切换
        self.stacked_widget = QStackedWidget()
        
        # 页面1: 章节管理视图
        chapter_view = self._create_chapter_management_view()
        
        # 页面2: 分析结果视图
        analysis_view = self._create_analysis_view()
        
        # 页面0: 欢迎/空白页
        welcome_label = QLabel("请在左侧选择一本书籍进行操作")
        welcome_label.setAlignment(Qt.AlignCenter)
        
        self.stacked_widget.addWidget(welcome_label) # index 0
        self.stacked_widget.addWidget(chapter_view)    # index 1
        self.stacked_widget.addWidget(analysis_view)   # index 2

        return self.stacked_widget
    
    def _create_chapter_management_view(self):
        """创建用于管理章节的视图"""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        self.chapter_table = QTableWidget()
        self.chapter_table.setColumnCount(5)
        self.chapter_table.setHorizontalHeaderLabels([" ", "章节标题", "起始页", "结束页", "状态"])
        self.chapter_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # 标题列自动拉伸
        self.chapter_table.setColumnWidth(0, 30)
        self.chapter_table.setColumnWidth(2, 80)
        self.chapter_table.setColumnWidth(3, 80)
        self.chapter_table.setColumnWidth(4, 80)
        
        # 添加操作按钮
        btn_layout = QHBoxLayout()
        load_bookmark_btn = QPushButton("从书签加载")
        add_chapter_btn = QPushButton("添加章节")
        remove_chapter_btn = QPushButton("删除章节")
        start_processing_btn = QPushButton("开始处理")
        start_processing_btn.setObjectName("start_button") # 用于设置CSS样式
        
        btn_layout.addWidget(load_bookmark_btn)
        btn_layout.addWidget(add_chapter_btn)
        btn_layout.addWidget(remove_chapter_btn)
        btn_layout.addStretch() # 添加伸缩，让按钮靠左
        btn_layout.addWidget(start_processing_btn)

        layout.addWidget(self.chapter_table)
        layout.addLayout(btn_layout)
        
        return container

    def _create_analysis_view(self):
        """创建用于显示分析结果的视图"""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        self.analysis_browser = QTextBrowser()
        # 使用HTML来模拟富文本报告
        self.analysis_browser.setHtml("""
            <h1>Book B: Man, the State, and War</h1>
            <hr>
            <h2>Chapter 1: Introduction</h2>
            <h3>核心论点</h3>
            <p>战争的根源可以从三个层面进行分析：个人、国家、以及国际体系。</p>
            <h3>支撑论据</h3>
            <ul>
                <li>个人层面的人性本恶或非理性是导致冲突的原因之一。 <i>(原文引用...) [p. 15]</i></li>
                <li>国家的内部结构，无论是民主还是专制，都会影响其对外行为。 <i>(原文引用...) [p. 32]</i></li>
            </ul>
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        generate_report_btn = QPushButton("生成 Word 报告")
        btn_layout.addWidget(generate_report_btn)
        
        layout.addWidget(self.analysis_browser)
        layout.addLayout(btn_layout)
        
        return container


    def _create_right_pane(self):
        """创建右侧的详情/预览面板"""
        container = QWidget()
        layout = QVBoxLayout(container)
        container.setObjectName("right_pane")
        
        self.details_title = QLabel("书籍详情")
        self.details_title.setObjectName("details_title")
        
        # 使用QFormLayout来创建整齐的键值对标签
        form_layout = QFormLayout()
        self.detail_book_title = QLineEdit()
        self.detail_author = QLineEdit()
        self.detail_status = QLineEdit()
        
        # 设为只读
        for field in [self.detail_book_title, self.detail_author, self.detail_status]:
            field.setReadOnly(True)
        
        form_layout.addRow("书名:", self.detail_book_title)
        form_layout.addRow("作者:", self.detail_author)
        form_layout.addRow("状态:", self.detail_status)
        
        layout.addWidget(self.details_title)
        layout.addLayout(form_layout)
        layout.addStretch() # 添加伸缩，让内容靠上
        
        return container

    def on_book_selected(self, selected, deselected):
        """当左侧列表中的选择项发生变化时调用的槽函数"""
        # 获取选中的项
        indexes = selected.indexes()
        if not indexes:
            self.stacked_widget.setCurrentIndex(0) # 显示欢迎页
            return

        item = self.tree_model.itemFromIndex(indexes[0])
        
        # 如果选中的是书籍组（父节点），则不做任何事
        if not item.parent():
            self.stacked_widget.setCurrentIndex(0)
            return
            
        book_title = item.text()
        book_status = item.data(Qt.UserRole)
        
        self.status_bar.showMessage(f"已选择: {book_title}")

        # 更新右侧详情面板
        self.detail_book_title.setText(book_title)
        self.detail_author.setText("未知") # TODO: 从metadata加载
        self.detail_status.setText(book_status)
        
        # 根据书籍状态，切换中间的工作区
        if book_status in ["pending", "error"]:
            self.stacked_widget.setCurrentIndex(1) # 显示章节管理
            # TODO: 清空并加载这本书的章节信息到表格
            self._populate_chapter_table_with_dummy_data() # 临时用假数据填充
        elif book_status in ["processing", "complete"]:
            self.stacked_widget.setCurrentIndex(2) # 显示分析结果
            # TODO: 加载这本书的分析报告
            
    def _populate_chapter_table_with_dummy_data(self):
        """用假数据填充章节表格，用于演示"""
        self.chapter_table.setRowCount(0) # 清空表格
        
        chapters = [
            ("Chapter 1: Introduction", 1, 20, "✔️"),
            ("Chapter 2: The Offensive Realism", 21, 55, "🕒")
        ]
        
        for i, (title, start, end, status) in enumerate(chapters):
            self.chapter_table.insertRow(i)
            
            # 复选框
            chk_box_item = QTableWidgetItem()
            chk_box_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_box_item.setCheckState(Qt.Checked)
            self.chapter_table.setItem(i, 0, chk_box_item)
            
            self.chapter_table.setItem(i, 1, QTableWidgetItem(title))
            self.chapter_table.setItem(i, 2, QTableWidgetItem(str(start)))
            self.chapter_table.setItem(i, 3, QTableWidgetItem(str(end)))
            self.chapter_table.setItem(i, 4, QTableWidgetItem(status))


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 可选：设置一个现代化的样式
    app.setStyleSheet("""
        QWidget#right_pane {
            background-color: #f0f0f0;
        }
        QLabel#details_title {
            font-size: 16px;
            font-weight: bold;
            padding-bottom: 10px;
        }
        QPushButton#start_button {
            font-weight: bold;
            background-color: #4CAF50; /* 绿色 */
            color: white;
            padding: 8px;
            border-radius: 4px;
        }
        QPushButton#start_button:hover {
            background-color: #45a049;
        }
    """)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())