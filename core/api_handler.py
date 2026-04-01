import requests
import time
import os
import json
import configparser
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable, Optional, Tuple
from .json_to_markdown import JSONToMarkdownConverter

DEFAULT_MINERU_BASE_URL = "https://mineru.net/api/v4"
DEFAULT_MINERU_LANGUAGE = "ch"
MINERU_LANGUAGE_OPTIONS = {"ch", "en", "auto"}
DEFAULT_MINERU_MODEL_VERSION = "pipeline"
MINERU_MODEL_VERSION_OPTIONS = {"pipeline", "vlm", "MinerU-HTML"}
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"
DEFAULT_ZENMUX_BASE_URL = "https://zenmux.ai/api/v1"
DEFAULT_ZENMUX_MODEL_NAME = "google/gemini-3.1-pro-preview"


def normalize_mineru_language(language: str) -> str:
    """兼容历史配置中的zh，并约束为MinerU支持的语言值。"""
    normalized = (language or DEFAULT_MINERU_LANGUAGE).strip().lower()
    if normalized == "zh":
        return DEFAULT_MINERU_LANGUAGE
    if normalized in MINERU_LANGUAGE_OPTIONS:
        return normalized
    return DEFAULT_MINERU_LANGUAGE


def normalize_mineru_model_version(model_version: str) -> str:
    """确保MinerU模型版本始终为官方文档支持的值。"""
    normalized = (model_version or DEFAULT_MINERU_MODEL_VERSION).strip()
    if normalized in MINERU_MODEL_VERSION_OPTIONS:
        return normalized
    return DEFAULT_MINERU_MODEL_VERSION


