"""パイプライン共通ユーティリティ"""

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "GiinScore/0.1 (Data Pipeline)"


def detect_encoding(resp: httpx.Response) -> str:
    """レスポンスのContent-Typeヘッダからエンコーディングを判定する。"""
    content_type = resp.headers.get("content-type", "")
    if "euc-jp" in content_type.lower():
        return "euc-jp"
    if "shift_jis" in content_type.lower():
        return "shift_jis"
    return "utf-8"


def health_check(soup: BeautifulSoup) -> bool:
    """HTML構造が期待通りかチェックする。"""
    return soup.find("table") is not None or soup.find("a") is not None
