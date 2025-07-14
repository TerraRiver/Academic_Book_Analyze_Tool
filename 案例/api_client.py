import requests
import openai
import time
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import config  # 导入我们更新后的配置文件

# --- 配置 OpenAI 客户端 ---
# (这部分保持不变)
openai.api_key = config.OPENAI_API_KEY
if config.OPENAI_API_BASE_URL:
    openai.api_base = config.OPENAI_API_BASE_URL

# --- 配置 DeepSeek 客户端 ---
if config.DEEPSEEK_API_KEY and "YOUR" not in config.DEEPSEEK_API_KEY:
    deepseek_client = openai.OpenAI(
        api_key=config.DEEPSEEK_API_KEY,
        base_url=config.DEEPSEEK_API_BASE_URL
    )
else:
    deepseek_client = None

# ==============================================================================
# MinerU V4 API 异步流程实现
# ==============================================================================

def request_upload_url(filenames: list, headers: dict, enable_ocr: bool, enable_formula: bool, enable_table: bool, language: str) -> tuple:
    """第一步：为一批文件申请上传URL。"""
    print("1. 正在申请文件上传链接...")
    
    # 根据官方示例，为每个文件添加 data_id (这里我们使用文件名作为唯一标识)
    files_payload = []
    for name in filenames:
        base_name = os.path.basename(name)
        data_id = os.path.splitext(base_name)[0]
        files_payload.append({
            "name": base_name,
            "is_ocr": enable_ocr,
            "data_id": data_id
        })

    payload = {
        "enable_formula": enable_formula,
        "language": language,
        "enable_table": enable_table,
        "files": files_payload
    }
    
    print(f"   - 请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(config.MINERU_URL_APPLY_UPLOAD, headers=headers, json=payload, timeout=30)
        print(f"   - 响应状态码: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   - 响应内容: {response.text}")
            response.raise_for_status()
        
        result = response.json()
        print(f"   - 响应数据: {json.dumps(result, indent=2, ensure_ascii=False, default=str)}")
        
        if result.get("code") == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            print(f"   - 成功获取 batch_id: {batch_id}")
            print(f"   - 获取到 {len(urls)} 个上传URL")
            return batch_id, urls
        else:
            error_msg = result.get('msg', '未知错误')
            print(f"   - API返回错误: {error_msg}")
            raise Exception(f"申请上传URL失败: {error_msg}")
            
    except requests.exceptions.RequestException as e:
        print(f"   - 网络请求失败: {e}")
        raise Exception(f"网络请求失败: {e}")
    except json.JSONDecodeError as e:
        print(f"   - JSON解析失败: {e}")
        print(f"   - 响应内容: {response.text}")
        raise Exception(f"响应JSON解析失败: {e}")
    except Exception as e:
        print(f"   - 未知错误: {e}")
        raise

def _upload_single_file(url: str, file_path: str):
    """上传单个文件到给定的URL。"""
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    try:
        print(f"   - 开始上传: {file_name} ({file_size / 1024 / 1024:.2f} MB)")
        
        with open(file_path, 'rb') as f:
            response = requests.put(url, data=f, timeout=600)
            print(f"   - 上传响应状态码: {response.status_code}")
            
            if response.status_code not in [200, 201]:
                print(f"   - 上传响应内容: {response.text}")
            
            response.raise_for_status()
            return f"   - [成功] {file_name}"
            
    except requests.exceptions.Timeout:
        return f"   - [超时] {file_name}: 上传超时"
    except requests.exceptions.RequestException as e:
        return f"   - [失败] {file_name}: 网络错误 - {e}"
    except Exception as e:
        return f"   - [失败] {file_name}: 未知错误 - {e}"

def upload_files(file_paths: list, upload_urls: list):
    """第二步：并行上传所有文件。"""
    print("2. 正在上传文件...")
    
    # 假设 API 返回的 upload_urls 列表与我们发送的 file_paths 列表顺序一致。
    if len(file_paths) != len(upload_urls):
        error_msg = f"文件列表数量 ({len(file_paths)}) 与返回的URL数量 ({len(upload_urls)}) 不匹配。"
        print(f"   - 错误: {error_msg}")
        raise ValueError(error_msg)

    upload_results = []
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 使用 zip 将文件路径和上传URL直接配对
        future_to_url = {executor.submit(_upload_single_file, url, path): (url, path) for path, url in zip(file_paths, upload_urls)}
        
        for future in as_completed(future_to_url):
            result_message = future.result()
            print(result_message)
            upload_results.append(result_message)
            
            if "[失败]" in result_message or "[超时]" in result_message:
                failed_count += 1
    
    if failed_count > 0:
        print(f"   - 警告: {failed_count} 个文件上传失败")
        # 可以选择是否继续，这里我们继续处理但记录警告
    
    print(f"   - 上传完成，成功: {len(file_paths) - failed_count}, 失败: {failed_count}")
    return True # 表示上传任务已全部提交

def poll_for_results(batch_id: str, headers: dict, status_callback=None, poll_interval=10, max_attempts=60) -> dict:
    """第三步：轮询获取最终的解析结果。"""
    print(f"3. 开始轮询结果 (batch_id: {batch_id})...")
    result_url = f"{config.MINERU_URL_GET_RESULT}/{batch_id}"
    
    for attempt in range(max_attempts):
        try:
            print(f"   - 正在查询... (第 {attempt + 1} 次)")
            
            response = requests.get(result_url, headers=headers, timeout=30)
            print(f"   - 查询响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   - 查询响应内容: {response.text}")
                response.raise_for_status()
            
            result = response.json()
            
            if result.get("code") == 0:
                data = result.get("data", {})
                # 根据最新文档，结果列表在 'extract_result' 键中
                results_list = data.get("extract_result", [])
                
                if not results_list:
                    print(f"   - 警告: 没有找到解析结果 (attempt {attempt + 1})")
                    time.sleep(poll_interval)
                    continue
                
                # 检查是否所有任务都已完成
                all_done = all(item.get("state") == "done" for item in results_list)
                
                if all_done and results_list:
                    print("   - 所有任务解析成功！")
                    # 将结果列表转换为以文件名为键的字典
                    results_dict = {item.get('file_name'): item for item in results_list}
                    
                    # 打印结果摘要
                    print(f"   - 解析结果摘要:")
                    for filename, item in results_dict.items():
                        zip_url = item.get('full_zip_url', '无')
                        print(f"     * {filename}: {zip_url}")
                    
                    return results_dict

                # 检查是否有任何任务失败
                failed_tasks = [item for item in results_list if item.get("state") == "failed"]
                if failed_tasks:
                    error_messages = [f"文件 '{t.get('file_name')}': {t.get('err_msg', '未知错误')}" for t in failed_tasks]
                    error_msg = f"解析任务失败:\n" + "\n".join(error_messages)
                    print(f"   - 错误: {error_msg}")
                    raise Exception(error_msg)

                # 打印当前每个文件的状态
                current_statuses = {item.get('file_name'): item.get('state') for item in results_list}
                status_summary = ", ".join(f"{k}: {v}" for k, v in current_statuses.items())
                print(f"   - 当前各文件状态: {status_summary}")
                
                if status_callback:
                    try:
                        status_callback(current_statuses)
                    except Exception as e:
                        print(f"   - 状态回调函数出错: {e}")
                
                time.sleep(poll_interval)
            else:
                error_msg = result.get('msg', '未知错误')
                print(f"   - API返回错误: {error_msg}")
                raise Exception(f"查询结果API返回错误: {error_msg}")
                
        except requests.exceptions.RequestException as e:
            print(f"   - 网络请求失败 (attempt {attempt + 1}): {e}")
            if attempt < max_attempts - 1:
                time.sleep(poll_interval)
                continue
            else:
                raise Exception(f"网络请求持续失败: {e}")
        except json.JSONDecodeError as e:
            print(f"   - JSON解析失败 (attempt {attempt + 1}): {e}")
            if attempt < max_attempts - 1:
                time.sleep(poll_interval)
                continue
            else:
                raise Exception(f"响应JSON解析失败: {e}")
        except Exception as e:
            print(f"   - 轮询过程中发生错误 (attempt {attempt + 1}): {e}")
            raise
            
    raise TimeoutError(f"轮询超时，无法在规定时间内获取解析结果。已尝试 {max_attempts} 次，每次间隔 {poll_interval} 秒。")


def process_chapters_with_mineru(
    chapter_file_paths: list, 
    enable_ocr: bool, 
    enable_formula: bool, 
    enable_table: bool, 
    language: str,
    status_callback=None
) -> dict:
    """
    使用 MinerU V4 API 处理一批章节PDF文件的主函数。

    Args:
        chapter_file_paths (list): 所有切分好的章节PDF文件的本地路径列表。
        enable_ocr (bool): 是否启用 OCR。
        enable_formula (bool): 是否启用公式识别。
        enable_table (bool): 是否启用表格识别。
        language (str): 文档语言。
        status_callback (function, optional): 用于接收状态更新的回调函数。

    Returns:
        dict: 解析结果，键为原始文件名，值为解析后的JSON数据。
              如果处理失败，则返回空字典。
    """
    if config.MINERU_API_KEY == "YOUR_API_KEY_HERE":
        print("错误: 请在 config.py 文件中配置您的 MINERU_API_KEY。")
        return {}

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {config.MINERU_API_KEY}'
    }

    print(f"开始处理 {len(chapter_file_paths)} 个章节文件...")
    print(f"参数: OCR={enable_ocr}, 公式={enable_formula}, 表格={enable_table}, 语言={language}")

    try:
        # 步骤 1: 申请上传链接
        batch_id, upload_urls = request_upload_url(
            chapter_file_paths, headers, enable_ocr, enable_formula, enable_table, language
        )
        
        # 步骤 2: 上传文件
        upload_files(chapter_file_paths, upload_urls)
        
        # 步骤 3: 轮询结果
        final_results = poll_for_results(batch_id, headers, status_callback=status_callback)
        
        print("\n所有章节处理完成！")
        return final_results

    except Exception as e:
        print(f"\n处理流程中断，发生错误: {e}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        print(f"详细堆栈: {traceback.format_exc()}")
        return {}


# ==============================================================================
# LLM 分析接口
# ==============================================================================
def analyze_chapter_with_llm(markdown_content: str, system_prompt: str, model_name: str, llm_params: dict) -> str:
    """
    使用配置好的LLM模型分析单个Markdown章节内容。

    Args:
        markdown_content (str): 要分析的章节的Markdown全文。
        system_prompt (str): 指导模型行为的系统提示词。
        model_name (str): 要使用的模型名称。
        llm_params (dict): 包含temperature, max_tokens等API参数的字典。

    Returns:
        str: LLM返回的分析结果。
        
    Raises:
        Exception: 如果客户端未初始化或API调用失败。
    """
    if not deepseek_client:
        raise Exception("DeepSeek客户端未初始化。请检查config.py中的DEEPSEEK_API_KEY。")

    # 格式化用户输入
    final_user_prompt = config.LLM_ANALYSIS_USER_PROMPT_TEMPLATE.format(markdown_content=markdown_content)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": final_user_prompt},
    ]

    # 发送请求
    try:
        start_time = time.time()
        print(f"  > [LLM] 开始分析章节 (模型: {model_name})...")
        response = deepseek_client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=False,
            **llm_params
        )
        end_time = time.time()
        print(f"  < [LLM] 分析完成，耗时: {end_time - start_time:.2f} 秒。")
        return response.choices[0].message.content
    except Exception as e:
        print(f"调用LLM API时出错: {e}")
        # 将原始异常重新引发，以便上层可以捕获并处理
        raise
        