class ConfigManager:
    """配置管理器，从config.ini读取配置"""
    
    def __init__(self, config_file="config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        self.config.clear()
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
    
    def get_mineru_config(self) -> Dict:
        """获取MinerU配置"""
        if not self.config.has_section('MinerU'):
            return self._get_default_mineru_config()
        
        section = self.config['MinerU']
        return {
            'api_key': section.get('api_key', ''),
            'base_url': section.get('base_url', DEFAULT_MINERU_BASE_URL),
            'enable_ocr': section.getboolean('enable_ocr', True),
            'enable_formula': section.getboolean('enable_formula', True),
            'enable_table': section.getboolean('enable_table', True),
            'language': normalize_mineru_language(section.get('language', DEFAULT_MINERU_LANGUAGE)),
            'model_version': normalize_mineru_model_version(
                section.get('model_version', DEFAULT_MINERU_MODEL_VERSION)
            ),
            'poll_interval': section.getint('poll_interval', 10),
            'max_attempts': section.getint('max_attempts', 60)
        }
    
    def get_llm_config(self) -> Dict:
        """获取LLM配置"""
        if not self.config.has_section('LLM'):
            return {
                'provider': 'DeepSeek',
                'model_name': 'deepseek-chat',
                'temperature': 0.7,
                'max_tokens': 2000,
                'prompt': self._get_default_system_prompt(),
                'max_concurrent_calls': 5
            }
        
        section = self.config['LLM']
        return {
            'provider': section.get('provider', 'DeepSeek'),
            'model_name': section.get('model_name', 'deepseek-chat'),
            'temperature': section.getfloat('temperature', 0.7),
            'max_tokens': section.getint('max_tokens', 2000),
            'prompt': section.get('prompt', self._get_default_system_prompt()),
            'max_concurrent_calls': section.getint('max_concurrent_llm_calls', 5)
        }

    def get_provider_config(self, provider: str) -> Dict:
        """获取指定LLM提供商的配置"""
        section_name = provider
        if not self.config.has_section(section_name):
            if provider == "DeepSeek":
                return self._get_default_deepseek_config()
            elif provider == "Gemini":
                return self._get_default_gemini_config()
            elif provider == "Zenmux":
                return self._get_default_zenmux_config()
            return {}
            
        section = self.config[section_name]
        return {
            'api_key': section.get('api_key', ''),
            'base_url': section.get('base_url', '')
        }
    
    def _get_default_mineru_config(self) -> Dict:
        return {
            'api_key': '',
            'base_url': DEFAULT_MINERU_BASE_URL,
            'enable_ocr': True,
            'enable_formula': True,
            'enable_table': True,
            'language': DEFAULT_MINERU_LANGUAGE,
            'model_version': DEFAULT_MINERU_MODEL_VERSION,
            'poll_interval': 10,
            'max_attempts': 60
        }
    
    def _get_default_deepseek_config(self) -> Dict:
        return {
            'api_key': '',
            'base_url': DEFAULT_DEEPSEEK_BASE_URL
        }

    def _get_default_gemini_config(self) -> Dict:
        return {
            'api_key': '',
            'base_url': DEFAULT_GEMINI_BASE_URL
        }

    def _get_default_zenmux_config(self) -> Dict:
        return {
            'api_key': '',
            'base_url': DEFAULT_ZENMUX_BASE_URL
        }
    
    def _get_default_system_prompt(self) -> str:
        return """你是一个专业的学术文献分析助手。请仔细分析提供的章节内容，并按照以下要求进行总结：

1. 提取章节的核心观点和主要论述
2. 识别关键概念、理论和方法
3. 总结重要的数据、案例或实证证据
4. 指出作者的主要结论和建议
5. 标注重要信息的页码位置

请保持客观、准确，并确保分析结果结构清晰、逻辑严密。"""


class LLMAPI:
    """通用LLM API调用处理器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.llm_config = self.config_manager.get_llm_config()
        self.provider = self.llm_config['provider']
        self.provider_config = self.config_manager.get_provider_config(self.provider)
        
        if not self.provider_config.get('api_key'):
            raise ValueError(f"{self.provider} API Key未配置")

    def analyze_text(self, text: str) -> Optional[Dict]:
        """
        使用所选的LLM API分析文本，并加入指数退避重试机制。
        
        Args:
            text: 要分析的文本内容
            
        Returns:
            API响应字典，包含分析结果
        """
        max_retries = 3
        base_backoff = 1  # seconds

        for attempt in range(max_retries):
            try:
                if self.provider == "DeepSeek":
                    return self._analyze_with_deepseek(text)
                elif self.provider == "Gemini":
                    return self._analyze_with_gemini(text)
                elif self.provider == "Zenmux":
                    return self._analyze_with_zenmux(text)
                else:
                    raise NotImplementedError(f"不支持的LLM提供商: {self.provider}")
            except requests.exceptions.RequestException as e:
                # 只对特定的服务器错误 (5xx) 进行重试
                if e.response is not None and 500 <= e.response.status_code < 600:
                    if attempt < max_retries - 1:
                        wait_time = base_backoff * (2 ** attempt) + (os.urandom(1)[0] / 255.0) # 添加抖动
                        print(f"API调用失败 (尝试 {attempt + 1}/{max_retries})，状态码: {e.response.status_code}。将在 {wait_time:.2f} 秒后重试...")
                        time.sleep(wait_time)
                    else:
                        raise Exception(f"{self.provider} API请求在 {max_retries} 次尝试后仍然失败: {e}")
                else:
                    # 对于客户端错误，尽量附带响应体，便于定位模型权限或鉴权问题
                    raise Exception(self._format_request_exception(e))
        return None # 如果循环结束仍未成功，理论上不会执行到这里

    def _format_request_exception(self, error: requests.exceptions.RequestException) -> str:
        """为HTTP异常补充状态码和响应体摘要，便于排查供应商错误。"""
        response = getattr(error, 'response', None)
        if response is None:
            return str(error)

        response_preview = response.text.strip()
        if len(response_preview) > 500:
            response_preview = response_preview[:500] + "..."

        if response_preview:
            return f"{response.status_code} {response.reason}: {response_preview}"
        return f"{response.status_code} {response.reason}: {error}"

    def _analyze_with_deepseek(self, text: str) -> Optional[Dict]:
        """使用DeepSeek API分析"""
        url = f"{self.provider_config['base_url']}/v1/chat/completions"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.provider_config['api_key']}"
        }
        payload = {
            "model": self.llm_config['model_name'],
            "messages": [
                {"role": "system", "content": self.llm_config['prompt']},
                {"role": "user", "content": text}
            ],
            "temperature": self.llm_config['temperature'],
            "max_tokens": self.llm_config['max_tokens']
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        # 统一返回格式
        result = response.json()
        return {'content': result['choices'][0]['message']['content']}

    def _analyze_with_gemini(self, text: str) -> Optional[Dict]:
        """使用Gemini API分析"""
        url = f"{self.provider_config['base_url']}/v1beta/models/{self.llm_config['model_name']}:generateContent?key={self.provider_config['api_key']}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{"parts": [{"text": f"{self.llm_config['prompt']}\n\n{text}"}]}],
            "generationConfig": {
                "temperature": self.llm_config['temperature'],
                "maxOutputTokens": self.llm_config['max_tokens']
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        # 统一返回格式
        result = response.json()
        return {'content': result['candidates'][0]['content']['parts'][0]['text']}

    def _analyze_with_zenmux(self, text: str) -> Optional[Dict]:
        """使用Zenmux OpenAI兼容接口分析。"""
        url = f"{self.provider_config['base_url']}/chat/completions"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.provider_config['api_key']}"
        }
        payload = {
            "model": self.llm_config['model_name'] or DEFAULT_ZENMUX_MODEL_NAME,
            "messages": [
                {"role": "system", "content": self.llm_config['prompt']},
                {"role": "user", "content": text}
            ],
            "temperature": self.llm_config['temperature'],
            "max_completion_tokens": self.llm_config['max_tokens']
        }

        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return {'content': result['choices'][0]['message']['content']}


class MinerUAPI:
    """MinerU API调用处理器"""

    MAX_FILES_PER_BATCH = 200
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.mineru_config = config_manager.get_mineru_config()
        
        # 构建API URLs
        base_url = self.mineru_config['base_url']
        self.upload_url = f"{base_url}/file-urls/batch"
        self.result_url_template = f"{base_url}/extract-results/batch"
        
        # HTTP headers
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.mineru_config["api_key"]}'
        }
    
    def process_chapters(self, chapter_files: List[str], 
                        status_callback: Optional[Callable] = None,
                        log_callback: Optional[Callable] = None) -> Dict:
        """
        处理章节PDF文件
        
        Args:
            chapter_files: 章节PDF文件路径列表
            status_callback: 状态更新回调函数
            log_callback: 日志回调函数
            
        Returns:
            处理结果字典，键为文件名，值为解析结果
        """
        if not self.mineru_config['api_key']:
            error_msg = "MinerU API Key未配置，请在设置中配置API Key"
            if log_callback:
                log_callback(error_msg)
            return {}
        
        if log_callback:
            log_callback(
                f"开始处理 {len(chapter_files)} 个章节文件，MinerU模型版本: "
                f"{self.mineru_config['model_version']}"
            )
                
        try:
            results = {}
            chapter_file_batches = self._split_batches(chapter_files, self.MAX_FILES_PER_BATCH)

            if len(chapter_file_batches) > 1 and log_callback:
                log_callback(
                    f"根据MinerU官方限制，已拆分为 {len(chapter_file_batches)} 个批次提交。"
                )

            for batch_index, batch_files in enumerate(chapter_file_batches, start=1):
                if log_callback:
                    log_callback(
                        f"开始处理第 {batch_index}/{len(chapter_file_batches)} 批，"
                        f"共 {len(batch_files)} 个文件。"
                    )

                # 步骤1: 申请上传链接
                batch_id, upload_urls = self._request_upload_urls(batch_files, log_callback)
                
                # 步骤2: 上传文件
                self._upload_files(batch_files, upload_urls, log_callback)
                
                # 步骤3: 轮询结果
                batch_results = self._poll_results(batch_id, status_callback, log_callback)
                results.update(batch_results)
            
            if log_callback:
                log_callback(f"所有章节处理完成！共处理 {len(results)} 个文件")
            
            return results
            
        except Exception as e:
            error_msg = f"MinerU处理过程中发生错误：{str(e)}"
            if log_callback:
                log_callback(error_msg)
            return {}

    @staticmethod
    def _split_batches(items: List[str], batch_size: int) -> List[List[str]]:
        """将文件列表切分为符合官方上限的多个批次。"""
        return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    
    def _request_upload_urls(self, file_paths: List[str], 
                           log_callback: Optional[Callable] = None) -> Tuple[str, List[str]]:
        """申请上传URL"""
        if log_callback:
            log_callback("正在申请文件上传链接...")
        
        # 构建请求数据
        files_payload = []
        for file_path in file_paths:
            file_name = os.path.basename(file_path)
            base_name = os.path.splitext(file_name)[0]
            # 确保data_id不超过128字符限制
            if len(base_name) > 128:
                # 截取前120个字符，保留一些空间给可能的索引
                data_id = base_name[:120]
            else:
                data_id = base_name
            files_payload.append({
                "name": file_name,
                "is_ocr": self.mineru_config['enable_ocr'],
                "data_id": data_id
            })
        
        payload = {
            "enable_formula": self.mineru_config['enable_formula'],
            "language": self.mineru_config['language'],
            "enable_table": self.mineru_config['enable_table'],
            "model_version": self.mineru_config['model_version'],
            "files": files_payload
        }
        
        try:
            response = requests.post(self.upload_url, headers=self.headers, 
                                   json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                batch_id = result["data"]["batch_id"]
                urls = result["data"]["file_urls"]
                
                if log_callback:
                    log_callback(f"成功获取batch_id: {batch_id}")
                    log_callback(f"获取到 {len(urls)} 个上传URL")
                
                return batch_id, urls
            else:
                error_msg = result.get('msg', '未知错误')
                raise Exception(f"申请上传URL失败: {error_msg}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"响应JSON解析失败: {e}")
    
    def _upload_single_file(self, file_path: str, upload_url: str) -> str:
        """上传单个文件"""
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        try:
            with open(file_path, 'rb') as f:
                response = requests.put(upload_url, data=f, timeout=600)
                response.raise_for_status()
                return f"[成功] {file_name} ({file_size / 1024 / 1024:.2f} MB)"
                
        except requests.exceptions.Timeout:
            return f"[超时] {file_name}: 上传超时"
        except requests.exceptions.RequestException as e:
            return f"[失败] {file_name}: {e}"
    
    def _upload_files(self, file_paths: List[str], upload_urls: List[str],
                     log_callback: Optional[Callable] = None):
        """并行上传文件"""
        if log_callback:
            log_callback("开始上传文件...")
        
        if len(file_paths) != len(upload_urls):
            raise ValueError(f"文件数量({len(file_paths)})与URL数量({len(upload_urls)})不匹配")
        
        failed_count = 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_file = {
                executor.submit(self._upload_single_file, path, url): path 
                for path, url in zip(file_paths, upload_urls)
            }
            
            for future in as_completed(future_to_file):
                result = future.result()
                if log_callback:
                    log_callback(f"  {result}")
                
                if "[失败]" in result or "[超时]" in result:
                    failed_count += 1
        
        if log_callback:
            success_count = len(file_paths) - failed_count
            log_callback(f"上传完成: 成功 {success_count}, 失败 {failed_count}")
    
    def _poll_results(self, batch_id: str, 
                     status_callback: Optional[Callable] = None,
                     log_callback: Optional[Callable] = None) -> Dict:
        """轮询处理结果"""
        result_url = f"{self.result_url_template}/{batch_id}"
        poll_interval = self.mineru_config['poll_interval']
        max_attempts = self.mineru_config['max_attempts']
        
        if log_callback:
            log_callback(f"开始轮询结果 (batch_id: {batch_id})...")
        
        for attempt in range(max_attempts):
            try:
                if log_callback:
                    log_callback(f"正在查询... (第 {attempt + 1} 次)")
                
                response = requests.get(result_url, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("code") == 0:
                    data = result.get("data", {})
                    results_list = data.get("extract_result", [])
                    
                    if not results_list:
                        if log_callback:
                            log_callback(f"暂无结果，继续等待... (attempt {attempt + 1})")
                        time.sleep(poll_interval)
                        continue
                    
                    # 检查完成状态
                    all_done = all(item.get("state") == "done" for item in results_list)
                    
                    if all_done and results_list:
                        if log_callback:
                            log_callback("所有任务解析成功！")
                        
                        # 转换为字典格式
                        results_dict = {
                            item.get('file_name'): item 
                            for item in results_list
                        }
                        
                        return results_dict
                    
                    # 检查失败任务
                    failed_tasks = [item for item in results_list if item.get("state") == "failed"]
                    if failed_tasks:
                        error_messages = [
                            f"文件 '{t.get('file_name')}': {t.get('err_msg', '未知错误')}" 
                            for t in failed_tasks
                        ]
                        raise Exception(f"解析任务失败:\n" + "\n".join(error_messages))
                    
                    # 更新状态
                    current_statuses = {
                        item.get('file_name'): item.get('state') 
                        for item in results_list
                    }
                    
                    if status_callback:
                        try:
                            status_callback(current_statuses)
                        except Exception:
                            pass  # 忽略回调错误
                    
                    if log_callback:
                        state_counts = {}
                        for state in current_statuses.values():
                            state_counts[state] = state_counts.get(state, 0) + 1
                        status_summary = ", ".join(
                            f"{state}={count}" for state, count in sorted(state_counts.items())
                        )
                        log_callback(f"当前状态: {status_summary}")
                    
                    time.sleep(poll_interval)
                    
            except requests.exceptions.RequestException as e:
                if log_callback:
                    log_callback(f"网络请求失败 (attempt {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    time.sleep(poll_interval)
                    continue
                else:
                    raise Exception(f"网络请求持续失败: {e}")
        
        raise TimeoutError(f"轮询超时，无法在规定时间内获取解析结果")


class ContentExtractor:
    """内容提取器，用于下载和解压MinerU返回的ZIP文件"""
    
    @staticmethod
    def download_and_extract(zip_url: str, output_dir: str,
                           log_callback: Optional[Callable] = None) -> bool:
        """
        下载并解压ZIP文件
        
        Args:
            zip_url: ZIP文件下载URL
            output_dir: 输出目录
            log_callback: 日志回调函数
            
        Returns:
            是否成功
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            if log_callback:
                log_callback(f"正在下载: {zip_url}")
            
            # 下载ZIP文件
            response = requests.get(zip_url, timeout=300)
            response.raise_for_status()
            
            # 保存ZIP文件
            zip_filename = os.path.basename(zip_url).split('?')[0]  # 去掉URL参数
            if not zip_filename.endswith('.zip'):
                zip_filename += '.zip'
            
            local_zip_path = os.path.join(output_dir, zip_filename)
            with open(local_zip_path, 'wb') as f:
                f.write(response.content)
            
            if log_callback:
                log_callback(f"ZIP文件已保存: {local_zip_path}")
            
            # 解压文件
            with zipfile.ZipFile(local_zip_path, 'r') as zf:
                zf.extractall(output_dir)
            
            if log_callback:
                log_callback(f"ZIP文件已解压到: {output_dir}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            if log_callback:
                log_callback(f"下载ZIP文件失败: {e}")
            return False
        except zipfile.BadZipFile as e:
            if log_callback:
                log_callback(f"ZIP文件格式错误: {e}")
            return False
        except Exception as e:
            if log_callback:
                log_callback(f"处理ZIP文件时发生错误: {e}")
            return False


class APIHandler:
    """API处理器主类，整合MinerU和其他API调用"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.mineru_api = None
        self.llm_api = None
        self.content_extractor = ContentExtractor()
        self.json_to_markdown = JSONToMarkdownConverter()

    def refresh_clients(self):
        """在每次处理前重新加载配置，避免要求重启应用。"""
        self.config_manager.load_config()
        self.mineru_api = MinerUAPI(self.config_manager)
        self.llm_api = None

    def get_llm_api(self) -> LLMAPI:
        """延迟初始化LLM客户端，避免首启时因未配置Key而崩溃。"""
        if self.llm_api is None:
            self.llm_api = LLMAPI(self.config_manager)
        return self.llm_api
    
    def process_book_chapters(self, book_path: str, chapters: List[Dict],
                            status_callback: Optional[Callable] = None,
                            log_callback: Optional[Callable] = None) -> bool:
        """
        处理整本书的章节
        
        Args:
            book_path: 书籍路径
            chapters: 章节信息列表
            status_callback: 状态更新回调
            log_callback: 日志回调
            
        Returns:
            是否处理成功
        """
        try:
            self.refresh_clients()

            # 获取章节PDF文件路径
            chapters_pdf_dir = os.path.join(book_path, "chapters_pdf")
            if not os.path.exists(chapters_pdf_dir):
                if log_callback:
                    log_callback("章节PDF目录不存在，请先进行章节切分")
                return False
            
            # 收集章节文件
            chapter_files = []
            for i, chapter in enumerate(chapters):
                # 使用与pdf_processor.py中一致的简单命名规则
                chapter_filename = f"{i+1:02d}.pdf"
                chapter_path = os.path.join(chapters_pdf_dir, chapter_filename)
                
                if os.path.exists(chapter_path):
                    chapter_files.append(chapter_path)
                else:
                    if log_callback:
                        log_callback(f"警告: 章节文件不存在: {chapter_path}")
            
            if not chapter_files:
                if log_callback:
                    log_callback("没有找到章节PDF文件")
                return False
            
            if log_callback:
                log_callback(f"找到 {len(chapter_files)} 个章节文件，开始MinerU解析...")
            
            # 调用MinerU API
            results = self.mineru_api.process_chapters(
                chapter_files, status_callback, log_callback
            )
            
            if not results:
                if log_callback:
                    log_callback("MinerU解析失败")
                return False
            
            # 下载和解压结果
            mineru_json_dir = os.path.join(book_path, "MinerU_json")
            os.makedirs(mineru_json_dir, exist_ok=True)
            
            success_count = 0
            for filename, result_data in results.items():
                zip_url = result_data.get('full_zip_url')
                if not zip_url:
                    if log_callback:
                        log_callback(f"警告: {filename} 没有找到下载链接")
                    continue
                
                # 为每个章节创建单独目录
                chapter_name = os.path.splitext(filename)[0]
                chapter_output_dir = os.path.join(mineru_json_dir, chapter_name)
                
                if self.content_extractor.download_and_extract(
                    zip_url, chapter_output_dir, log_callback
                ):
                    success_count += 1
                else:
                    if log_callback:
                        log_callback(f"下载解压失败: {filename}")
            
            if log_callback:
                log_callback(f"MinerU处理完成: {success_count}/{len(results)} 个文件成功")
            
            # 如果MinerU处理成功，继续转换JSON为Markdown
            if success_count > 0:
                if log_callback:
                    log_callback("开始将JSON转换为Markdown...")
                
                # 调用JSON转Markdown功能
                markdown_success = self.json_to_markdown.process_chapter_json_files(
                    book_path, chapters, log_callback
                )
                
                if markdown_success:
                    if log_callback:
                        log_callback("JSON转Markdown完成！")
                else:
                    if log_callback:
                        log_callback("JSON转Markdown失败，但MinerU处理已完成")
            
            return success_count > 0
            
        except Exception as e:
            if log_callback:
                log_callback(f"处理章节时发生错误: {str(e)}")
            return False

    def analyze_chapters(self, book_path: str, chapters: List[Dict],
                       status_callback: Optional[Callable] = None,
                       log_callback: Optional[Callable] = None) -> bool:
        """
        使用DeepSeek分析章节Markdown内容
        
        Args:
            book_path: 书籍路径
            chapters: 章节信息列表
            status_callback: 状态更新回调
            log_callback: 日志回调
            
        Returns:
            是否处理成功
        """
        try:
            self.refresh_clients()
            llm_api = self.get_llm_api()

            # 获取章节Markdown文件路径
            chapters_markdown_dir = os.path.join(book_path, "chapters_markdown")
            if not os.path.exists(chapters_markdown_dir):
                if log_callback:
                    log_callback("章节Markdown目录不存在，请先完成Markdown转换")
                return False
            
            # 创建LLM结果目录（按照用户要求改为LLM_result）
            llm_result_dir = os.path.join(book_path, "LLM_result")
            os.makedirs(llm_result_dir, exist_ok=True)
            
            if log_callback:
                log_callback(f"开始分析 {len(chapters)} 个章节...")
            
            llm_config = self.config_manager.get_llm_config()
            max_concurrent_calls = llm_config.get('max_concurrent_calls', 5) # 从配置中获取最大并发数
            
            success_count = 0
            
            def _analyze_single_chapter(i: int, chapter: Dict) -> bool:
                """内部函数，用于处理单个章节的LLM分析"""
                # 使用与pdf_processor.py和MinerU处理中一致的简单命名规则
                markdown_filename = f"{i+1:02d}.md"
                markdown_path = os.path.join(chapters_markdown_dir, markdown_filename)
                
                if not os.path.exists(markdown_path):
                    if log_callback:
                        log_callback(f"警告: Markdown文件不存在: {markdown_path}")
                    return False
                
                if log_callback:
                    log_callback(f"正在分析章节 {i+1}: {chapter['title']}")
                
                try:
                    with open(markdown_path, 'r', encoding='utf-8') as f:
                        markdown_content = f.read()
                except Exception as e:
                    if log_callback:
                        log_callback(f"读取Markdown文件失败: {str(e)}")
                    return False
                
                try:
                    analysis_result = llm_api.analyze_text(markdown_content)
                    if not analysis_result or 'content' not in analysis_result:
                        if log_callback:
                            log_callback(f"{llm_api.provider} API返回结果异常")
                        return False
                    
                    analysis_content = analysis_result['content']
                    
                    analysis_filename = f"{i+1:02d}_analysis.md"
                    analysis_path = os.path.join(llm_result_dir, analysis_filename)
                    
                    with open(analysis_path, 'w', encoding='utf-8') as f:
                        f.write(f"# {chapter['title']} - LLM分析结果\n\n")
                        f.write(f"**章节页码范围:** {chapter.get('start_page', 'N/A')} - {chapter.get('end_page', 'N/A')}\n\n")
                        f.write(f"**分析时间:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        f.write("---\n\n")
                        f.write(analysis_content)
                    
                    if log_callback:
                        log_callback(f"章节 {i+1} 分析完成，结果已保存: {analysis_filename}")
                    
                    if status_callback:
                        status_callback({
                            chapter['title']: "completed"
                        })
                    return True
                    
                except Exception as e:
                    if log_callback:
                        log_callback(f"分析章节 {chapter['title']} 失败: {str(e)}")
                    return False
            
            with ThreadPoolExecutor(max_workers=max_concurrent_calls) as executor:
                futures = {executor.submit(_analyze_single_chapter, i, chapter): (i, chapter) for i, chapter in enumerate(chapters)}
                
                for future in as_completed(futures):
                    if future.result():
                        success_count += 1
            
            if log_callback:
                log_callback(f"章节分析完成: {success_count}/{len(chapters)} 个章节成功")
                log_callback(f"分析结果保存在: {llm_result_dir}")
            
            return success_count > 0
            
        except Exception as e:
            if log_callback:
                log_callback(f"分析章节时发生错误: {str(e)}")
            return False
