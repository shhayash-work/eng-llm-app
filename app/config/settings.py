"""
アプリケーション設定
"""
import os
from pathlib import Path

# アプリケーション基本設定
APP_TITLE = "工程報告書チェックアプリ"
APP_DESCRIPTION = "建設工程異常検知・分析システム"
VERSION = "1.0.0"

# パス設定
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SHAREPOINT_DOCS_DIR = DATA_DIR / "sharepoint_docs"
CONSTRUCTION_DATA_DIR = DATA_DIR / "sample_construction_data"

# LLMプロバイダー設定
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # ollama, openai, anthropic
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.3:latest")

# Ollama設定
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.3:latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:6081")

# OpenAI設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Anthropic設定
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

# ベクターストア設定
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
EMBEDDING_MODEL = "mxbai-embed-large:latest"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# フラグ定義
RISK_FLAGS = {
    "emergency_stop": {
        "name": "🚨 緊急停止",
        "description": "住民反対、事故等による緊急停止",
        "priority": 1,
        "color": "#FF0000"
    },
    "delay_risk": {
        "name": "⚠️ 遅延リスク",
        "description": "許可遅れ、資材不足等による遅延懸念",
        "priority": 2,
        "color": "#FFA500"
    },
    "technical_issue": {
        "name": "🔧 技術課題",
        "description": "設計変更、工法問題等の技術的課題",
        "priority": 3,
        "color": "#FFD700"
    },
    "procedure_problem": {
        "name": "📋 手続き問題",
        "description": "申請不備、承認待ち等の手続き関連問題",
        "priority": 4,
        "color": "#87CEEB"
    },
    "requires_review": {
        "name": "❓ 要確認",
        "description": "分類困難な異常ケース",
        "priority": 5,
        "color": "#DDA0DD"
    }
}

# UI設定
STREAMLIT_CONFIG = {
    "page_title": APP_TITLE,
    "page_icon": "🏗️",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# ログ設定
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"