# ==============================================================================
# 遗留的旧版LLM调用函数 (可以考虑移除或重构)
# ==============================================================================
def call_llm_api(content: str, prompt: str = None, max_retries=3, delay=5) -> str:
    """调用大语言模型 API 进行文本分析。"""
    if not prompt:
        prompt = config.DEFAULT_PROMPT
    
    full_prompt = f"{prompt}\n\n---\n\n以下是需要分析的内容：\n\n{content}"

    for attempt in range(max_retries):
        try:
            completion = openai.ChatCompletion.create(
                model=config.LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是一个专业的文献分析助手。"},
                    {"role": "user", "content": full_prompt}
                ]
            )
            analysis_result = completion.choices[0].message['content']
            return analysis_result.strip()
        except openai.error.OpenAIError as e:
            print(f"调用 LLM API 时发生错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                print("调用 LLM API 失败，已达到最大重试次数。")
                return ""
    return ""

# --- 测试代码 ---
if __name__ == '__main__':
    # 注意: 测试前请确保：
    # 1. 在 config.py 中填入有效的 MINERU_API_KEY。
    # 2. 在项目根目录下存在一个名为 'output/test_book/pdf/' 的文件夹。
    # 3. 该文件夹下至少有一个PDF文件 (例如 'Chapter_1_Test.pdf')。
    
    print("--- 测试 MinerU V4 完整流程 ---")
    
    # 模拟的章节文件路径列表
    test_dir = "output/test_book/pdf"
    if os.path.exists(test_dir) and len(os.listdir(test_dir)) > 0:
        test_files = [os.path.join(test_dir, f) for f in os.listdir(test_dir) if f.endswith('.pdf')]
        print(f"找到 {len(test_files)} 个测试文件: {test_files}")
        
        # 测试时使用 config.py 中的默认值
        results = process_chapters_with_mineru(
            test_files,
            enable_ocr=config.MINERU_ENABLE_OCR,
            enable_formula=config.MINERU_ENABLE_FORMULA,
            enable_table=config.MINERU_ENABLE_TABLE,
            language=config.MINERU_LANGUAGE,
            status_callback=lambda s: print("回调状态更新:", s) # 添加一个简单的lambda测试回调
        )
        
        if results:
            print("\n--- MinerU API 调用成功 ---")
            # 只打印文件名和结果摘要，避免输出过多内容
            for filename, result_data in results.items():
                print(f"  - 文件 '{filename}' 的解析结果（摘要）:")
                # 此处可以根据实际返回的json结构打印关键信息
                print(json.dumps(result_data.get('full_zip_url'), indent=2, ensure_ascii=False, default=str))
        else:
            print("\n--- MinerU API 调用失败 ---")
    else:
        print(f"跳过 MinerU API 测试：请在 '{test_dir}' 目录下放置一些PDF文件。")
