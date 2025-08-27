"""
建設管理システム連動LLMアプリ - メインアプリケーション
Aurora-LLM Connector

KDDI様向けデモアプリケーション
"""
import streamlit as st
import logging
import json
import time
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# アプリケーション内部モジュール
from app.config.settings import (
    APP_TITLE, 
    APP_DESCRIPTION, 
    VERSION,
    STREAMLIT_CONFIG,
    SHAREPOINT_DOCS_DIR,
    CONSTRUCTION_DATA_DIR
)
from app.models.report import DocumentReport, ReportType, StatusFlag
from app.models.construction import ConstructionProject, PhaseStatus, RiskLevel, ConstructionPhase
from app.services.document_processor import DocumentProcessor
from app.ui.dashboard import render_dashboard
from app.ui.project_dashboard import render_project_dashboard
from app.services.project_aggregator import ProjectAggregator
from app.ui.report_viewer import render_report_list
from app.ui.analysis_panel import render_analysis_panel

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🎨 システムスタイリング
SYSTEM_STYLE = """
<style>
    /* システム基調カラー */
    :root {
        --primary-blue: #0052CC;
        --light-blue: #4A90E2;
        --dark-blue: #003C8F;
        --accent-orange: #FF6B35;
        --light-gray: #F5F7FA;
        --dark-gray: #2C3E50;
        --text-primary: #2C3E50;
        --text-secondary: #7F8C8D;
    }
    
    /* メインヘッダー */
    .main-header {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--light-blue) 100%);
        padding: 24px 32px;
        border-radius: 12px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 82, 204, 0.25);
    }
    
    .main-header h1 {
        font-size: 38px;
        font-weight: 700;
        margin: 0 0 8px 0;
        line-height: 1.2;
    }
    
    .main-header p {
        font-size: 16px;
        opacity: 0.9;
        margin: 0;
        line-height: 1.4;
    }
    
    /* メトリクスカード */
    .metric-card {
        background: white;
        padding: 24px;
        border-radius: 12px;
        border-left: 5px solid var(--primary-blue);
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
        margin: 12px 0;
        transition: all 0.2s ease;
    }
    
    .metric-card:hover {
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
        transform: translateY(-2px);
    }
    
    .metric-card h3 {
        font-size: 26px !important;
        font-weight: 600 !important;
        margin: 0 0 8px 0 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    .metric-card h2 {
        font-size: 48px !important;
        font-weight: 700 !important;
        margin: 0 !important;
        line-height: 1 !important;
    }
    
    .metric-card p {
        font-size: 16px !important;
        margin: 4px 0 0 0 !important;
        color: var(--text-secondary) !important;
    }
    
    /* ボタンスタイル */
    .stButton > button {
        background: var(--primary-blue);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 14px;
        transition: all 0.3s ease;
        border: 2px solid var(--primary-blue);
    }
    
    .stButton > button:hover {
        background: var(--light-blue);
        border-color: var(--light-blue);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(74, 144, 226, 0.4);
    }
    
    /* カスタムヘッダー */
    .custom-header {
        font-size: 26px;
        font-weight: 700;
        color: var(--primary-blue);
        margin: 24px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid var(--primary-blue);
        line-height: 1.3;
    }
    
    /* サイドバーヘッダー */
    .sidebar-header {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--light-blue) 100%);
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 3px 15px rgba(0, 82, 204, 0.2);
    }
    
    .sidebar-header h1 {
        color: white;
        margin: 0;
        font-size: 18px;
        font-weight: 700;
        line-height: 1.3;
    }
    
    .sidebar-header p {
        color: white;
        margin: 4px 0 0 0;
        opacity: 0.9;
        font-size: 13px;
        line-height: 1.2;
    }
    
    /* テキストサイズ調整 */
    .stMarkdown h1 {
        font-size: 24px;
        line-height: 1.3;
    }
    
    .stMarkdown h2 {
        font-size: 20px;
        line-height: 1.3;
    }
    
    .stMarkdown h3 {
        font-size: 16px;
        line-height: 1.4;
    }
    
    .stMarkdown p {
        font-size: 14px;
        line-height: 1.5;
    }
    
    /* メトリクス表示 */
    .stMetric {
        background: white;
        padding: 16px;
        border-radius: 8px;
        border-left: 4px solid var(--primary-blue);
    }
    
    /* アラート・通知 */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid var(--accent-orange);
        font-size: 14px;
    }
    
    .stSuccess {
        border-left-color: #28a745;
    }
    
    .stError {
        border-left-color: #dc3545;
    }
    
    /* フッター */
    .system-footer {
        background: var(--dark-blue);
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        text-align: center;
        margin-top: 24px;
        font-size: 14px;
    }
    
    /* エキスパンダー */
    .streamlit-expanderHeader {
        background: var(--light-gray);
        border-radius: 8px;
        border-left: 4px solid var(--primary-blue);
        font-size: 14px;
    }
    
    /* データフレーム */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
    
    /* プログレスバー */
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--primary-blue) 0%, var(--light-blue) 100%);
    }
    
    /* チャート */
    .stPlotlyChart {
        background: white;
        border-radius: 8px;
        padding: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
</style>
"""

# Streamlit設定
SYSTEM_CONFIG = {
    **STREAMLIT_CONFIG,
    "page_icon": "🏗️",
}
st.set_page_config(**SYSTEM_CONFIG)

# スタイル適用
st.markdown(SYSTEM_STYLE, unsafe_allow_html=True)

def load_sample_construction_data() -> List[ConstructionProject]:
    """サンプル建設データを読み込み"""
    try:
        data_file = CONSTRUCTION_DATA_DIR / "project_reports_mapping.json"
        if not data_file.exists():
            logger.warning(f"Construction data file not found: {data_file}")
            return []
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        projects = []
        for project_data in data:
            
            project = ConstructionProject(
                project_id=project_data["project_id"],
                project_name=project_data["project_name"],
                location=project_data["location"],
                current_phase=project_data.get("current_phase", "計画中"),
                phases=[],  # プロジェクトマスターには詳細フェーズ情報がないため空
                risk_level=RiskLevel.LOW,  # デフォルト値
                start_date=datetime.fromisoformat(project_data["start_date"]) if project_data.get("start_date") and project_data["start_date"] != "未定" else None,
                estimated_completion=datetime.fromisoformat(project_data["estimated_completion"]) if project_data.get("estimated_completion") and project_data["estimated_completion"] != "未定" else None,
                responsible_person=project_data.get("responsible_person", "未定")
            )
            projects.append(project)
        
        return projects
    except Exception as e:
        logger.error(f"Failed to load construction data: {e}")
        return []

def load_and_process_documents(llm_provider: str = "ollama") -> List[DocumentReport]:
    """文書を読み込んで処理"""
    try:
        processor = DocumentProcessor(llm_provider=llm_provider, create_vector_store=False)
        reports = processor.process_directory(SHAREPOINT_DOCS_DIR)
        return reports
    except Exception as e:
        logger.error(f"Failed to process documents: {e}")
        st.error(f"文書処理中にエラーが発生しました: {str(e)}")
        return []

def _deserialize_report(data: Dict[str, Any]) -> Optional[DocumentReport]:
    """JSONデータからDocumentReportオブジェクトを復元"""
    try:
        from app.models.report import StatusFlag, RiskLevel, ConstructionStatus, AnalysisResult, AnomalyDetection
        
        report = DocumentReport(
            file_path=data["file_path"],
            file_name=data["file_name"],
            report_type=ReportType(data["report_type"]) if data.get("report_type") else ReportType.PROGRESS_UPDATE,
            content=data.get("content", data.get("content_preview", "")),  # contentを優先、なければcontent_preview
            created_at=datetime.fromisoformat(data.get("processed_at", datetime.now().isoformat())),
            project_id=data.get("project_id")  # プロジェクトID復元
        )
        
        # AnalysisResult復元（簡素化構造）
        if data.get("analysis_result"):
            analysis = data["analysis_result"]
            report.analysis_result = AnalysisResult(
                summary=analysis.get("summary", ""),
                issues=analysis.get("issues", []),
                key_points=analysis.get("key_points", "").split(",") if analysis.get("key_points") else [],
                confidence=float(analysis.get("confidence", 0.0))
            )
        
        # AnomalyDetection復元（新構造）
        if data.get("anomaly_detection"):
            anomaly = data["anomaly_detection"]
            report.anomaly_detection = AnomalyDetection(
                is_anomaly=bool(anomaly.get("is_anomaly", anomaly.get("has_anomaly", False))),  # 後方互換性
                anomaly_description=anomaly.get("anomaly_description", anomaly.get("explanation", "")),  # 後方互換性
                confidence=float(anomaly.get("confidence", 0.0)),
                suggested_action=anomaly.get("suggested_action", ""),
                requires_human_review=bool(anomaly.get("requires_human_review", False)),
                similar_cases=anomaly.get("similar_cases", [])
            )
        
        # 新しいフラグ体系復元
        if data.get("status_flag"):
            report.status_flag = StatusFlag(data["status_flag"])
        
        # category_labels削除: 15カテゴリ遅延理由体系に統一
        
        if data.get("risk_level"):
            report.risk_level = RiskLevel(data["risk_level"])
        
        # urgency_score復元
        report.urgency_score = data.get("urgency_score", 1)
        
        # データ品質監視フィールド復元
        report.has_unexpected_values = data.get("has_unexpected_values", False)
        if data.get("validation_issues"):
            if isinstance(data["validation_issues"], list):
                report.validation_issues = data["validation_issues"]
            else:
                report.validation_issues = data["validation_issues"].split(",") if data["validation_issues"] else []
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to deserialize report: {e}")
        return None

