from pypdf import PdfReader, PdfWriter
import os


def enrich_chapters(chapters: list) -> list:
    """
    为章节列表补充层级路径、父子关系与叶子节点信息。
    返回的新列表保留原顺序，不修改原始输入。
    """
    enriched = []
    stack = []

    for i, chapter in enumerate(chapters):
        chapter_copy = dict(chapter)
        level = chapter_copy.get("level", 1)

        while stack and stack[-1].get("level", 1) >= level:
            stack.pop()

        parent = stack[-1] if stack else None
        path_titles = [node.get("title", "") for node in stack] + [chapter_copy.get("title", "")]

        chapter_copy["path_titles"] = path_titles
        chapter_copy["display_title"] = " > ".join(filter(None, path_titles))
        chapter_copy["parent_index"] = parent.get("_source_index") if parent else None
        chapter_copy["_source_index"] = i

        enriched.append(chapter_copy)
        stack.append(chapter_copy)

    for i, chapter in enumerate(enriched):
        level = chapter.get("level", 1)
        next_level = enriched[i + 1].get("level", 1) if i + 1 < len(enriched) else 0
        chapter["is_leaf"] = next_level <= level

    return enriched


def get_bookmarks(pdf_path: str, max_level: int = 3) -> list:
    """
    从 PDF 文件中提取书签（大纲），支持最多 max_level 级层次。

    返回列表，每项包含:
        title     - 书签标题
        page      - 起始页码（1-based）
        end_page  - 结束页码（1-based）
        level     - 层级（1 ~ max_level）
    """
    bookmarks = []
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        def process_outline(items, level=1):
            if level > max_level:
                return
            for item in items:
                if isinstance(item, list):
                    # 子书签列表，递归处理，层级 +1
                    process_outline(item, level + 1)
                else:
                    try:
                        page = reader.get_destination_page_number(item) + 1
                        bookmarks.append({
                            "title": item.title,
                            "page": page,
                            "level": level,
                        })
                    except Exception:
                        pass

        process_outline(reader.outline)

        # 为每个书签计算结束页：找到下一个同级或更高级的书签
        for i, bm in enumerate(bookmarks):
            next_page = total_pages + 1
            for j in range(i + 1, len(bookmarks)):
                if bookmarks[j]["level"] <= bm["level"]:
                    next_page = bookmarks[j]["page"]
                    break
            bm["end_page"] = next_page - 1

    except Exception as e:
        print(f"读取书签时出错: {e}")
    return bookmarks


def get_leaf_chapters(chapters: list) -> list:
    """
    筛选叶子章节（无直接子章节），作为 OCR / LLM 分析的实际处理单元。

    判断规则：若下一条目的 level <= 本条目的 level，则本条目为叶子节点。
    若章节列表不含层级信息（旧数据 level 均默认为 1），全部视为叶子节点（向后兼容）。
    """
    return [chapter for chapter in enrich_chapters(chapters) if chapter.get("is_leaf")]


def get_non_leaf_chapters(chapters: list) -> list:
    """返回所有非叶子章节。"""
    return [chapter for chapter in enrich_chapters(chapters) if not chapter.get("is_leaf")]


def split_pdf_by_chapters(original_pdf_path: str, chapters: list, output_dir: str):
    """
    根据章节信息切分 PDF，仅切分叶子章节。
    输出文件按序命名为 01.pdf, 02.pdf …
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        reader = PdfReader(original_pdf_path)
        leaf_chapters = get_leaf_chapters(chapters)

        for seq_idx, chapter in enumerate(leaf_chapters):
            writer = PdfWriter()
            start_page = chapter["start_page"]
            end_page = chapter["end_page"]

            for page_num in range(start_page - 1, end_page):
                writer.add_page(reader.pages[page_num])

            output_filename = os.path.join(output_dir, f"{seq_idx + 1:02d}.pdf")
            writer.add_metadata({"/Title": chapter["title"]})
            with open(output_filename, "wb") as f:
                writer.write(f)

        return True, ""
    except Exception as e:
        return False, f"切分PDF时出错: {e}"
