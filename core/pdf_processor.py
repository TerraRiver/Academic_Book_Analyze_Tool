from pypdf import PdfReader, PdfWriter
import os

def get_bookmarks(pdf_path: str) -> list:
    """
    从 PDF 文件中提取书签（大纲）。

    :param pdf_path: PDF 文件的路径。
    :return: 一个包含书签信息的列表，每个元素是一个元组 (title, page_number)。
    """
    bookmarks = []
    try:
        reader = PdfReader(pdf_path)
        for item in reader.outline:
            # 我们只处理顶层书签
            if isinstance(item, list):
                # 忽略嵌套书签
                continue
            bookmarks.append({
                "title": item.title,
                "page": reader.get_destination_page_number(item) + 1 # pypdf 页码从0开始，我们转换为从1开始
            })
    except Exception as e:
        print(f"读取书签时出错: {e}")
    return bookmarks

def split_pdf_by_chapters(original_pdf_path: str, chapters: list, output_dir: str):
    """
    根据章节信息切分PDF。

    :param original_pdf_path: 原始PDF文件的路径。
    :param chapters: 包含章节信息的列表，每个元素是一个字典，包含 title, start_page, end_page。
    :param output_dir: 切分后的PDF文件的输出目录。
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        reader = PdfReader(original_pdf_path)
        
        for i, chapter in enumerate(chapters):
            writer = PdfWriter()
            start_page = chapter["start_page"]
            end_page = chapter["end_page"]
            
            # 将页码从1开始转换回0开始
            for page_num in range(start_page - 1, end_page):
                writer.add_page(reader.pages[page_num])
            
            # 清理文件名中的非法字符并限制长度
            safe_title = "".join(c for c in chapter['title'] if c.isalnum() or c in (' ', '_')).rstrip()
            # 限制标题长度，确保最终文件名不会太长（考虑到data_id有128字符限制）
            # 格式是：02d_safe_title.pdf，所以safe_title部分最好不超过100字符
            if len(safe_title) > 100:
                safe_title = safe_title[:100].rstrip()
            output_filename = os.path.join(output_dir, f"{i+1:02d}_{safe_title}.pdf")
            
            with open(output_filename, "wb") as f:
                writer.write(f)
        return True, ""
    except Exception as e:
        return False, f"切分PDF时出错: {e}"