def load_preprocessed_documents() -> List[DocumentReport]:
    """事前処理済み文書データを読み込み（バイナリキャッシュ + 並列処理）"""
    try:
        processed_reports_dir = Path("data/processed_reports")
        
        if not processed_reports_dir.exists():
            st.warning("⚠️ 事前処理が実行されていません。以下のコマンドを実行してください:")
            st.code("python scripts/preprocess_documents.py")
            return []
        
        from app.utils.streaming_loader import StreamingLoader
        
        streaming_loader = StreamingLoader(max_workers=3, batch_size=5)
        
        # プログレス表示
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        start_time = time.time()
        reports = []
        
        for current_count, total_count, batch_reports in streaming_loader.load_reports_streaming(processed_reports_dir):
            progress = current_count / total_count if total_count > 0 else 0
            progress_placeholder.progress(progress, text=f"📊 レポート読み込み中... ({current_count}/{total_count}件)")
            
            if batch_reports:
                status_placeholder.info(f"⚡ {len(batch_reports)}件を読み込み完了")
                reports.extend(batch_reports)
        
        load_time = time.time() - start_time
        
        progress_placeholder.empty()
        if reports:
            status_placeholder.success(f"✅ 全{len(reports)}件のレポートを{load_time:.2f}秒で読み込み完了")
            logger.info(f"🚀 Loaded {len(reports)} documents in {load_time:.3f}s using streaming")
        else:
            status_placeholder.warning("⚠️ 処理済みレポートが見つかりません")
        
        return reports
        
    except Exception as e:
        logger.error(f"Failed to load preprocessed documents: {e}")
        st.error(f"事前処理済みデータの読み込み中にエラーが発生しました: {str(e)}")
        return []

