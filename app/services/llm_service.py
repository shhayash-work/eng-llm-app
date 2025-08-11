"""
マルチプロバイダー対応LLMサービス - Ollama/OpenAI/Anthropic
"""
import json
import logging
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import streamlit as st

# 環境変数を読み込み
load_dotenv()

try:
    import ollama
except ImportError:
    ollama = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

from app.config.settings import (
    LLM_PROVIDER,
    OLLAMA_MODEL, 
    OLLAMA_BASE_URL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL
)
from app.config.prompts import (
    SYSTEM_PROMPT, 
    DOCUMENT_ANALYSIS_PROMPT, 
    QA_PROMPT,
    FEW_SHOT_EXAMPLES
)

logger = logging.getLogger(__name__)

class LLMService:
    """マルチプロバイダー対応LLMサービスクラス"""
    
    def __init__(self, provider: Optional[str] = None, force_test: bool = False):
        self.provider = provider or LLM_PROVIDER
        self.model = None
        self.force_test = force_test
        self._setup_provider()
    
    def _setup_provider(self):
        """プロバイダーに応じてクライアントをセットアップ"""
        try:
            if self.provider == "ollama":
                self._setup_ollama()
            elif self.provider == "openai":
                self._setup_openai()
            elif self.provider == "anthropic":
                self._setup_anthropic()
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"Failed to setup {self.provider}: {e}")
            self.model = None
    
    def _setup_ollama(self):
        """Ollamaクライアントをセットアップ"""
        if ollama is None:
            raise ImportError("ollama package not installed")
        
        self.model = OLLAMA_MODEL
        self.client = ollama.Client(host=OLLAMA_BASE_URL)
        
        # セッションキャッシュを使用した接続テスト
        self._test_ollama_connection()
    
    def _test_ollama_connection(self):
        """Ollama接続テスト（セッションキャッシュ対応）"""
        # Streamlitセッションステートをインポート（利用可能な場合のみ）
        try:
            import streamlit as st
            cache_key = f"ollama_tested_{OLLAMA_BASE_URL}_{OLLAMA_MODEL}"
            
            # 強制テストでない場合、キャッシュをチェック
            if not self.force_test and cache_key in st.session_state:
                cached_result = st.session_state[cache_key]
                self.model = cached_result.get("model", OLLAMA_MODEL)
                logger.info(f"⚡ Using cached Ollama connection: {self.model}")
                return
        except ImportError:
            # Streamlitが利用できない場合は毎回テスト
            pass
        
        # 実際の接続テスト実行
        try:
            logger.info(f"🔍 Testing Ollama connection: {OLLAMA_BASE_URL}")
            
            # Ollamaサーバーの接続確認
            models = self.client.list()
            logger.info(f"Ollama server connected: {OLLAMA_BASE_URL}")
            logger.debug(f"Ollama models response: {models}")
            
            # 指定されたモデルの存在確認
            model_names = []
            try:
                if hasattr(models, 'models'):
                    models_list = models.models
                elif isinstance(models, dict) and 'models' in models:
                    models_list = models['models']
                elif isinstance(models, list):
                    models_list = models
                else:
                    models_list = []
                
                for model in models_list:
                    if hasattr(model, 'model'):
                        model_names.append(model.model)
                    elif hasattr(model, 'name'):
                        model_names.append(model.name)
                    elif isinstance(model, dict):
                        model_name = model.get('name') or model.get('model')
                        if model_name:
                            model_names.append(model_name)
            except Exception as e:
                logger.error(f"Failed to parse models list: {e}")
                model_names = []
                
            if self.model not in model_names:
                logger.warning(f"Model {self.model} not found. Available models: {model_names}")
                if model_names:
                    self.model = model_names[0]
                    logger.info(f"Using available model: {self.model}")
                else:
                    raise Exception("No models available in Ollama")
            else:
                logger.info(f"✅ Using model: {self.model}")
            
            # 接続成功をキャッシュに保存
            try:
                import streamlit as st
                st.session_state[cache_key] = {
                    "model": self.model,
                    "status": "connected"
                }
                logger.info(f"💾 Cached Ollama connection result")
            except ImportError:
                pass
                
        except Exception as e:
            logger.error(f"Failed to connect to Ollama at {OLLAMA_BASE_URL}: {e}")
            logger.info("Please ensure Ollama is running with: ollama serve")
            raise
    
    def _setup_openai(self):
        """OpenAIクライアントをセットアップ"""
        if ChatOpenAI is None:
            raise ImportError("langchain-openai package not installed")
        
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not provided")
        
        self.model = OPENAI_MODEL
        self.client = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            temperature=0.2
        )
        logger.info(f"OpenAI client initialized: {OPENAI_MODEL}")
    
    def _setup_anthropic(self):
        """Anthropicクライアントをセットアップ"""
        if ChatAnthropic is None:
            raise ImportError("langchain-anthropic package not installed")
        
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not provided")
        
        self.model = ANTHROPIC_MODEL
        self.client = ChatAnthropic(
            api_key=ANTHROPIC_API_KEY,
            model=ANTHROPIC_MODEL,
            temperature=0.2
        )
        logger.info(f"Anthropic client initialized: {ANTHROPIC_MODEL}")
    
    def _make_request(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
        """プロバイダーに応じてリクエストを送信"""
        if self.model is None:
            raise RuntimeError(f"LLM model not initialized for provider: {self.provider}")
        
        try:
            if self.provider == "ollama":
                return self._ollama_request(prompt, system_prompt)
            elif self.provider in ["openai", "anthropic"]:
                return self._langchain_request(prompt, system_prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"LLM request failed ({self.provider}): {e}")
            raise
    
    def _make_request_stream(self, prompt: str, system_prompt: str = SYSTEM_PROMPT):
        """プロバイダーに応じてストリーミングリクエストを送信"""
        if self.model is None:
            raise RuntimeError(f"LLM model not initialized for provider: {self.provider}")
        
        try:
            if self.provider == "ollama":
                yield from self._ollama_request_stream(prompt, system_prompt)
            elif self.provider in ["openai", "anthropic"]:
                # OpenAI/Anthropicのストリーミングは後で実装
                yield self._langchain_request(prompt, system_prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"LLM streaming request failed ({self.provider}): {e}")
            yield f"エラー: {str(e)}"
    
    def _ollama_request(self, prompt: str, system_prompt: str) -> str:
        """Ollamaリクエスト"""
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            options={
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": 2048
            }
        )
        return response['message']['content']
    
    def _ollama_request_stream(self, prompt: str, system_prompt: str):
        """Ollamaストリーミングリクエスト"""
        stream = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            options={
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": 2048
            },
            stream=True
        )
        
        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                yield chunk['message']['content']
    
    def _langchain_request(self, prompt: str, system_prompt: str) -> str:
        """LangChainリクエスト（OpenAI/Anthropic）"""
        messages = [
            ("system", system_prompt),
            ("human", prompt)
        ]
        response = self.client.invoke(messages)
        return response.content
    
    def analyze_document(self, document_content: str) -> Dict[str, Any]:
        """文書を分析してJSON結果を返す"""
        prompt = DOCUMENT_ANALYSIS_PROMPT.format(
            document_content=document_content
        )
        
        # Few-shot例文を含める
        full_prompt = f"{FEW_SHOT_EXAMPLES}\n\n{prompt}"
        
        try:
            response = self._make_request(full_prompt)
            logger.debug(f"LLM response: {response[:200]}...")
            
            # JSONパースを試行
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                
                # JSONの前処理（一般的な問題を修正）
                json_str = self._clean_json_string(json_str)
                
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as json_e:
                    logger.warning(f"JSON parse failed, attempting repair: {str(json_e)[:100]}")
                    # JSON修復を試行
                    repaired_json = self._repair_json_string(json_str)
                    if repaired_json:
                        try:
                            return json.loads(repaired_json)
                        except json.JSONDecodeError:
                            logger.warning("JSON repair failed, using fallback")
                    
                    # フォールバック
                    return self._fallback_analysis(document_content, response)
            else:
                # JSONが見つからない場合はテキスト解析でフォールバック
                logger.warning("No JSON found in response, using fallback")
                return self._fallback_analysis(document_content, response)
                
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            return self._create_error_result(str(e))

    
    def answer_question(self, question: str, context: str) -> str:
        """質問応答機能"""
        prompt = QA_PROMPT.format(
            question=question,
            context=context
        )
        
        try:
            return self._make_request(prompt)
        except Exception as e:
            logger.error(f"QA failed: {e}")
            return f"申し訳ございませんが、回答の生成中にエラーが発生しました: {str(e)}"
    
    def answer_question_stream(self, question: str, context: str):
        """質問応答機能（ストリーミング対応）"""
        prompt = QA_PROMPT.format(
            question=question,
            context=context
        )
        
        try:
            yield from self._make_request_stream(prompt)
        except Exception as e:
            logger.error(f"Streaming QA failed: {e}")
            yield f"申し訳ございませんが、回答の生成中にエラーが発生しました: {str(e)}"
    
    def _fallback_analysis(self, content: str, llm_response: str) -> Dict[str, Any]:
        """JSONパースに失敗した場合のフォールバック分析"""
        # キーワードベースの簡易分析
        issues = []
        flags = []
        risk_level = "低"
        urgency_score = 1
        
        content_lower = content.lower()
        
        # キーワード検索による分類
        if any(word in content_lower for word in ["反対", "停止", "中止", "緊急"]):
            flags.append("emergency_stop")
            risk_level = "高"
            urgency_score = 8
        
        if any(word in content_lower for word in ["遅延", "延期", "遅れ"]):
            flags.append("delay_risk")
            if risk_level == "低":
                risk_level = "中"
                urgency_score = 5
        
        if any(word in content_lower for word in ["不具合", "故障", "問題", "トラブル"]):
            flags.append("technical_issue")
            if risk_level == "低":
                risk_level = "中"
                urgency_score = 6
        
        if any(word in content_lower for word in ["申請", "許可", "免許", "手続き"]):
            flags.append("procedure_problem")
        
        return {
            "project_info": {
                "project_id": "不明",
                "location": "不明", 
                "responsible_person": "不明"
            },
            "status": "分析中",
            "issues": issues,
            "risk_level": risk_level,
            "recommended_flags": flags,
            "summary": "詳細分析が必要です",
            "urgency_score": urgency_score,
            "key_points": ["手動確認推奨"]
        }
    
    def _clean_json_string(self, json_str: str) -> str:
        """JSONString前処理で一般的な問題を修正"""
        import re
        
        # 改行とインデントを削除
        json_str = re.sub(r'\n\s*', '', json_str)
        
        # コメント行を削除
        json_str = re.sub(r'//.*?(?=\n|$)', '', json_str)
        
        # 末尾コンマを削除
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        return json_str.strip()
    
    def _repair_json_string(self, json_str: str) -> str:
        """破損したJSONの修復を試行"""
        try:
            import re
            
            # 一般的なJSON修復パターン
            repairs = [
                # 未閉じの引用符を修正
                (r'"([^"]*?)(?=[,\}\]])(?<!\\)"', r'"\1"'),
                # 未閉じのオブジェクトを修正
                (r'([^}])$', r'\1}'),
                # 空の値を修正
                (r':\s*,', r': null,'),
                (r':\s*}', r': null}'),
            ]
            
            repaired = json_str
            for pattern, replacement in repairs:
                repaired = re.sub(pattern, replacement, repaired)
            
            # 基本的な構造チェック
            if repaired.count('{') > repaired.count('}'):
                repaired += '}' * (repaired.count('{') - repaired.count('}'))
            
            return repaired
            
        except Exception as e:
            logger.warning(f"JSON repair attempt failed: {e}")
            return None
    
    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """エラー時のデフォルト結果を作成"""
        return {
            "project_info": {
                "project_id": "エラー",
                "location": "不明",
                "responsible_person": "不明"
            },
            "status": f"分析エラー: {error_msg}",
            "issues": ["分析処理失敗"],
            "risk_level": "要確認",
            "recommended_flags": ["requires_review"],
            "summary": "手動での確認が必要です",
            "urgency_score": 5,
            "key_points": ["エラーにより自動分析失敗"]
        }
    
    def get_provider_info(self) -> Dict[str, Any]:
        """現在のプロバイダー情報を取得"""
        return {
            "provider": self.provider,
            "model": self.model,
            "status": "connected" if self.model else "disconnected"
        }

# Streamlit用シングルトン化関数
@st.cache_resource
def get_llm_service() -> LLMService:
    """
    シングルトンLLMServiceインスタンスを取得
    
    初回実行時にLLMServiceを初期化し、以降はキャッシュされたインスタンスを返す。
    これにより2回目以降のアクセスが高速化される。
    """
    logger.info("🔧 Initializing singleton LLMService...")
    service = LLMService()
    logger.info("✅ Singleton LLMService initialized and cached")
    return service