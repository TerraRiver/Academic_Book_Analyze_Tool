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
            
            # 使用简单、健壮的索引作为文件名，避免非法字符问题
            output_filename = os.path.join(output_dir, f"{i+1:02d}.pdf")
            
            # 将章节标题添加到PDF元数据中，以便追溯
            writer.add_metadata({
                "/Title": chapter['title']
            })

            with open(output_filename, "wb") as f:
                writer.write(f)
        return True, ""
    except Exception as e:
        return False, f"切分PDF时出错: {e}"