def render_sidebar() -> str:
    """サイドバーを表示"""
    with st.sidebar:
        # システムヘッダー
        st.markdown("""
        <div class='sidebar-header'>
            <h1>工程報告書チェック</h1>
            <p>LLM連携システム</p>
        </div>
        """, unsafe_allow_html=True)
        
        # チェック内容選択
        st.markdown("<div class='custom-header'>チェック内容</div>", unsafe_allow_html=True)
        audit_type = st.radio(
            "チェック内容を選択:",
            ["報告書", "工程"],
            index=0,
            key="audit_type"
        )
        
        st.divider()
        
        # ナビゲーション（チェック内容に応じて表示）
        st.markdown("<div class='custom-header'>ナビゲーション</div>", unsafe_allow_html=True)
        
        if audit_type == "報告書":
            page = st.radio(
                "表示したいページを選択:",
                ["報告書管理", "報告書一覧", "AI対話分析"],
                index=0,
                label_visibility="collapsed"
            )
        else:  # 工程
            page = st.radio(
                "表示したいページを選択:",
                ["工程管理", "工程一覧", "AI対話分析"],
                index=0,
                label_visibility="collapsed"
            )
        
        st.divider()
        
        # LLMプロバイダ選択
        st.markdown("<div class='custom-header'>LLMプロバイダ</div>", unsafe_allow_html=True)
        provider = st.selectbox(
            "使用するLLMプロバイダを選択:",
            ["ollama", "openai", "anthropic"],
            index=0,
            key="selected_llm_provider"
        )
        
        # 接続テスト
        from app.services.llm_service import LLMService
        try:
            test_service = LLMService(provider, force_test=False)
            provider_info = test_service.get_provider_info()
            
            if provider_info["status"] == "connected":
                st.success(f"✅ {provider_info['model']}")
            else:
                st.error(f"❌ 接続エラー")
        except Exception as e:
            st.error(f"❌ {str(e)}")
        
        # 備考
        st.markdown("<div class='custom-header' style='font-size: 18px; margin: 16px 0 8px 0;'>備考</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background-color: #f0f0f0; padding: 12px; border-radius: 4px; margin-bottom: 16px;">
        <span style="color: #666; font-size: 14px;">
        工程報告書チェックは、建設工程管理を効率化するAIアシスタントです。各種報告書を自動分析し、工程の状況把握・リスク評価・緊急度判定を行います。7段階建設工程（置局発注→基本同意→基本図承認→内諾→附帯着工→電波発射→工事検収）の進捗管理と、15カテゴリ遅延理由体系による問題分析で、現場の状況を的確に把握できます。分析結果は参考情報として活用し、最終判断は現場情報と照合してください。
        </span>
        </div>
        """, unsafe_allow_html=True)
        
        return page

def load_confirmed_mappings():
    """確定済みマッピング情報を読み込み"""
    confirmed_file = Path("data/confirmed_mappings.json")
    if confirmed_file.exists():
        try:
            with open(confirmed_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"確定済みマッピング読み込みエラー: {e}")
    return {}

def save_confirmed_mappings(confirmed_mappings: dict):
    """確定済みマッピング情報を保存"""
    confirmed_file = Path("data/confirmed_mappings.json")
    try:
        with open(confirmed_file, 'w', encoding='utf-8') as f:
            json.dump(confirmed_mappings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"確定済みマッピング保存エラー: {e}")

def update_source_data(file_name: str, new_project_id: str):
    """元データ（JSON/キャッシュファイル）を更新"""
    try:
        logger.info(f"Starting update_source_data: file_name={file_name}, new_project_id={new_project_id}")
        
        # JSONファイルの更新（複数の拡張子に対応）
        base_name = file_name
        for ext in ['.xlsx', '.docx', '.pdf', '.txt']:
            base_name = base_name.replace(ext, '')
        
        json_file = Path(f"data/processed_reports/{base_name}.json")
        logger.info(f"JSON file path: {json_file}")
        
        if not json_file.exists():
            logger.error(f"JSON file does not exist: {json_file}")
            logger.error(f"Original file_name: {file_name}, Base name: {base_name}")
            # 処理済みディレクトリの内容をログ出力
            processed_dir = Path("data/processed_reports")
            if processed_dir.exists():
                files = list(processed_dir.glob("*.json"))
                logger.error(f"Available JSON files: {[f.name for f in files]}")
            return False
            
        # ファイル読み込み
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Successfully loaded JSON file")
        except Exception as e:
            logger.error(f"Failed to load JSON file: {e}")
            return False
        
        # プロジェクトIDを更新
        old_project_id = data.get('project_id')
        data['project_id'] = new_project_id
        logger.info(f"Updated project_id: {old_project_id} -> {new_project_id}")
        
        # project_mapping_infoを更新
        if data.get('project_mapping_info'):
            data['project_mapping_info']['confidence_score'] = 1.0
            data['project_mapping_info']['matching_method'] = 'manual_correction'
            data['project_mapping_info']['extracted_info'] = {'manual_update': new_project_id}
        else:
            data['project_mapping_info'] = {
                'confidence_score': 1.0,
                'matching_method': 'manual_correction',
                'alternative_candidates': [],
                'extracted_info': {'manual_update': new_project_id}
            }
        logger.info("Updated project_mapping_info")
        
        # validation_issuesからプロジェクトマッピング関連を削除
        if 'validation_issues' in data:
            original_issues = len(data['validation_issues'])
            data['validation_issues'] = [
                issue for issue in data['validation_issues'] 
                if 'プロジェクトマッピング' not in issue
            ]
            logger.info(f"Removed validation issues: {original_issues} -> {len(data['validation_issues'])}")
            
            if not data['validation_issues']:
                data['has_unexpected_values'] = False
                logger.info("Set has_unexpected_values to False")
        
        # requires_mapping_reviewフラグをFalseに設定（確定済みのため）
        data['requires_mapping_review'] = False
        logger.info("Set requires_mapping_review to False (confirmed mapping)")
        
        # JSONファイルを保存
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Successfully saved JSON file: {json_file}")
        except Exception as e:
            logger.error(f"Failed to save JSON file: {e}")
            return False
        
        # キャッシュファイルも更新（存在する場合）
        cache_file = json_file.with_suffix('.cache')
        if cache_file.exists():
            try:
                cache_file.unlink()
                logger.info(f"Deleted cache file for regeneration: {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to delete cache file: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"元データ更新エラー: {e}", exc_info=True)
        return False

def load_fresh_reports():
    """最新のレポートデータを直接ファイルシステムから読み込み"""
    try:
        from app.utils.cache_loader import CacheLoader
        processed_reports_dir = Path("data/processed_reports")
        
        if not processed_reports_dir.exists():
            return []
        
        cache_loader = CacheLoader(max_workers=3)
        reports = cache_loader.load_reports_parallel(processed_reports_dir)
        logger.info(f"Fresh reports loaded: {len(reports)} reports")
        return reports
    except Exception as e:
        logger.error(f"Fresh reports loading error: {e}")
        return []

def render_report_editor(reports: List[DocumentReport]):
    """報告書編集・更新機能"""
    st.markdown("<div class='custom-header'>報告書編集・更新</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>確認必須の報告書を選択して内容を編集・更新できます</p>", unsafe_allow_html=True)
    
    # セッション状態に保存されたメッセージを表示
    if 'report_edit_message' in st.session_state:
        message_type, message_text = st.session_state.report_edit_message
        if message_type == 'success':
            st.success(message_text)
        elif message_type == 'error':
            st.error(message_text)
        elif message_type == 'warning':
            st.warning(message_text)
        
        # メッセージクリアボタン
        if st.button("🗑️ メッセージクリア", key="clear_report_edit_message"):
            del st.session_state.report_edit_message
            st.rerun()
    
    # 確認必須の報告書のみを対象
    required_review_reports = [r for r in reports if getattr(r, 'requires_content_review', False)]
    
    if not required_review_reports:
        st.success("✅ 編集が必要な報告書はありません。")
        return
    
    # セッション状態で確定済み報告書を管理
    if 'confirmed_edited_reports' not in st.session_state:
        st.session_state.confirmed_edited_reports = set()
    
    # 確定済みを除外
    pending_reports = [r for r in required_review_reports if r.file_path not in st.session_state.confirmed_edited_reports]
    
    if not pending_reports:
        st.success("✅ すべての報告書の編集が完了しました。")
        return
    
    # セッション状態で選択された報告書を管理
    if 'selected_report_index' not in st.session_state:
        st.session_state.selected_report_index = None
    
    # テーブル表示
    table_data = []
    for i, report in enumerate(pending_reports):
        # 確認理由の詳細を取得
        reasons = []
        if getattr(report, 'delay_reasons', []) and any("重大問題" in str(reason) for reason in report.delay_reasons):
            reasons.append("遅延理由分類困難")
        if getattr(report, 'validation_issues', []):
            # 具体的な不足項目を抽出
            missing_fields = []
            for issue in report.validation_issues:
                if "必須項目不足:" in issue:
                    field_name = issue.replace("必須項目不足:", "").strip()
                    missing_fields.append(field_name)
            if missing_fields:
                reasons.append(f"必須項目不足({', '.join(missing_fields)})")
            else:
                reasons.append("必須項目不足")
        if getattr(report, 'requires_human_review', False):
            reasons.append("LLM分析困難")
        
        reason_text = ", ".join(reasons) if reasons else "その他"
        
        # 現在選択されているかどうか
        is_selected = (st.session_state.selected_report_index == i)
        
        table_data.append({
            "選択": is_selected,
            "ファイル名": report.file_name,
            "プロジェクトID": report.project_id or "未抽出",
            "確認理由": reason_text,
            "作成日時": report.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # データフレーム表示
    df = pd.DataFrame(table_data)
    edited_df = st.data_editor(
        df,
        column_config={
            "選択": st.column_config.CheckboxColumn(
                "選択",
                help="編集する報告書を選択（1つのみ選択可能）",
                default=False,
            )
        },
        disabled=["ファイル名", "プロジェクトID", "確認理由", "作成日時"],
        hide_index=True,
        use_container_width=True,
        key="report_editor_table"
    )
    
    # 単一選択ロジック：新しく選択された項目を検出
    selected_indices = edited_df[edited_df["選択"] == True].index.tolist()
    
    if selected_indices:
        new_selection = selected_indices[-1]  # 最後に選択されたものを使用
        if st.session_state.selected_report_index != new_selection:
            st.session_state.selected_report_index = new_selection
            st.rerun()  # 他の選択を解除するために再実行
    elif st.session_state.selected_report_index is not None:
        # すべての選択が解除された場合
        st.session_state.selected_report_index = None
    
    if st.session_state.selected_report_index is not None:
        selected_index = st.session_state.selected_report_index
        selected_report = pending_reports[selected_index]
        
        st.markdown(f"### 📝 {selected_report.file_name} の編集")
        
        # 編集フォーム
        with st.form(f"edit_form_{selected_report.file_name}"):
            # 必須項目の不足チェック
            validation_issues = getattr(selected_report, 'validation_issues', [])
            missing_fields = []
            if validation_issues:
                for issue in validation_issues:
                    if 'missing_fields' in issue:
                        missing_fields.extend(issue['missing_fields'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                # プロジェクトID（必須）
                project_id_missing = 'プロジェクトID' in missing_fields
                project_id_label = "プロジェクトID ⚠️（必須）" if project_id_missing else "プロジェクトID（必須）"
                
                # プロジェクトID入力（視覚的強調付き）
                if project_id_missing:
                    st.markdown("""
                    <div style="padding: 8px; background-color: #ffebee; border: 2px solid #f44336; border-radius: 4px; margin-bottom: 8px;">
                    """, unsafe_allow_html=True)
                    project_id = st.text_input(
                        project_id_label, 
                        value=selected_report.project_id or "",
                        help="⚠️ この項目が不足しています",
                        key=f"project_id_{selected_index}"
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.error("⚠️ プロジェクトIDが不足しています")
                else:
                    project_id = st.text_input(
                        project_id_label, 
                        value=selected_report.project_id or "",
                        help="必須項目です",
                        key=f"project_id_{selected_index}"
                    )
                
                # auRoraプラン（必須）
                aurora_plan_missing = 'auRoraプラン' in missing_fields or 'auRoraプラン名' in missing_fields
                aurora_plan_label = "auRoraプラン ⚠️（必須）" if aurora_plan_missing else "auRoraプラン（必須）"
                
                # LLMの出力から取得を試行
                llm_aurora_plan = ""
                if hasattr(selected_report, 'llm_extraction_result') and selected_report.llm_extraction_result:
                    llm_aurora_plan = selected_report.llm_extraction_result.get('aurora_plan', '')
                elif hasattr(selected_report, 'analysis_result') and selected_report.analysis_result:
                    # analysis_resultから取得を試行
                    llm_aurora_plan = getattr(selected_report.analysis_result, 'aurora_plan', '')
                
                # auRoraプラン入力（視覚的強調付き）
                if aurora_plan_missing:
                    with st.container():
                        st.markdown("""
                        <div style="padding: 8px; background-color: #ffebee; border: 2px solid #f44336; border-radius: 4px; margin-bottom: 8px;">
                        <strong>⚠️ 不足項目</strong>
                        </div>
                        """, unsafe_allow_html=True)
                        aurora_plan = st.text_input(
                            aurora_plan_label,
                            value=llm_aurora_plan or "",
                            help="⚠️ この項目が不足しています",
                            key=f"aurora_plan_{selected_index}"
                        )
                        st.error("⚠️ auRoraプランが不足しています")
                else:
                    aurora_plan = st.text_input(
                        aurora_plan_label,
                        value=llm_aurora_plan or "",
                        help="必須項目です",
                        key=f"aurora_plan_{selected_index}"
                    )
                
                # 局名（必須）
                station_name_missing = '局名' in missing_fields
                station_name_label = "局名 ⚠️（必須）" if station_name_missing else "局名（必須）"
                
                # LLMの出力から取得を試行
                llm_station_name = ""
                if hasattr(selected_report, 'llm_extraction_result') and selected_report.llm_extraction_result:
                    llm_station_name = selected_report.llm_extraction_result.get('station_name', '')
                elif hasattr(selected_report, 'analysis_result') and selected_report.analysis_result:
                    llm_station_name = getattr(selected_report.analysis_result, 'station_name', '')
                
                # 局名入力（視覚的強調付き）
                if station_name_missing:
                    with st.container():
                        st.markdown("""
                        <div style="padding: 8px; background-color: #ffebee; border: 2px solid #f44336; border-radius: 4px; margin-bottom: 8px;">
                        <strong>⚠️ 不足項目</strong>
                        </div>
                        """, unsafe_allow_html=True)
                        station_name = st.text_input(
                            station_name_label,
                            value=llm_station_name or "",
                            help="⚠️ この項目が不足しています",
                            key=f"station_name_{selected_index}"
                        )
                        st.error("⚠️ 局名が不足しています")
                else:
                    station_name = st.text_input(
                        station_name_label,
                        value=llm_station_name or "",
                        help="必須項目です",
                        key=f"station_name_{selected_index}"
                    )
                
                # 住所（必須）
                address_missing = '住所' in missing_fields
                address_label = "住所 ⚠️（必須）" if address_missing else "住所（必須）"
                
                # LLMの出力から取得を試行
                llm_address = ""
                if hasattr(selected_report, 'llm_extraction_result') and selected_report.llm_extraction_result:
                    llm_address = selected_report.llm_extraction_result.get('location', '')
                elif hasattr(selected_report, 'analysis_result') and selected_report.analysis_result:
                    llm_address = getattr(selected_report.analysis_result, 'location', '')
                
                # 住所入力（視覚的強調付き）
                if address_missing:
                    with st.container():
                        st.markdown("""
                        <div style="padding: 8px; background-color: #ffebee; border: 2px solid #f44336; border-radius: 4px; margin-bottom: 8px;">
                        <strong>⚠️ 不足項目</strong>
                        </div>
                        """, unsafe_allow_html=True)
                        address = st.text_input(
                            address_label,
                            value=llm_address or "",
                            help="⚠️ この項目が不足しています",
                            key=f"address_{selected_index}"
                        )
                        st.error("⚠️ 住所が不足しています")
                else:
                    address = st.text_input(
                        address_label,
                        value=llm_address or "",
                        help="必須項目です",
                        key=f"address_{selected_index}"
                    )
                
                # 報告書種別（必須）
                report_type_missing = '報告書種別' in missing_fields
                report_type_label = "報告書種別 ⚠️（必須）" if report_type_missing else "報告書種別（必須）"
                report_type_mapping = {
                    "工事見積書": "CONSTRUCTION_ESTIMATE",
                    "進捗報告書": "PROGRESS_UPDATE", 
                    "工事報告書": "CONSTRUCTION_REPORT",
                    "トラブル報告書": "TROUBLE_REPORT",
                    "交渉進捗報告書": "NEGOTIATION_PROGRESS",
                    "構造設計書": "STRUCTURAL_DESIGN",
                    "その他": "OTHER"
                }
                reverse_report_type_mapping = {v: k for k, v in report_type_mapping.items()}
                report_type_options = list(report_type_mapping.keys())
                current_report_type = selected_report.report_type.value if selected_report.report_type else "OTHER"
                current_display = reverse_report_type_mapping.get(current_report_type, "その他")
                report_type_display = st.selectbox(
                    report_type_label,
                    report_type_options,
                    index=report_type_options.index(current_display) if current_display in report_type_options else 0,
                    help="必須項目です" if not report_type_missing else "⚠️ この項目が不足しています"
                )
                report_type = report_type_mapping[report_type_display]
                if report_type_missing:
                    st.error("⚠️ 報告書種別が不足しています")
            
            with col2:
                # ステータス（必須）
                status_missing = 'ステータス' in missing_fields
                status_label = "ステータス ⚠️（必須）" if status_missing else "ステータス（必須）"
                status_options = ["順調", "軽微な遅延", "重大な遅延", "停止"]
                current_status = selected_report.status_flag.value if selected_report.status_flag else "normal"
                status_mapping = {"順調": "normal", "軽微な遅延": "minor_delay", "重大な遅延": "major_delay", "停止": "stopped"}
                reverse_status_mapping = {v: k for k, v in status_mapping.items()}
                status_display = reverse_status_mapping.get(current_status, "順調")
                status = st.selectbox(
                    status_label,
                    status_options,
                    index=status_options.index(status_display),
                    help="必須項目です" if not status_missing else "⚠️ この項目が不足しています"
                )
                if status_missing:
                    st.error("⚠️ ステータスが不足しています")
                
                # リスクレベル（必須）
                risk_missing = 'リスクレベル' in missing_fields
                risk_label = "リスクレベル ⚠️（必須）" if risk_missing else "リスクレベル（必須）"
                risk_options = ["低", "中", "高"]
                current_risk = selected_report.risk_level.value if selected_report.risk_level else "低"
                risk = st.selectbox(
                    risk_label,
                    risk_options,
                    index=risk_options.index(current_risk),
                    help="必須項目です" if not risk_missing else "⚠️ この項目が不足しています"
                )
                if risk_missing:
                    st.error("⚠️ リスクレベルが不足しています")
                
                # 緊急度スコア（必須）
                urgency_missing = '緊急度スコア' in missing_fields
                urgency_label = "緊急度スコア ⚠️（必須）" if urgency_missing else "緊急度スコア（必須）"
                urgency_options = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
                current_urgency = selected_report.urgency_score or 3
                urgency = st.selectbox(
                    urgency_label,
                    urgency_options,
                    index=urgency_options.index(current_urgency) if current_urgency in urgency_options else 2,
                    help="必須項目です" if not urgency_missing else "⚠️ この項目が不足しています"
                )
                if urgency_missing:
                    st.error("⚠️ 緊急度スコアが不足しています")
                
                # 担当者（任意）
                # LLMの出力から取得を試行
                llm_responsible_person = ""
                if hasattr(selected_report, 'llm_extraction_result') and selected_report.llm_extraction_result:
                    llm_responsible_person = selected_report.llm_extraction_result.get('responsible_person', '')
                elif hasattr(selected_report, 'analysis_result') and selected_report.analysis_result:
                    llm_responsible_person = getattr(selected_report.analysis_result, 'responsible_person', '')
                responsible_person = st.text_input(
                    "担当者",
                    value=llm_responsible_person or "",
                    help="任意項目です"
                )
            
            # 要約（任意、全幅）
            st.markdown("**要約**")
            # LLMの出力から取得を試行
            llm_summary = ""
            if hasattr(selected_report, 'analysis_result') and selected_report.analysis_result:
                llm_summary = selected_report.analysis_result.summary or ""
            summary = st.text_area(
                "要約",
                value=llm_summary or "",
                height=100,
                help="任意項目です"
            )
            
            # 遅延理由
            st.markdown("**遅延理由**")
            delay_reasons_text = st.text_area("遅延理由（1行に1つずつ記入）", 
                                            value="\n".join([str(reason) for reason in selected_report.delay_reasons]) if selected_report.delay_reasons else "", 
                                            height=100)
            
            # 更新ボタン
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                confirm_submitted = st.form_submit_button("✅ 確定", use_container_width=True)
            with col_btn2:
                update_confirm_submitted = st.form_submit_button("🔄 更新・確定", use_container_width=True)
            
            if confirm_submitted or update_confirm_submitted:
                try:
                    if update_confirm_submitted:
                        # 報告書データを更新
                        selected_report.project_id = project_id
                        
                        # ステータス更新
                        from app.models.report import StatusFlag, RiskLevel
                        selected_report.status_flag = StatusFlag(status_mapping[status])
                        selected_report.risk_level = RiskLevel(risk)
                        selected_report.urgency_score = urgency
                        
                        # 分析結果更新
                        if selected_report.analysis_result:
                            selected_report.analysis_result.summary = summary
                            # issues と key_points は既存の値を保持（入力フィールドが削除されているため）
                            # selected_report.analysis_result.issues = [issue.strip() for issue in issues.split('\n') if issue.strip()]
                            # selected_report.analysis_result.key_points = [point.strip() for point in key_points.split('\n') if point.strip()]
                        
                        # 遅延理由更新
                        selected_report.delay_reasons = [reason.strip() for reason in delay_reasons_text.split('\n') if reason.strip()]
                        
                        # JSONファイルに保存
                        json_path = Path(f"data/processed_reports/{selected_report.file_name.replace('.xlsx', '.json').replace('.docx', '.json').replace('.pdf', '.json').replace('.txt', '.json')}")
                        logger.info(f"報告書更新: JSONファイルパス = {json_path}")
                        
                        if json_path.exists():
                            # 既存のJSONデータを読み込み
                            with open(json_path, 'r', encoding='utf-8') as f:
                                json_data = json.load(f)
                            logger.info(f"報告書更新: JSONファイル読み込み成功")
                            
                            # データを更新
                            json_data['project_id'] = project_id
                            json_data['status_flag'] = status_mapping[status]
                            json_data['risk_level'] = risk
                            json_data['urgency_score'] = urgency
                            
                            # analysis_resultが存在することを確認
                            if 'analysis_result' not in json_data:
                                json_data['analysis_result'] = {}
                            json_data['analysis_result']['summary'] = summary
                            
                            # issues と key_points は既存の値を保持
                            # json_data['analysis_result']['issues'] = [issue.strip() for issue in issues.split('\n') if issue.strip()]
                            # json_data['analysis_result']['key_points'] = [point.strip() for point in key_points.split('\n') if point.strip()]
                            json_data['delay_reasons'] = [reason.strip() for reason in delay_reasons_text.split('\n') if reason.strip()]
                            
                            # validation_issuesを更新（必須項目チェック）
                            validation_issues = []
                            if not project_id or project_id.strip() == "":
                                validation_issues.append("必須項目不足: プロジェクトID")
                            if not aurora_plan or aurora_plan.strip() == "" or aurora_plan == "不明":
                                validation_issues.append("必須項目不足: auRoraプラン名")
                            if not station_name or station_name.strip() == "" or station_name == "不明":
                                validation_issues.append("必須項目不足: 局名")
                            if not address or address.strip() == "" or address == "不明":
                                validation_issues.append("必須項目不足: 住所")
                            if not report_type or report_type == "選択してください":
                                validation_issues.append("必須項目不足: 報告書種別")
                            if not status or status == "選択してください":
                                validation_issues.append("必須項目不足: ステータス")
                            if not risk or risk == "選択してください":
                                validation_issues.append("必須項目不足: リスクレベル")
                            
                            json_data['validation_issues'] = validation_issues
                            json_data['has_unexpected_values'] = len(validation_issues) > 0
                            json_data['requires_content_review'] = len(validation_issues) > 0
                            
                            logger.info(f"報告書更新: データ更新完了 - validation_issues: {len(validation_issues)}件")
                            
                            # ファイルに保存
                            with open(json_path, 'w', encoding='utf-8') as f:
                                json.dump(json_data, f, ensure_ascii=False, indent=2)
                            logger.info(f"報告書更新: JSONファイル保存成功")
                            
                            # 対応するキャッシュファイルも更新
                            cache_path = json_path.with_suffix('.cache')
                            if cache_path.exists():
                                try:
                                    import pickle
                                    # キャッシュファイルを読み込み
                                    with open(cache_path, 'rb') as f:
                                        cached_report = pickle.load(f)
                                    
                                    # キャッシュファイルのデータも更新
                                    cached_report.project_id = project_id
                                    cached_report.status_flag = StatusFlag(status_mapping[status])
                                    cached_report.risk_level = RiskLevel(risk)
                                    cached_report.urgency_score = urgency
                                    if cached_report.analysis_result:
                                        cached_report.analysis_result.summary = summary
                                    cached_report.delay_reasons = [reason.strip() for reason in delay_reasons_text.split('\n') if reason.strip()]
                                    cached_report.validation_issues = validation_issues
                                    cached_report.has_unexpected_values = len(validation_issues) > 0
                                    cached_report.requires_content_review = len(validation_issues) > 0
                                    
                                    # キャッシュファイルを保存
                                    with open(cache_path, 'wb') as f:
                                        pickle.dump(cached_report, f)
                                    logger.info(f"報告書更新: キャッシュファイル更新成功")
                                except Exception as cache_error:
                                    logger.warning(f"キャッシュファイル更新エラー: {cache_error}")
                        else:
                            logger.error(f"報告書更新: JSONファイルが見つかりません: {json_path}")
                            raise FileNotFoundError(f"JSONファイルが見つかりません: {json_path}")
                    
                    # 確定済みリストに追加
                    st.session_state.confirmed_edited_reports.add(selected_report.file_path)
                    
                    # 成功メッセージをセッション状態に保存
                    if update_confirm_submitted:
                        st.session_state.report_edit_message = ('success', f"✅ 報告書「{selected_report.file_name}」を更新し、確定しました！\nデータファイルも更新されました。")
                    else:
                        st.session_state.report_edit_message = ('success', f"✅ 報告書「{selected_report.file_name}」を確定しました！")
                    
                    st.rerun()
                        
                except Exception as e:
                    # エラーメッセージをセッション状態に保存
                    st.session_state.report_edit_message = ('error', f"❌ 報告書「{selected_report.file_name}」の更新に失敗しました: {str(e)}")
                    st.rerun()
    else:
        st.info("📝 編集する報告書を選択してください。")

def render_project_mapping_review(reports: List[DocumentReport]):
    """案件紐づけ信頼度管理"""
    st.markdown("<div class='custom-header'>案件紐づけ信頼度管理</div>", unsafe_allow_html=True)
    st.markdown("ベクター検索による案件紐づけの確認と修正")
    
    # セッション状態がクリアされている場合は最新データを読み込み
    if 'reports' not in st.session_state:
        fresh_reports = load_fresh_reports()
        if fresh_reports:
            reports = fresh_reports
    
    # 確定済みマッピングのクリーンアップ（事前処理再実行対応）
    cleanup_confirmed_mappings(reports)
    
    # 信頼度が低い案件紐づけの件数を事前計算して表示
    if reports:
        # 信頼度が低いマッピングを抽出（更新失敗も含む）
        low_confidence_reports = []
        confirmed_mappings = load_confirmed_mappings()  # ファイルから直接読み込み
        
        for report in reports:
            is_confirmed = report.file_name in confirmed_mappings
            is_update_failed = getattr(report, '_update_failed', False)
            
            # 表示対象の判定
            should_show = False
            
            # 🚨 最優先: 確定済みの場合は表示対象外（更新失敗を除く）
            if is_confirmed and not is_update_failed:
                should_show = False
            else:
                # 1. project_mapping_infoがあり、ベクター検索を使用した場合（信頼度が低い場合のみ）
                if (hasattr(report, 'project_mapping_info') and 
                        report.project_mapping_info):
                    
                    method = report.project_mapping_info.get('matching_method', 'unknown')
                    
                    # 直接抽出できた場合は表示対象外（高信頼度）
                    if method == 'llm_direct':
                        should_show = False
                    # ベクター検索の場合は表示対象（信頼度に関わらず表示）
                    elif method == 'vector_search':
                        extracted_info = report.project_mapping_info.get('extracted_info', {})
                        vector_similarity = extracted_info.get('vector_similarity', 0.0)
                        should_show = True
                
                # 2. プロジェクトマッピング失敗（project_id=None）の場合
                elif (report.project_id is None and 
                      hasattr(report, 'validation_issues') and
                      any('プロジェクトマッピング' in issue for issue in report.validation_issues)):
                    should_show = True
                    # マッピング失敗の理由を詳細表示用に設定
                    if hasattr(report, 'project_mapping_info') and report.project_mapping_info:
                        method = report.project_mapping_info.get('matching_method', 'mapping_failed')
                        if method == 'mapping_failed':
                            report.project_mapping_info['matching_method'] = 'ベクターキャッシュ未初期化'
                        elif method == 'vector_search_unavailable':
                            report.project_mapping_info['matching_method'] = 'ベクター検索利用不可'
                        elif method == 'direct_id_failed':
                            report.project_mapping_info['matching_method'] = 'プロジェクトID抽出失敗'
                
                # 3. 更新失敗の場合
                elif is_update_failed:
                    should_show = True
                
            if should_show:
                # 更新失敗フラグを追加
                report._update_failed = is_update_failed
                low_confidence_reports.append(report)
        
        # 警告メッセージを表示
        if low_confidence_reports:
            st.warning(f"⚠️ 信頼度が低い案件紐づけ: {len(low_confidence_reports)}件")
    
    # 永続メッセージの表示
    if 'mapping_message' in st.session_state:
        message_type, message_text = st.session_state.mapping_message
        if message_type == 'success':
            st.success(message_text)
        elif message_type == 'error':
            st.error(message_text)
        elif message_type == 'warning':
            st.warning(message_text)
    
    # リフレッシュボタンを追加
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        if st.button("🔄 最新データを読み込み"):
            # 最新のレポートデータを読み込み
            fresh_reports = load_fresh_reports()
            if fresh_reports:
                reports = fresh_reports
                st.session_state.mapping_message = ('success', f"✅ {len(reports)}件のレポートを読み込みました")
            else:
                st.session_state.mapping_message = ('warning', "⚠️ レポートの読み込みに失敗しました")
            st.rerun()
    
    with col3:
        if st.button("🗑️ メッセージクリア"):
            if 'mapping_message' in st.session_state:
                del st.session_state.mapping_message
            st.rerun()
    
    
    if not reports:
        st.info("レポートがありません。")
        return
    
    # 永続化された確定済みマッピングを読み込み
    persistent_confirmed = load_confirmed_mappings()
    
    # セッション状態と統合
    if 'confirmed_mappings' not in st.session_state:
        st.session_state.confirmed_mappings = {}
    
    # 永続化データをセッション状態に統合
    for file_name, project_id in persistent_confirmed.items():
        if file_name not in st.session_state.confirmed_mappings:
            st.session_state.confirmed_mappings[file_name] = project_id
    
        # 既に上で計算済みのlow_confidence_reportsを使用
    
    # 信頼度の低い順でソート（マッピング失敗は信頼度0として扱う）
    def get_confidence(report):
        if report.project_mapping_info:
            mapping_info = report.project_mapping_info
            method = mapping_info.get('matching_method', 'unknown')
            
            # ベクトル検索の場合はベクトル類似度を使用
            if method == 'vector_search':
                extracted_info = mapping_info.get('extracted_info', {})
                return extracted_info.get('vector_similarity', 0.0)
            else:
                # 直接ID指定などの場合は従来の信頼度スコア
                return mapping_info.get('confidence_score', 1.0)
        else:
            return 0.0  # マッピング失敗は最低信頼度
    
    low_confidence_reports.sort(key=get_confidence)
    
    if not low_confidence_reports:
        st.success("✅ すべての案件紐づけが確定済みまたは高信頼度です。")
        return
    
    # プロジェクトマスタを読み込み
    try:
        import json
        with open('/home/share/eng-llm-app/data/sample_construction_data/project_reports_mapping.json', 'r', encoding='utf-8') as f:
            project_master = json.load(f)
        project_options = {p['project_id']: f"{p['project_id']} - {p['project_name']}" for p in project_master}
    except Exception as e:
        st.error(f"プロジェクトマスタの読み込みに失敗しました: {e}")
        return
    
    # 各レポートの確認
    for i, report in enumerate(low_confidence_reports[:10]):  # 最大10件表示
        if report.project_mapping_info:
            mapping_info = report.project_mapping_info
            method = mapping_info.get('matching_method', 'unknown')
            
            # ベクトル検索の場合はベクトル類似度を表示
            if method == 'vector_search':
                extracted_info = mapping_info.get('extracted_info', {})
                confidence = extracted_info.get('vector_similarity', 0.0)
            else:
                # 直接ID指定などの場合は従来の信頼度スコア
                confidence = mapping_info.get('confidence_score', 0.0)
        else:
            # マッピング失敗の場合
            confidence = 0.0
            method = 'mapping_failed'
            mapping_info = {}
        
        # 更新失敗の場合は特別な表示
        is_update_failed = getattr(report, '_update_failed', False)
        status_icon = "❌" if is_update_failed else "📄"
        status_text = " (更新失敗)" if is_update_failed else ""
        
        with st.expander(f"{status_icon} {report.file_name} (信頼度: {confidence:.2f}){status_text}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**現在のマッピング:** {report.project_id or '失敗'}")
                st.write(f"**信頼度スコア:** {confidence:.2f}")
                # マッピング手法の日本語表示
                method_display = {
                    'vector_search': 'ベクトル検索',
                    'direct_id': '直接ID指定',
                    'vector_search_unavailable': 'ベクトル検索不可'
                }.get(method, method)
                st.write(f"**マッピング手法:** {method_display}")
                
                # 更新失敗の場合は詳細を表示
                if is_update_failed:
                    expected_id = getattr(report, '_expected_project_id', '不明')
                    st.error(f"⚠️ **ファイル更新失敗**: 手動設定値 {expected_id} がファイルに反映されていません（現在値: {report.project_id or 'None'}）")
                
                if mapping_info.get('extracted_info'):
                    extracted_info = mapping_info['extracted_info']
                    
                    # 抽出情報（検索時のインプットデータ）を表示
                    if extracted_info.get('query_text'):
                        st.write("**抽出情報:**")
                        st.write(f"検索クエリ: {extracted_info['query_text']}")
                    elif extracted_info.get('matched_keywords'):
                        st.write("**抽出情報:**")
                        keywords = extracted_info['matched_keywords']
                        if isinstance(keywords, list):
                            st.write(f"キーワード: {', '.join(keywords)}")
                        else:
                            st.write(f"キーワード: {keywords}")
                    
                    # 🆕 紐づけ根拠表示
                    if method == 'vector_search' and extracted_info.get('reasoning'):
                        st.write("**紐づけ根拠:**")
                        st.write(f"{extracted_info['reasoning']}")
                        

                

            
            with col2:
                # 確定ボタン
                if st.button("✅ 確定", key=f"confirm_{i}"):
                    # セッション状態に確定情報を保存
                    if 'confirmed_mappings' not in st.session_state:
                        st.session_state.confirmed_mappings = {}
                    st.session_state.confirmed_mappings[report.file_name] = report.project_id or '失敗'
                    
                    # 永続化
                    save_confirmed_mappings(st.session_state.confirmed_mappings)
                    # 成功メッセージをセッション状態に保存
                    st.session_state.mapping_message = ('success', "✅ 確定しました！")
                    st.rerun()
                
                # プロジェクト変更
                st.write("**プロジェクト変更:**")
                new_project = st.selectbox(
                    "正しいプロジェクトを選択",
                    options=list(project_options.keys()),
                    format_func=lambda x: project_options[x],
                    key=f"project_select_{i}"
                )
                
                if st.button("🔄 更新・確定", key=f"update_{i}"):
                    # セッション状態に更新・確定情報を保存
                    if 'updated_mappings' not in st.session_state:
                        st.session_state.updated_mappings = {}
                    if 'confirmed_mappings' not in st.session_state:
                        st.session_state.confirmed_mappings = {}
                    
                    st.session_state.updated_mappings[report.file_name] = new_project
                    st.session_state.confirmed_mappings[report.file_name] = new_project
                    
                    # 元データ（JSON/キャッシュファイル）を更新
                    try:
                        if update_source_data(report.file_name, new_project):
                            # 成功メッセージをセッション状態に保存
                            st.session_state.mapping_message = ('success', f"✅ プロジェクトを {new_project} に更新・確定しました！\n元データも更新されました。")
                            # セッション状態をクリアして再読み込みを促す
                            if 'reports' in st.session_state:
                                del st.session_state.reports
                            # 最新データを即座に読み込み
                            fresh_reports = load_fresh_reports()
                            if fresh_reports:
                                reports = fresh_reports
                        else:
                            # エラーメッセージをセッション状態に保存
                            st.session_state.mapping_message = ('error', f"❌ 元データの更新に失敗しました。\nファイル: {report.file_name}\n\n**考えられる原因:**\n• 事前処理が実行されていない\n• ファイルが処理済みディレクトリに存在しない\n\n**対処法:**\n1. 事前処理を実行してください\n2. 処理済みファイルが生成されてから再試行してください")
                    except Exception as e:
                        # 予期しないエラーの場合
                        st.session_state.mapping_message = ('error', f"❌ 予期しないエラーが発生しました: {str(e)}")
                    
                    # 永続化
                    save_confirmed_mappings(st.session_state.confirmed_mappings)
                    st.rerun()

def calculate_confidence_statistics(reports: List[DocumentReport]) -> Dict[str, Any]:
    """信頼度統計を計算"""
    if not reports:
        return {'average': 0.0, 'high_confidence': 0, 'low_confidence': 0, 'mapping_failed': 0}
    
    # 全体の信頼度を収集
    confidences = []
    high_confidence_count = 0
    low_confidence_count = 0
    mapping_failed_count = 0
    
    for report in reports:
        # 分析全体の信頼度
        overall_confidence = getattr(report, 'analysis_confidence', 0.0)
        if hasattr(report, 'analysis_metadata') and report.analysis_metadata:
            overall_confidence = report.analysis_metadata.get('overall_confidence', overall_confidence)
        
        confidences.append(overall_confidence)
        
        # 高信頼度・低信頼度の判定
        if overall_confidence >= 0.8:
            high_confidence_count += 1
        elif overall_confidence < 0.6:
            low_confidence_count += 1
        
        # マッピング失敗の判定
        if not report.project_id or report.project_id == '不明':
            mapping_failed_count += 1
    
    average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    
    return {
        'average': average_confidence,
        'high_confidence': high_confidence_count,
        'low_confidence': low_confidence_count,
        'mapping_failed': mapping_failed_count,
        'total': len(reports)
    }

def analyze_item_confidence(reports: List[DocumentReport]) -> Dict[str, Dict[str, float]]:
    """項目別信頼度分析"""
    item_stats = {}
    
    for report in reports:
        if not hasattr(report, 'confidence_details') or not report.confidence_details:
            continue
        
        for item, confidence in report.confidence_details.items():
            if item not in item_stats:
                item_stats[item] = []
            item_stats[item].append(confidence)
    
    # 平均信頼度を計算
    result = {}
    for item, confidences in item_stats.items():
        if confidences:
            result[item] = {
                'average': sum(confidences) / len(confidences),
                'count': len(confidences),
                'min': min(confidences),
                'max': max(confidences)
            }
    
    return result

def display_detailed_reasoning(report: DocumentReport):
    """詳細な推論根拠を表示"""
    if hasattr(report, 'analysis_metadata') and report.analysis_metadata:
        st.write("**🤖 分析メタデータ:**")
        metadata = report.analysis_metadata
        st.write(f"• 全体信頼度: {metadata.get('overall_confidence', 0.0):.2f}")
        st.write(f"• 分析サマリ: {metadata.get('analysis_summary', '不明')}")
        
        if metadata.get('difficult_items'):
            st.write(f"• 困難項目: {', '.join(metadata['difficult_items'])}")
        if metadata.get('high_confidence_items'):
            st.write(f"• 高信頼度項目: {', '.join(metadata['high_confidence_items'])}")
    
    if hasattr(report, 'confidence_details') and report.confidence_details:
        st.write("**📊 項目別信頼度:**")
        for item, confidence in report.confidence_details.items():
            color = '🟢' if confidence > 0.8 else '🟡' if confidence > 0.6 else '🔴'
            st.write(f"• {color} {item}: {confidence:.2f}")
    
    if hasattr(report, 'evidence_details') and report.evidence_details:
        st.write("**🔍 根拠詳細:**")
        for item, evidence in report.evidence_details.items():
            if evidence and evidence != '':
                st.write(f"• **{item}**: {evidence}")

def render_data_quality_dashboard(reports: List[DocumentReport]):
    """報告書統計ダッシュボード"""
    st.markdown("<div class='custom-header'>報告書統計</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>報告書の品質管理と人的確認が必要な報告書の特定</p>", unsafe_allow_html=True)
    
    if not reports:
        st.warning("⚠️ 監視対象のレポートがありません。")
        return
    
    # フォルダ配下の全報告書数を取得（実際の値）
    from pathlib import Path
    sharepoint_docs_dir = Path("data/sharepoint_docs")
    actual_total_files_in_folder = 0
    if sharepoint_docs_dir.exists():
        supported_extensions = {'.txt', '.pdf', '.docx', '.xlsx'}
        for file_path in sharepoint_docs_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                actual_total_files_in_folder += 1
    
    # 人的確認フラグに基づく分類（実際の値）
    actual_ai_analyzed_reports = len(reports)  # 分析済み
    content_review_reports = [r for r in reports if getattr(r, 'requires_content_review', False)]
    mapping_review_reports = [r for r in reports if getattr(r, 'requires_mapping_review', False)]
    
    # 確認必須：報告書内容確認が必要
    required_review_reports = content_review_reports
    
    # 確認推奨：案件紐づけ確認が必要（案件紐づけ信頼度管理と同じロジック）
    confirmed_mappings = load_confirmed_mappings()  # ファイルから直接読み込み
    recommended_review_reports = []
    
    for report in reports:
        is_confirmed = report.file_name in confirmed_mappings
        is_update_failed = getattr(report, '_update_failed', False)
        
        should_include = False
        
        if is_confirmed and not is_update_failed:
            should_include = False
        else:
            if (hasattr(report, 'project_mapping_info') and 
                    report.project_mapping_info):
                method = report.project_mapping_info.get('matching_method', 'unknown')
                
                if method == 'llm_direct':
                    should_include = False
                elif method == 'vector_search':
                    should_include = True
            
            # プロジェクトマッピング失敗の場合
            elif (report.project_id is None and 
                  hasattr(report, 'validation_issues') and
                  any('プロジェクトマッピング' in issue for issue in report.validation_issues)):
                should_include = True
            
            # 更新失敗の場合
            elif is_update_failed:
                should_include = True
        
        if should_include:
            recommended_review_reports.append(report)
    
    # 問題なし：確認不要（どちらのフラグもない）
    actual_no_issues_reports = actual_ai_analyzed_reports - len(set([r.file_path for r in content_review_reports + mapping_review_reports]))
    
    # ダミー数値を適用
    from app.config.dummy_data import get_report_audit_metrics
    actual_metrics = {
        "total_in_folder": actual_total_files_in_folder,
        "analyzed_reports": actual_ai_analyzed_reports,
        "required_review": len(required_review_reports),
        "recommended_review": len(recommended_review_reports),
        "no_issues": actual_no_issues_reports
    }
    
    metrics = get_report_audit_metrics(actual_metrics)
    
    # 表示用の値を設定
    total_files_in_folder = metrics["total_in_folder"]
    ai_analyzed_reports = metrics["analyzed_reports"]
    no_issues_reports = metrics["no_issues"]
    
    # データ品質メトリクス（4列レイアウト）
    col1, col2, col3, col4 = st.columns(4)
    
    # 分数・％計算（ダミー数値を使用）
    ai_analyzed_percentage = (ai_analyzed_reports / total_files_in_folder * 100) if total_files_in_folder > 0 else 0
    required_percentage = (metrics["required_review"] / ai_analyzed_reports * 100) if ai_analyzed_reports > 0 else 0
    recommended_percentage = (metrics["recommended_review"] / ai_analyzed_reports * 100) if ai_analyzed_reports > 0 else 0
    no_issues_percentage = (no_issues_reports / ai_analyzed_reports * 100) if ai_analyzed_reports > 0 else 0
    
    # 案件管理と同じスタイルを適用
    st.markdown("""
    <style>
    .metric-card-updated {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        text-align: center;
        border: 1px solid #e1e5e9;
    }
    .metric-card-updated h3 {
        font-size: 1.4rem !important;
        margin: 0 0 0.5rem 0 !important;
        color: #666 !important;
        font-weight: 600 !important;
        line-height: 1.2 !important;
        text-align: left !important;
    }
    .metric-card-updated h2 {
        margin: 0.5rem 0 !important;
        font-size: 3rem !important;
        font-weight: bold !important;
    }
    .metric-card-updated p {
        margin: 0 !important;
        color: #888 !important;
        font-size: 0.9rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card-updated'>
            <h3>分析済み</h3>
            <h2 style='color: #0052CC;'>{ai_analyzed_reports}<sub style='font-size: 0.8em; color: #666;'>/{total_files_in_folder}</sub></h2>
            <p>{ai_analyzed_percentage:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        color = "#dc3545" if metrics["required_review"] > 0 else "#28a745"
        st.markdown(f"""
        <div class='metric-card-updated'>
            <h3>確認必須</h3>
            <h2 style='color: {color};'>{metrics["required_review"]}<sub style='font-size: 0.8em; color: #666;'>/{ai_analyzed_reports}</sub></h2>
            <p>{required_percentage:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        color = "#fd7e14" if metrics["recommended_review"] > 0 else "#28a745"
        st.markdown(f"""
        <div class='metric-card-updated'>
            <h3>確認推奨</h3>
            <h2 style='color: {color};'>{metrics["recommended_review"]}<sub style='font-size: 0.8em; color: #666;'>/{ai_analyzed_reports}</sub></h2>
            <p>{recommended_percentage:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class='metric-card-updated'>
            <h3>問題なし</h3>
            <h2 style='color: #28a745;'>{no_issues_reports}<sub style='font-size: 0.8em; color: #666;'>/{ai_analyzed_reports}</sub></h2>
            <p>{no_issues_percentage:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 確認必須の理由別集計（推奨アクション用）
    required_reasons = {}
    for report in required_review_reports:
        reasons = []
        # 遅延理由分類困難
        if getattr(report, 'delay_reasons', []) and any("重大問題" in str(reason) for reason in report.delay_reasons):
            reasons.append("遅延理由分類困難")
        # 必須項目不足
        if getattr(report, 'validation_issues', []):
            reasons.append("必須項目不足")
        # LLM分析困難
        if getattr(report, 'requires_human_review', False):
            reasons.append("LLM分析困難")
        
        if not reasons:
            reasons = ["その他"]
        
        for reason in reasons:
            required_reasons[reason] = required_reasons.get(reason, 0) + 1
    
    # 確認推奨の理由別集計（推奨アクション用）
    # 案件紐づけ信頼度管理と同じロジックを使用
    recommended_reasons = {}
    confirmed_mappings_for_actions = load_confirmed_mappings()  # ファイルから直接読み込み
    
    for report in reports:
        is_confirmed = report.file_name in confirmed_mappings_for_actions
        is_update_failed = getattr(report, '_update_failed', False)
        
        # 案件紐づけ信頼度管理と同じ表示対象判定
        should_include = False
        
        if is_confirmed and not is_update_failed:
            should_include = False
        else:
            if (hasattr(report, 'project_mapping_info') and 
                    report.project_mapping_info):
                method = report.project_mapping_info.get('matching_method', 'unknown')
                
                if method == 'llm_direct':
                    should_include = False
                elif method == 'vector_search':
                    should_include = True
            
            # プロジェクトマッピング失敗の場合
            elif (report.project_id is None and 
                  hasattr(report, 'validation_issues') and
                  any('プロジェクトマッピング' in issue for issue in report.validation_issues)):
                should_include = True
            
            # 更新失敗の場合
            elif is_update_failed:
                should_include = True
        
        if should_include:
            reasons = []
            
            # LLM信頼度低
            if getattr(report, 'analysis_confidence', 1.0) < 0.7:
                reasons.append("LLM信頼度低の報告書確認")
            
            # 案件紐づけ確認
            mapping_info = getattr(report, 'project_mapping_info', {})
            method = mapping_info.get('matching_method', '不明') if mapping_info else '不明'
            if method == 'vector_search' or report.project_id is None:
                reasons.append("案件紐づけ確認")
            
            if not reasons:
                reasons = ["その他"]
            
            for reason in reasons:
                recommended_reasons[reason] = recommended_reasons.get(reason, 0) + 1
    
    # 推奨アクション
    st.markdown("<div class='custom-header'>推奨アクション</div>", unsafe_allow_html=True)
    
    actions = []
    if required_reasons.get("遅延理由分類困難", 0) > 0:
        actions.append(("required", "遅延理由分類困難", f"{required_reasons.get('遅延理由分類困難', 0)}件", "15カテゴリ体系に該当しない遅延理由を人的確認し、適切なカテゴリに分類してください"))
    if required_reasons.get("必須項目不足", 0) > 0:
        actions.append(("required", "必須項目不足", f"{required_reasons.get('必須項目不足', 0)}件", "プロジェクトID、局名、担当者等の必須項目を確認・補完してください"))
    if required_reasons.get("LLM分析困難", 0) > 0:
        actions.append(("required", "LLM分析困難", f"{required_reasons.get('LLM分析困難', 0)}件", "文書内容が複雑または不明瞭なため、人的確認による分析が必要です"))
    if recommended_reasons.get("LLM信頼度低の報告書確認", 0) > 0:
        actions.append(("recommended", "LLM信頼度低の報告書確認", f"{recommended_reasons.get('LLM信頼度低の報告書確認', 0)}件", "LLMの分析信頼度が低い報告書の内容を確認してください"))
    if recommended_reasons.get("案件紐づけ確認", 0) > 0:
        actions.append(("recommended", "案件紐づけ確認", f"{recommended_reasons.get('案件紐づけ確認', 0)}件", "類似度に基づく案件紐づけの妥当性を確認してください"))
    
    if actions:
        for action_type, title, count, description in actions:
            if action_type == "required":
                st.markdown(f"""
                <div style='background-color: #ffebee; border-left: 4px solid #f44336; padding: 12px; margin: 8px 0; border-radius: 4px;'>
                    <strong style='color: #d32f2f;'>⚠️ {title}: {count}</strong><br>
                    <span style='color: #666; font-size: 14px;'>{description}</span>
                </div>
                """, unsafe_allow_html=True)
            else:  # recommended
                st.markdown(f"""
                <div style='background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 12px; margin: 8px 0; border-radius: 4px;'>
                    <strong style='color: #f57c00;'>⚠️ {title}: {count}</strong><br>
                    <span style='color: #666; font-size: 14px;'>{description}</span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.success("✅ 現在、対応が必要な問題はありません。")
    
    # 要確認タイプ別統計
    st.markdown("<div class='custom-header'>要確認タイプ別統計</div>", unsafe_allow_html=True)
    
    # 棒グラフ表示
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 確認必須の理由別内訳")
        # 50音順 + その他で固定順序
        all_required_reasons = ["必須項目不足", "遅延理由分類困難", "LLM分析困難", "その他"]
        # ラベルを短縮
        required_labels = ["必須項目不足", "遅延理由困難", "LLM分析困難", "その他"]
        required_counts = [required_reasons.get(reason, 0) for reason in all_required_reasons]
        
        if sum(required_counts) > 0:
            import plotly.graph_objects as go
            fig_required = go.Figure(data=[
                go.Bar(
                    x=required_labels,
                    y=required_counts,
                    marker_color='#ffcdd2',  # 薄い赤
                    text=required_counts,
                    textposition='auto',
                )
            ])
            fig_required.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=20, b=60),
                xaxis=dict(tickangle=45),
                showlegend=False
            )
            st.plotly_chart(fig_required, use_container_width=True)
        else:
            st.success("✅ 確認必須の報告書はありません。")
    
    with col2:
        st.markdown("#### 確認推奨の理由別内訳")
        # 50音順 + その他で固定順序
        all_recommended_reasons = ["LLM信頼度低", "案件紐づけ確認", "その他"]
        # ラベルを短縮
        recommended_labels = ["LLM信頼度低", "案件紐づけ確認", "その他"]
        recommended_counts = [recommended_reasons.get("LLM信頼度低の報告書確認", 0), recommended_reasons.get("案件紐づけ確認", 0), recommended_reasons.get("その他", 0)]
        
        if sum(recommended_counts) > 0:
            import plotly.graph_objects as go
            fig_recommended = go.Figure(data=[
                go.Bar(
                    x=recommended_labels,
                    y=recommended_counts,
                    marker_color='#ffe0b2',  # 薄いオレンジ
                    text=recommended_counts,
                    textposition='auto',
                )
            ])
            fig_recommended.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=20, b=60),
                xaxis=dict(tickangle=45),
                showlegend=False
            )
            st.plotly_chart(fig_recommended, use_container_width=True)
        else:
            st.success("✅ 確認推奨の報告書はありません。")
    

    # 報告書編集・更新
    render_report_editor(reports)
    
    # 案件紐づけ信頼度管理
    render_project_mapping_review(reports)
    


def main():
    """メインアプリケーション"""
    try:
        # システムメインヘッダー
        st.markdown("""
        <div class='main-header'>
            <h1>工程報告書チェック</h1>
            <p>効率的な工程管理とAI支援分析システム</p>
        </div>
        """, unsafe_allow_html=True)
        
        # ページ選択（セッション状態からのページ遷移対応）
        selected_page = render_sidebar()
        
        # セッション状態でページ遷移が指定されている場合は上書き
        if 'current_page' in st.session_state:
            selected_page = st.session_state.current_page
            # セッション状態をリセット（一回限りの遷移）
            del st.session_state.current_page
        
        # データ読み込み
        if 'reports' not in st.session_state or 'projects' not in st.session_state or 'context_analysis' not in st.session_state:
            with st.spinner("事前処理済みデータを読み込み中..."):
                st.session_state.reports = load_preprocessed_documents()
                st.session_state.projects = load_sample_construction_data()
                st.session_state.context_analysis = load_context_analysis()
        

        
        reports = st.session_state.reports
        projects = st.session_state.projects
        context_analysis = st.session_state.context_analysis
        
        # ページルーティング
        if selected_page == "工程管理":
            # 🆕 統合分析ベースのプロジェクト表示
            if context_analysis:
                # 統合分析結果から ProjectSummary を作成
                from app.services.integration_aggregator import IntegrationAggregator
                integration_aggregator = IntegrationAggregator()
                project_summaries = integration_aggregator.create_project_summaries_from_context(
                    context_analysis, reports, projects
                )
            else:
                # フォールバック: 従来の集約方式
                st.warning("統合分析結果が見つかりません。従来の集約方式を使用します。")
            aggregator = ProjectAggregator()
            project_summaries = aggregator.aggregate_projects(reports)
            
            # 全件表示フラグの処理
            if st.session_state.get('show_all_projects', False):
                # 全工程表示
                st.markdown("<div class='custom-header'>全工程一覧</div>", unsafe_allow_html=True)
                from app.ui.project_dashboard import _render_all_projects_table
                _render_all_projects_table(project_summaries, show_more_link=False)
                
                if st.button("🔙 ダッシュボードに戻る", use_container_width=True):
                    st.session_state.show_all_projects = False
                    st.rerun()
            else:
                # 通常のダッシュボード表示
                render_project_dashboard(project_summaries, reports)
        elif selected_page == "工程一覧":
            # 🆕 統合分析ベースの工程一覧ページ
            if context_analysis:
                # 統合分析結果から ProjectSummary を作成
                from app.services.integration_aggregator import IntegrationAggregator
                integration_aggregator = IntegrationAggregator()
                project_summaries = integration_aggregator.create_project_summaries_from_context(
                    context_analysis, reports, projects
                )
            else:
                # フォールバック: 従来の集約方式
                st.warning("統合分析結果が見つかりません。従来の集約方式を使用します。")
            aggregator = ProjectAggregator()
            project_summaries = aggregator.aggregate_projects(reports)
            
            from app.ui.project_list import render_project_list
            render_project_list(project_summaries, reports)
        elif selected_page == "報告書一覧":
            render_report_list(reports)
        elif selected_page == "AI対話分析":
            # チェック内容を取得
            audit_type = st.session_state.get('audit_type', '工程')
            render_analysis_panel(reports, audit_type)
        elif selected_page == "報告書管理":
            render_data_quality_dashboard(reports)
        
        # システムフッター
        st.markdown("""
        <div class='system-footer'>
            <strong>工程報告書チェック</strong> | Version """ + VERSION + """ | Powered by Ollama + llama3.3
        </div>
        """, unsafe_allow_html=True)
    
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error("アプリケーションエラーが発生しました。")
        st.exception(e)

def load_confirmed_mappings() -> Dict[str, str]:
    """確定済みマッピングを読み込み"""
    try:
        confirmed_file = Path("data/confirmed_mappings.json")
        if confirmed_file.exists():
            with open(confirmed_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Failed to load confirmed mappings: {e}")
        return {}

def save_confirmed_mappings(mappings: Dict[str, str]):
    """確定済みマッピングを保存"""
    try:
        confirmed_file = Path("data/confirmed_mappings.json")
        with open(confirmed_file, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, ensure_ascii=False, indent=2)
        logger.info(f"Confirmed mappings saved: {len(mappings)} entries")
    except Exception as e:
        logger.error(f"Failed to save confirmed mappings: {e}")

def load_context_analysis() -> Dict[str, Any]:
    """統合分析結果を読み込み"""
    try:
        context_file = Path("data/context_analysis/context_analysis.json")
        if context_file.exists():
            with open(context_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning("統合分析結果ファイルが見つかりません")
            return {}
    except Exception as e:
        logger.error(f"統合分析結果の読み込みに失敗しました: {e}")
        return {}

def cleanup_confirmed_mappings(reports: List[DocumentReport]):
    """確定済みマッピングをクリーンアップ（事前処理再実行対応）"""
    try:
        confirmed_mappings = load_confirmed_mappings()
        if not confirmed_mappings:
            return
        
        # 現在のレポートファイル名とプロジェクトIDのマッピング
        current_mappings = {report.file_name: report.project_id for report in reports}
        
        # 不整合のあるマッピングを特定
        inconsistent_files = []
        for file_name, confirmed_project_id in confirmed_mappings.items():
            current_project_id = current_mappings.get(file_name)
            if current_project_id is not None and current_project_id != confirmed_project_id:
                inconsistent_files.append(file_name)
                logger.info(f"Inconsistent mapping detected: {file_name} - confirmed: {confirmed_project_id}, current: {current_project_id}")
        
        # 不整合のあるマッピングを削除
        if inconsistent_files:
            for file_name in inconsistent_files:
                del confirmed_mappings[file_name]
            
            # 更新されたマッピングを保存
            save_confirmed_mappings(confirmed_mappings)
            logger.info(f"Cleaned up {len(inconsistent_files)} inconsistent mappings")
            
            # ユーザーに通知
            if len(inconsistent_files) > 0:
                st.info(f"📋 **事前処理再実行により{len(inconsistent_files)}件のマッピングが更新されました**\n"
                       f"以前の手動設定値と異なる結果になったファイルの確定状態をリセットしました。")
    
    except Exception as e:
        logger.error(f"Failed to cleanup confirmed mappings: {e}")

if __name__ == "__main__":
    main()