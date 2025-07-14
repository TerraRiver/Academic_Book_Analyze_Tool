import os
import shutil
import json

class BookManager:
    def __init__(self, data_path="data"):
        self.data_path = data_path

    def scan_book_groups(self):
        """扫描 data 目录以查找书籍组（即子目录）"""
        if not os.path.exists(self.data_path):
            return []
        
        book_groups = []
        for item in os.listdir(self.data_path):
            if os.path.isdir(os.path.join(self.data_path, item)):
                book_groups.append(item)
        return book_groups

    def create_book_group(self, group_name):
        """创建新的书籍组"""
        if not group_name:
            return False, "书籍组名称不能为空"
        
        group_path = os.path.join(self.data_path, group_name)
        if os.path.exists(group_path):
            return False, "书籍组已存在"
            
        try:
            os.makedirs(group_path)
            return True, ""
        except Exception as e:
            return False, f"创建失败: {e}"

    def upload_book(self, group_name, pdf_path, book_index):
        """上传书籍到指定的书籍组，并自动编号"""
        if not group_name:
            return False, "请先选择一个书籍组"
        if not pdf_path:
            return False, "请选择一个 PDF 文件"

        group_path = os.path.join(self.data_path, group_name)
        
        next_book_number = book_index + 1

        original_title = os.path.splitext(os.path.basename(pdf_path))[0]
        # 格式化书名，例如：01_BookTitle
        formatted_title = f"{next_book_number:02d}_{original_title}"
        
        book_dir = os.path.join(group_path, formatted_title)
        
        if os.path.exists(book_dir):
            # 如果编号后的目录仍然存在，尝试下一个编号
            # 这是一个简单的处理方式，更复杂的场景可能需要不同的策略
            return False, f"书籍 '{formatted_title}' 已存在"

        try:
            os.makedirs(book_dir)
            shutil.copy(pdf_path, os.path.join(book_dir, "original.pdf"))
            return True, formatted_title
        except Exception as e:
            return False, f"上传失败: {e}"

    def scan_books_in_group(self, group_name):
        """扫描书籍组以查找书籍"""
        group_path = os.path.join(self.data_path, group_name)
        if not os.path.isdir(group_path):
            return []
            
        books = []
        for item in os.listdir(group_path):
            if os.path.isdir(os.path.join(group_path, item)):
                books.append(item)
        return books

    def get_book_metadata(self, book_path):
        """获取书籍的元数据"""
        metadata_path = os.path.join(book_path, "metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def save_book_metadata(self, book_path, metadata):
        """保存书籍的元数据"""
        metadata_path = os.path.join(book_path, "metadata.json")
        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=4)
            return True
        except IOError:
            return False

    def delete_book(self, book_path):
        """删除一本书籍（及其目录）"""
        try:
            shutil.rmtree(book_path)
            return True, ""
        except Exception as e:
            return False, f"删除书籍失败: {e}"

    def delete_book_group(self, group_name):
        """删除一个书籍组（及其目录）"""
        group_path = os.path.join(self.data_path, group_name)
        try:
            shutil.rmtree(group_path)
            return True, ""
        except Exception as e:
            return False, f"删除书籍组失败: {e}"
