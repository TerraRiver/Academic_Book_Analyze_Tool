import sys
import os
import json
from PySide6.QtCore import Qt
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
)
from core.book_manager import BookManager
from core.pdf_processor import get_bookmarks


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("国际关系研究阅读助手")
        self.setGeometry(100, 100, 1200, 800)

        self.book_manager = BookManager()
        self.current_book_path = None

        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # --- 左侧面板重构 ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        left_toolbar = QHBoxLayout()
        self.add_group_button = QPushButton("创建书籍组")
        self.add_group_button.clicked.connect(self.create_book_group)
        left_toolbar.addWidget(self.add_group_button)
        left_layout.addLayout(left_toolbar)

        left_layout.addWidget(QLabel("书籍列表"))
        self.book_tree_widget = QTreeWidget()
        self.book_tree_widget.setHeaderLabel("书籍")
        self.book_tree_widget.currentItemChanged.connect(self.on_item_selected)
        self.book_tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.book_tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.book_tree_widget)
        main_layout.addWidget(left_panel, 1)

        # --- 右侧面板 ---
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_toolbar = QHBoxLayout()
        self.upload_book_button = QPushButton("上传书籍")
        self.upload_book_button.clicked.connect(self.upload_book)
        self.upload_book_button.setEnabled(False)
        right_toolbar.addWidget(self.upload_book_button)
        right_layout.addLayout(right_toolbar)

        right_layout.addWidget(QLabel("章节管理"))

        self.chapter_table = QTableWidget()
        self.chapter_table.setColumnCount(3)
        self.chapter_table.setHorizontalHeaderLabels(["章节标题", "起始页", "结束页"])
        self.chapter_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.chapter_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chapter_table.customContextMenuRequested.connect(self.show_chapter_context_menu)
        right_layout.addWidget(self.chapter_table)

        button_layout = QHBoxLayout()
        self.add_chapter_button = QPushButton("添加章节")
        self.add_chapter_button.clicked.connect(self.add_chapter)
        self.save_chapters_button = QPushButton("保存章节")
        self.save_chapters_button.clicked.connect(self.save_chapters)
        button_layout.addWidget(self.add_chapter_button)
        button_layout.addWidget(self.save_chapters_button)
        right_layout.addLayout(button_layout)

        # 添加章节切分按钮
        split_layout = QHBoxLayout()
        self.split_chapters_button = QPushButton("章节切分")
        self.split_chapters_button.clicked.connect(self.split_chapters)
        self.split_chapters_button.setEnabled(False)
        split_layout.addWidget(self.split_chapters_button)
        right_layout.addLayout(split_layout)

        main_layout.addWidget(self.right_panel, 2)

        # --- 详情/预览面板 ---
        self.detail_panel = QWidget()
        detail_layout = QVBoxLayout(self.detail_panel)
        
        detail_layout.addWidget(QLabel("详情/预览"))
        
        # 书籍信息显示区域
        self.book_info_label = QLabel("请选择一本书籍")
        self.book_info_label.setWordWrap(True)
        self.book_info_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc; }")
        detail_layout.addWidget(self.book_info_label)
        
        # 日志输出区域
        detail_layout.addWidget(QLabel("操作日志"))
        from PySide6.QtWidgets import QTextEdit
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setMaximumHeight(200)
        detail_layout.addWidget(self.log_text_edit)
        
        # 清空日志按钮
        clear_log_button = QPushButton("清空日志")
        clear_log_button.clicked.connect(self.clear_log)
        detail_layout.addWidget(clear_log_button)
        
        main_layout.addWidget(self.detail_panel, 1)

        self.load_books()

    def load_books(self):
        """
        重构后的书籍加载方法，确保稳定性和正确性。
        """
        # 在更新期间禁用信号，防止不必要的操作
        self.book_tree_widget.blockSignals(True)
        self.book_tree_widget.clear()

        book_groups = self.book_manager.scan_book_groups()
        for group_name in book_groups:
            group_item = QTreeWidgetItem()
            group_item.setText(0, group_name)
            self.book_tree_widget.addTopLevelItem(group_item)

            books = self.book_manager.scan_books_in_group(group_name)
            for book_title in books:
                book_path = os.path.join(self.book_manager.data_path, group_name, book_title)
                metadata = self.book_manager.get_book_metadata(book_path)
                status = metadata.get("status", "未知") if metadata else "未知"

                # 限制书名长度
                max_len = 30
                truncated_title = (book_title[:max_len] + '...') if len(book_title) > max_len else book_title
                
                display_text = f"[{status}] {truncated_title}"

                book_item = QTreeWidgetItem()
                book_item.setText(0, display_text)
                # 使用 Qt.UserRole 来存储自定义数据，这是标准做法
                book_item.setData(0, Qt.UserRole + 1, book_path)
                book_item.setData(0, Qt.UserRole + 2, book_title)
                
                group_item.addChild(book_item)

        self.book_tree_widget.expandAll()
        # 完成更新后重新启用信号
        self.book_tree_widget.blockSignals(False)

    def on_item_selected(self, current, previous):
        if current is None:
            self.upload_book_button.setEnabled(False)
            self.current_book_path = None
            return

        # 如果选择的是书籍组 (没有父项)
        if current.parent() is None:
            self.upload_book_button.setEnabled(True)
            self.chapter_table.setRowCount(0)
            self.current_book_path = None
        # 如果选择的是书籍 (有父项)
        else:
            self.upload_book_button.setEnabled(False)
            self.current_book_path = current.data(0, Qt.UserRole + 1)
            self.load_chapters()
            self.update_book_info()

    def load_chapters(self):
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
        self.chapter_table.setRowCount(len(chapters))
        for i, chapter in enumerate(chapters):
            self.chapter_table.setItem(i, 0, QTableWidgetItem(chapter["title"]))
            self.chapter_table.setItem(i, 1, QTableWidgetItem(str(chapter["start_page"])))
            self.chapter_table.setItem(i, 2, QTableWidgetItem(str(chapter["end_page"])))

    def create_book_group(self):
        group_name, ok = QInputDialog.getText(self, "创建书籍组", "请输入书籍组名称:")
        if ok and group_name:
            success, message = self.book_manager.create_book_group(group_name)
            if success:
                self.load_books()
                QMessageBox.information(self, "成功", "书籍组创建成功")
            else:
                QMessageBox.warning(self, "错误", message)

    def upload_book(self):
        current_item = self.book_tree_widget.currentItem()
        if not current_item or current_item.parent() is not None:
            QMessageBox.warning(self, "错误", "请先选择一个书籍组")
            return

        group_name = current_item.text(0)
        file_paths, _ = QFileDialog.getOpenFileNames(self, "选择 PDF 文件", "", "PDF Files (*.pdf)")
        if file_paths:
            try:
                start_index = len(self.book_manager.scan_books_in_group(group_name))
            except Exception:
                start_index = 0

            success_count = 0
            error_messages = []
            for i, file_path in enumerate(file_paths):
                success, result = self.book_manager.upload_book(group_name, file_path, start_index + i)
                if success:
                    success_count += 1
                    formatted_title = result
                    book_path = os.path.join(self.book_manager.data_path, group_name, formatted_title)
                    initial_metadata = {"status": "未处理", "chapters": []}
                    self.book_manager.save_book_metadata(book_path, initial_metadata)
                else:
                    error_messages.append(f"{os.path.basename(file_path)}: {result}")
            
            self.load_books()
            
            if success_count > 0:
                QMessageBox.information(self, "成功", f"{success_count} 本书籍上传成功")
            
            if error_messages:
                QMessageBox.warning(self, "上传失败", "\n".join(error_messages))

    def save_chapters(self):
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

    def delete_selected_chapter(self):
        current_row = self.chapter_table.currentRow()
        if current_row >= 0:
            self.chapter_table.removeRow(current_row)

    def delete_before_chapters(self):
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
        if row == -1:
            row = self.chapter_table.rowCount()
        self.chapter_table.insertRow(row)
        self.chapter_table.setItem(row, 0, QTableWidgetItem("新章节"))
        self.chapter_table.setItem(row, 1, QTableWidgetItem("0"))
        self.chapter_table.setItem(row, 2, QTableWidgetItem("0"))

    def show_chapter_context_menu(self, position):
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

    def show_context_menu(self, position):
        item = self.book_tree_widget.itemAt(position)
        if not item:
            return

        menu = QMenu()
        if item.parent() is None:
            delete_group_action = menu.addAction("删除书籍组")
            action = menu.exec(self.book_tree_widget.mapToGlobal(position))
            if action == delete_group_action:
                self.delete_book_group(item)
        else:
            delete_book_action = menu.addAction("删除书籍")
            action = menu.exec(self.book_tree_widget.mapToGlobal(position))
            if action == delete_book_action:
                self.delete_book(item)

    def delete_book_group(self, item):
        group_name = item.text(0)
        reply = QMessageBox.question(self, "确认删除", f"确定要删除书籍组 '{group_name}' 吗？\n这将删除该组下的所有书籍。",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            success, message = self.book_manager.delete_book_group(group_name)
            if success:
                self.load_books()
                QMessageBox.information(self, "成功", "书籍组已删除")
            else:
                QMessageBox.warning(self, "错误", message)

    def delete_book(self, item):
        book_path = item.data(0, Qt.UserRole + 1)
        book_title = item.data(0, Qt.UserRole + 2)
        reply = QMessageBox.question(self, "确认删除", f"确定要删除书籍 '{book_title}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            success, message = self.book_manager.delete_book(book_path)
            if success:
                self.load_books()
                QMessageBox.information(self, "成功", "书籍已删除")
            else:
                QMessageBox.warning(self, "错误", message)

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

    def update_book_info(self):
        """更新书籍信息显示"""
        if not self.current_book_path:
            self.book_info_label.setText("请选择一本书籍")
            self.split_chapters_button.setEnabled(False)
            return

        # 获取书籍基本信息
        book_title = os.path.basename(self.current_book_path)
        metadata = self.book_manager.get_book_metadata(self.current_book_path)
        
        info_text = f"书名: {book_title}\n"
        
        if metadata:
            status = metadata.get("status", "未知")
            info_text += f"状态: {status}\n"
            
            chapters = metadata.get("chapters", [])
            if chapters:
                info_text += f"章节数: {len(chapters)}\n"
                
                # 显示前几个章节名称
                chapter_names = [ch.get("title", "未命名") for ch in chapters[:3]]
                if len(chapters) > 3:
                    chapter_names.append("...")
                info_text += f"章节: {', '.join(chapter_names)}\n"
        else:
            info_text += "状态: 未处理\n"

        # 检查PDF文件是否存在
        pdf_path = os.path.join(self.current_book_path, "original.pdf")
        if os.path.exists(pdf_path):
            try:
                from pypdf import PdfReader
                reader = PdfReader(pdf_path)
                info_text += f"总页数: {len(reader.pages)}\n"
            except:
                info_text += "总页数: 无法读取\n"
        else:
            info_text += "PDF文件: 不存在\n"

        self.book_info_label.setText(info_text)
        
        # 更新按钮状态
        self.update_button_states()

    def update_button_states(self):
        """更新按钮的启用状态"""
        if not self.current_book_path:
            self.split_chapters_button.setEnabled(False)
            return

        # 检查是否有章节信息且PDF文件存在
        has_chapters = self.chapter_table.rowCount() > 0
        pdf_exists = os.path.exists(os.path.join(self.current_book_path, "original.pdf"))
        
        self.split_chapters_button.setEnabled(has_chapters and pdf_exists)

    def log_message(self, message):
        """添加日志消息"""
        from datetime import datetime
        from PySide6.QtGui import QTextCursor
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text_edit.append(formatted_message)
        
        # 自动滚动到底部
        cursor = self.log_text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text_edit.setTextCursor(cursor)

    def clear_log(self):
        """清空日志"""
        self.log_text_edit.clear()
        self.log_message("日志已清空")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
