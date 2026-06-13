from __future__ import annotations

import re

from xinyu_bridge_values import safe_str
from xinyu_text_variants import readable_markers


TRUSTED_CODEX_PUBLIC_SEARCH_MARKERS = readable_markers(
    "搜索",
    "搜一下",
    "搜下",
    "搜东西",
    "联网",
    "查一下",
    "查下",
    "查资料",
    "核对",
    "验证",
    "找资料",
    "公开资料",
    "网页",
    "新闻",
    "资料来源",
    "source",
    "search",
    "web",
    "verify",
)
TRUSTED_CODEX_LOCAL_BLOCK_MARKERS = readable_markers(
    "本机",
    "本地",
    "电脑",
    "文件",
    "目录",
    "路径",
    "代码",
    "项目",
    "仓库",
    "安装",
    "pip",
    "包",
    "修改",
    "改代码",
    "删除",
    "移动",
    "上传",
    "token",
    "密钥",
    "密码",
    "cookie",
    "日志",
    "配置",
    "权限配置",
)
TRUSTED_CODEX_LOCAL_PATH_RE = re.compile(
    r"(?i)(?:[a-z]:[\\/]|\\\\|file://|(?:^|[\s`'\"“”‘’])\.{1,2}[\\/])"
)
TRUSTED_CODEX_LOCAL_ENGLISH_BLOCK_MARKERS = (
    "local",
    "localhost",
    "127.0.0.1",
    "file://",
    "localfile",
    "localpath",
    "localconfig",
    "config.yaml",
    ".env",
    "code",
    "repo",
    "repository",
    "project",
    "install",
    "package",
    "admin",
    "permission",
    "delete",
    "modify",
    "write",
    "readfile",
    "openfile",
    "log",
    "secret",
    "api_key",
)


def trusted_public_search_task_allowed(
    task_text: str,
    *,
    public_search_markers: tuple[str, ...] | None = None,
    local_block_markers: tuple[str, ...] | None = None,
    local_path_pattern: re.Pattern[str] | None = None,
    local_english_block_markers: tuple[str, ...] | None = None,
) -> bool:
    if public_search_markers is None:
        public_search_markers = TRUSTED_CODEX_PUBLIC_SEARCH_MARKERS
    if local_block_markers is None:
        local_block_markers = TRUSTED_CODEX_LOCAL_BLOCK_MARKERS
    if local_path_pattern is None:
        local_path_pattern = TRUSTED_CODEX_LOCAL_PATH_RE
    if local_english_block_markers is None:
        local_english_block_markers = TRUSTED_CODEX_LOCAL_ENGLISH_BLOCK_MARKERS

    raw_text = safe_str(task_text)
    compact = re.sub(r"\s+", "", raw_text).lower()
    if not compact:
        return False
    if local_path_pattern.search(raw_text):
        return False
    if any(marker.lower() in compact for marker in local_block_markers):
        return False
    if any(marker in compact for marker in local_english_block_markers):
        return False
    return any(marker.lower() in compact for marker in public_search_markers)
