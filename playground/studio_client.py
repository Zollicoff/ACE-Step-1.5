"""
ACE Studio WebBridge Client
用于与 ACE Studio WebBridge REST API 交互的 Python 客户端封装。
"""
import os
import time
import requests
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import urllib3

# 禁用自签名证书警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ImportStatus(Enum):
    """音频导入任务状态"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class VersionInfo:
    """版本信息"""
    version: str
    app_version: str
    status: str


@dataclass
class ImportTaskResult:
    """导入任务结果"""
    success: bool
    task_id: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ImportStatusResult:
    """导入状态查询结果"""
    task_id: str
    status: str
    progress: int
    success: bool
    filename: Optional[str] = None
    clipboard_set: Optional[bool] = None
    error: Optional[str] = None


@dataclass
class ClipboardCheckResult:
    """剪贴板检查结果"""
    has_audio: bool
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    size: Optional[int] = None


class StudioClient:
    """
    ACE Studio WebBridge REST API 客户端
    
    用于与 ACE Studio 进行音频数据交换。
    
    使用示例:
    ```python
    client = StudioClient(token="your_token_here")
    
    # 检查服务状态
    version = client.get_version()
    print(f"Studio version: {version.app_version}")
    
    # 从 URL 导入音频
    result = client.import_audio_from_url("https://example.com/audio.wav", "my_audio.wav")
    if result.success:
        # 等待导入完成
        status = client.wait_for_import(result.task_id)
        print(f"Import completed: {status.filename}")
    
    # 检查剪贴板
    clipboard = client.check_clipboard()
    if clipboard.has_audio:
        # 下载剪贴板音频
        audio_data, filename = client.get_clipboard_audio()
        with open(filename, "wb") as f:
            f.write(audio_data)
    ```
    """
    
    DEFAULT_BASE_URL = "https://localhost:21573"
    DEFAULT_TIMEOUT = 30
    
    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        verify_ssl: bool = False  # 默认不验证自签名证书
    ):
        """
        初始化 Studio 客户端
        
        Args:
            token: Bearer Token，用于身份验证。如果为 None，则只能调用 /api/version
            base_url: API 基础 URL，默认为 https://localhost:21573
            timeout: 请求超时时间（秒）
            verify_ssl: 是否验证 SSL 证书，默认 False（因为使用自签名证书）
        """
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._session = requests.Session()
    
    def set_token(self, token: str) -> None:
        """设置或更新 Token"""
        self.token = token
    
    def _get_headers(self, require_auth: bool = True) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if require_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def _request(
        self,
        method: str,
        endpoint: str,
        require_auth: bool = True,
        **kwargs
    ) -> requests.Response:
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法 (GET, POST, etc.)
            endpoint: API 端点 (如 /api/version)
            require_auth: 是否需要身份验证
            **kwargs: 传递给 requests 的其他参数
        
        Returns:
            requests.Response 对象
        
        Raises:
            requests.exceptions.RequestException: 请求失败时抛出
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(require_auth)
        
        response = self._session.request(
            method=method,
            url=url,
            headers=headers,
            timeout=self.timeout,
            verify=self.verify_ssl,
            **kwargs
        )
        
        return response
    
    # =========================================================================
    # API 方法
    # =========================================================================
    
    def get_version(self) -> VersionInfo:
        """
        获取 Studio 版本信息（健康检查）
        
        无需身份验证。
        
        Returns:
            VersionInfo 对象
        
        Raises:
            requests.exceptions.RequestException: 请求失败
            ValueError: 响应格式错误
        """
        response = self._request("GET", "/api/version", require_auth=False)
        response.raise_for_status()
        
        data = response.json()
        return VersionInfo(
            version=data.get("version", ""),
            app_version=data.get("appVersion", ""),
            status=data.get("status", "")
        )
    
    def is_available(self) -> bool:
        """
        检查 Studio 服务是否可用
        
        Returns:
            True 如果服务可用，否则 False
        """
        try:
            version = self.get_version()
            return version.status == "ready"
        except Exception:
            return False
    
    def import_audio_from_url(
        self,
        url: str,
        filename: Optional[str] = None
    ) -> ImportTaskResult:
        """
        从 URL 导入音频到 Studio
        
        导入是异步的，返回 task_id 用于查询状态。
        导入完成后音频会保存到项目的 Samples/Clipboard 文件夹，
        并自动设置到 ACE Studio 剪贴板。
        
        Args:
            url: 音频文件的 URL 地址
            filename: 自定义文件名（可选）
        
        Returns:
            ImportTaskResult 对象，包含 task_id 和初始状态
        """
        payload = {"url": url}
        if filename:
            payload["filename"] = filename
        
        try:
            response = self._request("POST", "/api/audio/import", json=payload)
            data = response.json()
            
            return ImportTaskResult(
                success=data.get("success", False),
                task_id=data.get("taskId"),
                status=data.get("status"),
                error=data.get("error")
            )
        except Exception as e:
            return ImportTaskResult(
                success=False,
                error=str(e)
            )
    
    def get_import_status(self, task_id: str) -> ImportStatusResult:
        """
        查询音频导入任务的状态
        
        Args:
            task_id: 导入任务的 ID
        
        Returns:
            ImportStatusResult 对象
        """
        response = self._request("GET", "/api/audio/import/status", params={"id": task_id})
        data = response.json()
        
        return ImportStatusResult(
            task_id=data.get("taskId", task_id),
            status=data.get("status", "unknown"),
            progress=data.get("progress", 0),
            success=data.get("success", False),
            filename=data.get("filename"),
            clipboard_set=data.get("clipboardSet"),
            error=data.get("error")
        )
    
    def wait_for_import(
        self,
        task_id: str,
        poll_interval: float = 0.5,
        max_wait: float = 60.0
    ) -> ImportStatusResult:
        """
        等待导入任务完成
        
        Args:
            task_id: 导入任务的 ID
            poll_interval: 轮询间隔（秒）
            max_wait: 最大等待时间（秒）
        
        Returns:
            ImportStatusResult 对象
        
        Raises:
            TimeoutError: 超过最大等待时间
        """
        start_time = time.time()
        
        while True:
            status = self.get_import_status(task_id)
            
            if status.status in (ImportStatus.COMPLETED.value, ImportStatus.FAILED.value):
                return status
            
            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                raise TimeoutError(f"Import task {task_id} timed out after {max_wait}s")
            
            time.sleep(poll_interval)
    
    def check_clipboard(self) -> ClipboardCheckResult:
        """
        检查 Studio 剪贴板中是否有音频数据
        
        Returns:
            ClipboardCheckResult 对象
        """
        response = self._request("GET", "/api/audio/clipboard/check")
        data = response.json()
        
        return ClipboardCheckResult(
            has_audio=data.get("hasAudio", False),
            filename=data.get("filename"),
            mime_type=data.get("mimeType"),
            size=data.get("size")
        )
    
    def get_clipboard_audio(self) -> Tuple[bytes, str]:
        """
        获取剪贴板中的音频数据
        
        Returns:
            Tuple of (audio_bytes, filename)
        
        Raises:
            ValueError: 剪贴板中没有音频
            requests.exceptions.RequestException: 请求失败
        """
        # 先检查是否有音频
        check = self.check_clipboard()
        if not check.has_audio:
            raise ValueError("No audio in clipboard")
        
        # 获取音频数据
        response = self._request("GET", "/api/audio/clipboard/data")
        response.raise_for_status()
        
        # 从 Content-Disposition 头获取文件名
        content_disposition = response.headers.get("Content-Disposition", "")
        filename = check.filename or "clipboard_audio.wav"
        
        if "filename=" in content_disposition:
            # 解析文件名
            import re
            match = re.search(r'filename="?([^";\n]+)"?', content_disposition)
            if match:
                filename = match.group(1)
        
        return response.content, filename
    
    def download_clipboard_to_file(
        self,
        output_path: Optional[str] = None,
        output_dir: str = "."
    ) -> str:
        """
        下载剪贴板音频到文件
        
        Args:
            output_path: 指定输出文件路径。如果为 None，则使用原始文件名
            output_dir: 输出目录（当 output_path 为 None 时使用）
        
        Returns:
            保存的文件路径
        
        Raises:
            ValueError: 剪贴板中没有音频
        """
        audio_data, filename = self.get_clipboard_audio()
        
        if output_path is None:
            output_path = os.path.join(output_dir, filename)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        with open(output_path, "wb") as f:
            f.write(audio_data)
        
        return output_path
    
    # =========================================================================
    # 便捷方法（用于 Gradio 集成）
    # =========================================================================
    
    def send_audio_to_studio(
        self,
        audio_url: str,
        filename: Optional[str] = None,
        wait: bool = True,
        max_wait: float = 60.0
    ) -> Tuple[bool, str]:
        """
        发送音频到 Studio（便捷方法）
        
        Args:
            audio_url: 音频文件的 URL
            filename: 自定义文件名
            wait: 是否等待导入完成
            max_wait: 最大等待时间
        
        Returns:
            Tuple of (success, message)
        """
        # 检查服务是否可用
        if not self.is_available():
            return False, "❌ ACE Studio service is not available"
        
        # 检查 token
        if not self.token:
            return False, "❌ No authentication token provided"
        
        # 发起导入
        result = self.import_audio_from_url(audio_url, filename)
        if not result.success:
            return False, f"❌ Import failed: {result.error}"
        
        if not wait:
            return True, f"✅ Import started (task_id: {result.task_id})"
        
        # 等待完成
        try:
            status = self.wait_for_import(result.task_id, max_wait=max_wait)
            if status.status == ImportStatus.COMPLETED.value:
                return True, f"✅ Audio imported successfully: {status.filename}"
            else:
                return False, f"❌ Import failed: {status.error}"
        except TimeoutError:
            return False, f"❌ Import timed out after {max_wait}s"
    
    def receive_audio_from_studio(
        self,
        output_dir: str = "."
    ) -> Tuple[Optional[str], str]:
        """
        从 Studio 剪贴板接收音频（便捷方法）
        
        Args:
            output_dir: 输出目录
        
        Returns:
            Tuple of (file_path or None, message)
        """
        # 检查服务是否可用
        if not self.is_available():
            return None, "❌ ACE Studio service is not available"
        
        # 检查 token
        if not self.token:
            return None, "❌ No authentication token provided"
        
        # 检查剪贴板
        check = self.check_clipboard()
        if not check.has_audio:
            return None, "❌ No audio in Studio clipboard"
        
        # 下载音频
        try:
            file_path = self.download_clipboard_to_file(output_dir=output_dir)
            return file_path, f"✅ Audio received: {os.path.basename(file_path)}"
        except Exception as e:
            return None, f"❌ Failed to receive audio: {str(e)}"


# =============================================================================
# Gradio 集成辅助函数
# =============================================================================

# 全局客户端实例（用于 Gradio UI）
_studio_client: Optional[StudioClient] = None


def get_studio_client(token: Optional[str] = None) -> StudioClient:
    """
    获取或创建 Studio 客户端单例
    
    Args:
        token: 如果提供，会更新客户端的 token
    
    Returns:
        StudioClient 实例
    """
    global _studio_client
    
    if _studio_client is None:
        _studio_client = StudioClient(token=token)
    elif token:
        _studio_client.set_token(token)
    
    return _studio_client


def init_studio_client(token: str) -> Tuple[bool, str]:
    """
    初始化 Studio 客户端（用于 Gradio UI）
    
    Args:
        token: Bearer Token
    
    Returns:
        Tuple of (success, message)
    """
    client = get_studio_client(token)
    
    if client.is_available():
        version = client.get_version()
        return True, f"✅ Connected to ACE Studio {version.app_version}"
    else:
        return False, "❌ Failed to connect to ACE Studio"


def send_to_studio(audio_path: str, filename: Optional[str] = None) -> str:
    """
    发送本地音频文件到 Studio（用于 Gradio UI）
    
    注意：此函数需要音频文件通过 URL 访问。
    在 Gradio 中，可以使用 gr.Audio 的 value 作为 URL。
    
    Args:
        audio_path: 音频文件路径或 URL
        filename: 自定义文件名
    
    Returns:
        状态消息
    """
    client = get_studio_client()
    
    # 如果是本地路径，需要先上传到可访问的 URL
    # 这里假设 audio_path 已经是 URL 或 Gradio 提供的临时 URL
    success, message = client.send_audio_to_studio(audio_path, filename)
    return message


def receive_from_studio(output_dir: str = ".") -> Tuple[Optional[str], str]:
    """
    从 Studio 接收音频（用于 Gradio UI）
    
    Args:
        output_dir: 输出目录
    
    Returns:
        Tuple of (file_path or None, message)
    """
    client = get_studio_client()
    return client.receive_audio_from_studio(output_dir)


def check_studio_connection() -> Tuple[bool, str]:
    """
    检查 Studio 连接状态（用于 Gradio UI）
    
    Returns:
        Tuple of (connected, message)
    """
    client = get_studio_client()
    
    try:
        if client.is_available():
            version = client.get_version()
            return True, f"✅ Connected to ACE Studio {version.app_version}"
        else:
            return False, "❌ ACE Studio is not available"
    except Exception as e:
        return False, f"❌ Connection error: {str(e)}"
