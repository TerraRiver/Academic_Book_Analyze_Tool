import json
import os
import re
from typing import Dict, List, Any, Optional

class JSONToMarkdownConverter:
    """将MinerU解析的JSON结果转换为带页码的Markdown格式"""
    
    def __init__(self):
        pass
    
    def parse_mineru_json_to_markdown(self, json_file_path: str, original_start_page: int = 1) -> str:
        """
        将MinerU解析出的JSON文件转换为Markdown格式，并添加页码标识。
        
        Args:
            json_file_path (str): JSON文件的路径
            original_start_page (int): 该章节在原书中的起始页码
            
        Returns:
            str: 转换后的Markdown内容
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            markdown_content = []
            current_page = -1
            
            # 处理content_list格式的JSON（数组格式）
            if isinstance(data, list):
                for item in data:
                    # 获取页码
                    page_idx = item.get('page_idx', 0)
                    actual_page = original_start_page + page_idx
                    
                    # 如果是新的页面，添加页面分隔符
                    if actual_page != current_page:
                        if current_page != -1:  # 不是第一页
                            markdown_content.append("\n")
                        markdown_content.append(f"---\n**[第 {actual_page} 页]**\n")
                        current_page = actual_page
                    
                    # 处理内容项
                    block_content = self._process_content_item(item, actual_page)
                    if block_content:
                        markdown_content.append(block_content)
            
            # 处理旧格式的JSON（保持兼容性）
            elif isinstance(data, dict):
                # 处理文档标题（如果有的话）
                if 'title' in data:
                    markdown_content.append(f"# {data['title']}\n")
                
                # 处理页面内容
                if 'pages' in data:
                    for page_info in data['pages']:
                        # 获取页码，如果没有则使用索引
                        page_idx = page_info.get('page_idx', 0)
                        # 计算在原书中的实际页码
                        actual_page = original_start_page + page_idx
                        
                        markdown_content.append(f"\n---\n**[第 {actual_page} 页]**\n")
                        
                        # 处理该页面的各种元素
                        if 'blocks' in page_info:
                            for block in page_info['blocks']:
                                block_content = self._process_block(block, actual_page)
                                if block_content:
                                    markdown_content.append(block_content)
            
            return '\n'.join(markdown_content)
        
        except Exception as e:
            print(f"解析JSON文件时发生错误: {e}")
            return ""
    
    def _process_content_item(self, item: Dict[str, Any], current_page: int) -> str:
        """
        处理content_list格式中的单个内容项
        
        Args:
            item: 内容项数据
            current_page: 当前页码
            
        Returns:
            str: 处理后的Markdown内容
        """
        item_type = item.get('type', '')
        text_content = item.get('text', '').strip()
        
        if not text_content:
            return ""
        
        content_parts = []
        
        if item_type == 'text':
            # 检查是否有text_level字段（用于判断标题级别）
            text_level = item.get('text_level', 0)
            if text_level > 0:
                # 按text_level处理为标题
                level = min(text_level, 6)  # Markdown最多支持6级标题
                content_parts.append(f"{'#' * level} {text_content}")
            else:
                # 普通文本段落
                content_parts.append(text_content)
        
        elif item_type == 'title':
            # 处理标题类型
            content_parts.append(f"## {text_content}")
        
        else:
            # 其他类型默认作为普通文本处理
            content_parts.append(text_content)
        
        return '\n'.join(content_parts) + '\n'
    
    def _process_block(self, block: Dict[str, Any], current_page: int) -> str:
        """
        处理单个内容块
        
        Args:
            block: 内容块数据
            current_page: 当前页码
            
        Returns:
            str: 处理后的Markdown内容
        """
        block_type = block.get('type', '')
        content_parts = []
        
        if block_type == 'text':
            # 处理文本块
            text_content = block.get('text', '').strip()
            if text_content:
                # 为文本段落添加页码标识
                content_parts.append(f"{text_content}")
                content_parts.append(f"*[第{current_page}页]*\n")
        
        elif block_type == 'title':
            # 处理标题
            title_text = block.get('text', '').strip()
            if title_text:
                # 根据标题级别添加不同数量的#
                level = block.get('level', 2)
                content_parts.append(f"{'#' * level} {title_text}")
                content_parts.append(f"*[第{current_page}页]*\n")
        
        elif block_type == 'table':
            # 处理表格
            table_content = self._process_table_block(block)
            if table_content:
                content_parts.append(table_content)
                content_parts.append(f"*[第{current_page}页]*\n")
        
        elif block_type == 'image':
            # 处理图片
            image_info = block.get('image_info', {})
            if image_info:
                content_parts.append(f"![图片](data:image/png;base64,{image_info.get('base64', '')})")
                content_parts.append(f"*[第{current_page}页]*\n")
        
        elif block_type == 'formula':
            # 处理公式
            formula_text = block.get('latex', '').strip()
            if formula_text:
                content_parts.append(f"$$\n{formula_text}\n$$")
                content_parts.append(f"*[第{current_page}页]*\n")
        
        return '\n'.join(content_parts) if content_parts else ""
    
    def _process_table_block(self, table_block: Dict[str, Any]) -> str:
        """
        处理表格块，转换为Markdown表格格式。
        
        Args:
            table_block (dict): 表格块的数据
            
        Returns:
            str: Markdown格式的表格
        """
        try:
            # 获取表格数据
            table_data = table_block.get('table', {})
            rows = table_data.get('rows', [])
            
            if not rows:
                return ""
            
            markdown_table = []
            
            # 处理表头
            if len(rows) > 0:
                header_cells = []
                for cell in rows[0].get('cells', []):
                    cell_text = cell.get('text', '').strip().replace('\n', ' ')
                    header_cells.append(cell_text)
                
                if header_cells:
                    markdown_table.append('| ' + ' | '.join(header_cells) + ' |')
                    markdown_table.append('| ' + ' | '.join(['---'] * len(header_cells)) + ' |')
            
            # 处理数据行
            for row in rows[1:]:
                row_cells = []
                for cell in row.get('cells', []):
                    cell_text = cell.get('text', '').strip().replace('\n', ' ')
                    row_cells.append(cell_text)
                
                if row_cells:
                    markdown_table.append('| ' + ' | '.join(row_cells) + ' |')
            
            return '\n'.join(markdown_table) + '\n'
        
        except Exception as e:
            print(f"处理表格时发生错误: {e}")
            return ""
    
    def process_chapter_json_files(self, book_path: str, chapters: List[Dict],
                                 log_callback: Optional[callable] = None) -> bool:
        """
        批量处理章节的JSON文件，转换为Markdown。
        
        Args:
            book_path (str): 书籍路径
            chapters (List[Dict]): 章节信息列表
            log_callback: 日志回调函数
            
        Returns:
            bool: 是否处理成功
        """
        try:
            mineru_json_dir = os.path.join(book_path, "MinerU_json")
            output_markdown_dir = os.path.join(book_path, "chapters_markdown")
            
            if not os.path.exists(mineru_json_dir):
                if log_callback:
                    log_callback(f"MinerU JSON目录不存在: {mineru_json_dir}")
                return False
            
            # 创建输出目录
            os.makedirs(output_markdown_dir, exist_ok=True)
            
            if log_callback:
                log_callback("开始将JSON转换为Markdown...")
            
            processed_count = 0
            
            # 遍历所有章节
            for i, chapter in enumerate(chapters):
                chapter_title = chapter.get('title', f'Chapter_{i+1}')
                start_page = chapter.get('start_page', 1)
                
                # 使用新的、基于索引的命名规则
                chapter_dir_name = f"{i+1:02d}"
                chapter_json_dir = os.path.join(mineru_json_dir, chapter_dir_name)
                
                if log_callback:
                    log_callback(f"正在处理章节: {chapter_title}")
                
                if not os.path.exists(chapter_json_dir):
                    if log_callback:
                        log_callback(f"  - 警告: 章节目录不存在: {chapter_dir_name}")
                    continue
                
                # 查找该章节目录下的JSON文件（过滤掉layout.json，只处理content_list.json）
                json_files = []
                for root, dirs, files in os.walk(chapter_json_dir):
                    for file in files:
                        if file.endswith('_content_list.json'):
                            json_files.append(os.path.join(root, file))
                
                if not json_files:
                    if log_callback:
                        log_callback(f"  - 警告: 在 {chapter_dir_name} 中没有找到JSON文件")
                    continue
                
                # 处理找到的JSON文件
                for json_file in json_files:
                    if log_callback:
                        log_callback(f"  - 处理JSON文件: {os.path.basename(json_file)}")
                    
                    # 转换为Markdown
                    markdown_content = self.parse_mineru_json_to_markdown(json_file, start_page)
                    
                    if markdown_content:
                        # 使用新的、基于索引的命名规则生成输出文件名
                        output_filename = f"{i+1:02d}.md"
                        output_path = os.path.join(output_markdown_dir, output_filename)
                        
                        # 保存Markdown文件
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(markdown_content)
                        
                        if log_callback:
                            log_callback(f"  - 已生成: {output_filename}")
                        processed_count += 1
                        break  # 每个章节只处理第一个找到的JSON文件
                    else:
                        if log_callback:
                            log_callback(f"  - 转换失败: {os.path.basename(json_file)}")
            
            if log_callback:
                log_callback(f"JSON转Markdown完成! 共处理了 {processed_count} 个章节")
            
            return processed_count > 0
        
        except Exception as e:
            if log_callback:
                log_callback(f"批量处理JSON文件时发生错误: {e}")
            return False
    
    def convert_single_chapter(self, json_file_path: str, output_path: str, 
                             start_page: int = 1) -> bool:
        """
        转换单个章节的JSON文件为Markdown
        
        Args:
            json_file_path: JSON文件路径
            output_path: 输出Markdown文件路径
            start_page: 章节在原书中的起始页码
            
        Returns:
            bool: 是否转换成功
        """
        try:
            markdown_content = self.parse_mineru_json_to_markdown(json_file_path, start_page)
            
            if markdown_content:
                # 创建输出目录
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                return True
            else:
                return False
                
        except Exception as e:
            print(f"转换单个章节时发生错误: {e}")
            return False


# 测试代码
if __name__ == '__main__':
    converter = JSONToMarkdownConverter()
    
    # 示例用法
    test_book_path = "data/test_book"
    test_chapters = [
        {"title": "Chapter 1: Introduction", "start_page": 1, "end_page": 20},
        {"title": "Chapter 2: Theory", "start_page": 21, "end_page": 40}
    ]
    
    if os.path.exists(os.path.join(test_book_path, "MinerU_json")):
        print("开始批量转换JSON为Markdown...")
        success = converter.process_chapter_json_files(
            test_book_path, 
            test_chapters,
            log_callback=lambda msg: print(f"LOG: {msg}")
        )
        
        if success:
            print("转换完成!")
        else:
            print("转换失败!")
    else:
        print("测试目录不存在，请先运行MinerU解析步骤。")
