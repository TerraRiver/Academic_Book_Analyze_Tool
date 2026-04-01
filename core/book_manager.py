import os
import json
import shutil
from typing import List, Dict, Optional, Tuple
from .api_handler import APIHandler
from .report_generator import ReportGenerator

class BookManager:
    """管理书籍和章节处理流程"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_path = data_dir
        self.data_dir = data_dir  # 保持兼容性
        self.api_handler = None
        
        # 确保数据目录存在
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)

    def _get_api_handler(self) -> APIHandler:
        """延迟初始化API处理器，避免首次启动时因缺少Key而报错。"""
        if self.api_handler is None:
            self.api_handler = APIHandler()
        return self.api_handler
    
    def scan_book_groups(self) -> List[str]:
        """扫描所有书籍组"""
        if not os.path.exists(self.data_path):
            return []
        
        groups = []
        for item in os.listdir(self.data_path):
            item_path = os.path.join(self.data_path, item)
            if os.path.isdir(item_path):
                groups.append(item)
        return sorted(groups)
    
    def scan_books_in_group(self, group_name: str) -> List[str]:
        """扫描指定书籍组中的所有书籍"""
        group_path = os.path.join(self.data_path, group_name)
        if not os.path.exists(group_path):
            return []
        
        books = []
        for item in os.listdir(group_path):
            item_path = os.path.join(group_path, item)
            if os.path.isdir(item_path):
                books.append(item)
        return sorted(books)
    
    def create_book_group(self, group_name: str) -> Tuple[bool, str]:
        """创建新的书籍组"""
        if not group_name.strip():
            return False, "书籍组名称不能为空"
        
        group_path = os.path.join(self.data_path, group_name)
        if os.path.exists(group_path):
            return False, f"书籍组 '{group_name}' 已存在"
        
        try:
            os.makedirs(group_path)
            return True, "创建成功"
        except Exception as e:
            return False, f"创建失败: {str(e)}"
    
    def delete_book_group(self, group_name: str) -> Tuple[bool, str]:
        """删除书籍组及其下所有书籍"""
        group_path = os.path.join(self.data_path, group_name)
        if not os.path.exists(group_path):
            return False, f"书籍组 '{group_name}' 不存在"
        
        try:
            shutil.rmtree(group_path)
            return True, "删除成功"
        except Exception as e:
            return False, f"删除失败: {str(e)}"
    
    def upload_book(self, group_name: str, pdf_path: str, index: int = 0) -> Tuple[bool, str]:
        """上传书籍到指定书籍组"""
        if not os.path.exists(pdf_path):
            return False, f"PDF文件不存在: {pdf_path}"
        
        group_path = os.path.join(self.data_path, group_name)
        if not os.path.exists(group_path):
            return False, f"书籍组 '{group_name}' 不存在"
        
        # 生成书籍文件夹名称
        original_name = os.path.splitext(os.path.basename(pdf_path))[0]
        formatted_title = f"{index:03d}_{original_name}"
        book_path = os.path.join(group_path, formatted_title)
        
        try:
            # 创建书籍目录
            os.makedirs(book_path, exist_ok=True)
            
            # 复制PDF文件
            dest_pdf = os.path.join(book_path, "original.pdf")
            shutil.copy2(pdf_path, dest_pdf)
            
            # 创建初始元数据
            metadata = {
                "title": original_name,
                "status": "未处理",
                "upload_time": self._get_current_time()
            }
            self.save_book_metadata(book_path, metadata)
            
            return True, formatted_title
        except Exception as e:
            return False, f"上传失败: {str(e)}"
    
    def delete_book(self, book_path: str) -> Tuple[bool, str]:
        """删除指定书籍"""
        if not os.path.exists(book_path):
            return False, "书籍不存在"
        
        try:
            shutil.rmtree(book_path)
            return True, "删除成功"
        except Exception as e:
            return False, f"删除失败: {str(e)}"
    
    def get_book_metadata(self, book_path: str) -> Optional[Dict]:
        """获取书籍元数据"""
        metadata_path = os.path.join(book_path, "metadata.json")
        if not os.path.exists(metadata_path):
            return None
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def save_book_metadata(self, book_path: str, metadata: Dict) -> bool:
        """保存书籍元数据"""
        metadata_path = os.path.join(book_path, "metadata.json")
        try:
            existing_metadata = {}
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    existing_metadata = json.load(f)

            merged_metadata = existing_metadata.copy()
            merged_metadata.update(metadata)

            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(merged_metadata, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def get_book_list(self) -> List[Dict]:
        """获取所有书籍列表"""
        books = []
        for group_name in self.scan_book_groups():
            for book_title in self.scan_books_in_group(group_name):
                book_path = os.path.join(self.data_path, group_name, book_title)
                metadata = self.get_book_metadata(book_path)
                books.append({
                    "path": book_path,
                    "group": group_name,
                    "title": book_title,
                    "metadata": metadata
                })
        return books
    
    def get_book_chapters(self, book_path: str) -> List[Dict]:
        """
        获取书籍章节列表，从metadata.json中读取
        """
        metadata = self.get_book_metadata(book_path)
        if metadata and 'chapters' in metadata:
            # 为每个章节添加一个从0开始的索引，方便后续处理
            for i, chapter in enumerate(metadata['chapters']):
                chapter['index'] = i + 1 # 从1开始的章节序号
            return metadata['chapters']
        return []
    
    def process_book_chapters(self, book_path: str, 
                            status_callback: Optional[callable] = None,
                            log_callback: Optional[callable] = None) -> bool:
        """处理书籍章节(MinerU解析)"""
        chapters = self.get_book_chapters(book_path)
        return self._get_api_handler().process_book_chapters(
            book_path, chapters, status_callback, log_callback
        )
    
    def analyze_book_chapters(self, book_path: str,
                            status_callback: Optional[callable] = None,
                            log_callback: Optional[callable] = None) -> bool:
        """分析书籍章节(LLM解析)"""
        chapters = self.get_book_chapters(book_path)
        return self._get_api_handler().analyze_chapters(
            book_path, chapters, status_callback, log_callback
        )
    
    def generate_book_report(self, book_path: str,
                             status_callback: Optional[callable] = None,
                             log_callback: Optional[callable] = None) -> Optional[str]:
        """
        生成书籍的Word报告。
        
        Args:
            book_path: 书籍的路径。
            status_callback: 状态更新回调。
            log_callback: 日志回调。
            
        Returns:
            生成的报告文件路径，如果失败则返回None。
        """
        metadata = self.get_book_metadata(book_path)
        if not metadata:
            if log_callback:
                log_callback(f"无法获取书籍元数据: {book_path}")
            return None
        
        book_title = metadata.get('title', os.path.basename(book_path))
        chapters = self.get_book_chapters(book_path) # 获取章节信息
        
        # 创建ReportGenerator实例
        report_generator = ReportGenerator(book_path, log_callback)
        
        return report_generator.generate_report(book_title, chapters)
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
