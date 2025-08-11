"""
建設管理システム連動LLMアプリ - メインアプリケーション
Aurora-LLM Connector

KDDI様向けデモアプリケーション
"""
import streamlit as st
import logging
import json
import time
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
from app.models.report import DocumentReport, ReportType, FlagType
from app.models.construction import ConstructionProject, PhaseStatus, RiskLevel, ConstructionPhase
from app.services.document_processor import DocumentProcessor
from app.services.flag_classifier import FlagClassifier
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
        data_file = CONSTRUCTION_DATA_DIR / "construction_phases.json"
        if not data_file.exists():
            logger.warning(f"Construction data file not found: {data_file}")
            return []
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        projects = []
        for project_data in data:
            phases = []
            for phase_data in project_data.get("phases", []):
                phase = ConstructionPhase(
                    name=phase_data["name"],
                    status=PhaseStatus(phase_data["status"]),
                    date=datetime.fromisoformat(phase_data["start_date"]) if phase_data.get("start_date") else None,
                    description=phase_data.get("description", "")
                )
                phases.append(phase)
            
            project = ConstructionProject(
                project_id=project_data["project_id"],
                project_name=project_data["project_name"],
                location=project_data["location"],
                current_phase=project_data.get("current_phase", "計画中"),
                phases=phases,
                risk_level=RiskLevel(project_data.get("risk_level", "low")),
                estimated_completion=datetime.fromisoformat(project_data["estimated_completion"]) if project_data.get("estimated_completion") else None
            )
            projects.append(project)
        
        return projects
    except Exception as e:
        logger.error(f"Failed to load construction data: {e}")
        return []

@st.cache_data(ttl=300)
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
        from app.models.report import StatusFlag, CategoryLabel, RiskLevel, ConstructionStatus, AnalysisResult, AnomalyDetection
        
        report = DocumentReport(
            file_path=data["file_path"],
            file_name=data["file_name"],
            report_type=ReportType(data["report_type"]) if data.get("report_type") else ReportType.PROGRESS_UPDATE,
            content=data.get("content", data.get("content_preview", "")),
            created_at=datetime.fromisoformat(data.get("processed_at", datetime.now().isoformat())),
            project_id=data.get("project_id")  # プロジェクトID復元
        )
        
        # AnalysisResult復元
        if data.get("analysis_result"):
            analysis = data["analysis_result"]
            report.analysis_result = AnalysisResult(
                key_points=analysis.get("key_points", "").split(",") if analysis.get("key_points") else [],
                recommended_flags=analysis.get("recommended_flags", "").split(",") if analysis.get("recommended_flags") else [],
                confidence=float(analysis.get("confidence", 0.0))
            )
        
        # AnomalyDetection復元
        if data.get("anomaly_detection"):
            anomaly = data["anomaly_detection"]
            report.anomaly_detection = AnomalyDetection(
                has_anomaly=bool(anomaly.get("has_anomaly", False)),
                anomaly_score=float(anomaly.get("anomaly_score", 0.0)),
                explanation=anomaly.get("explanation", "")
            )
        
        # 新しいフラグ体系復元
        if data.get("status_flag"):
            report.status_flag = StatusFlag(data["status_flag"])
        
        if data.get("category_labels"):
            category_strs = data["category_labels"].split(",") if isinstance(data["category_labels"], str) else data["category_labels"]
            report.category_labels = [CategoryLabel(cat.strip()) for cat in category_strs if cat.strip()]
        
        if data.get("risk_level"):
            report.risk_level = RiskLevel(data["risk_level"])
        
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

@st.cache_data(ttl=60)
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
            <h1>建設管理AI</h1>
            <p>LLM連携システム</p>
        </div>
        """, unsafe_allow_html=True)
        
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
        
        st.divider()
        
        # ナビゲーション
        st.markdown("<div class='custom-header'>ナビゲーション</div>", unsafe_allow_html=True)
        page = st.radio(
            "表示したいページを選択:",
            ["プロジェクト管理", "AI対話分析", "プロジェクト一覧", "レポート一覧", "データ品質監視"],
            label_visibility="collapsed"
        )
        
        # 備考
        st.markdown("<div class='custom-header' style='font-size: 18px; margin: 16px 0 8px 0;'>備考</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background-color: #f0f0f0; padding: 12px; border-radius: 4px; margin-bottom: 16px;">
        <span style="color: #666; font-size: 14px;">
        このダッシュボードでは、auRoraとSynapseのデータおよび各種報告書を基に統合LLM分析を活用し、レポートタイプ判定・ステータス・リスク・問題区分の抽出・緊急度スコアの算出・建設工程8段階の進捗推定・プロジェクト自動紐づけ（マルチ戦略：直接ID抽出＋ベクター検索）・分析困難度評価を1回の呼び出しで実施しています。分析結果には誤差が含まれる可能性があるため、最終判断は必ず現場情報と照合してください。
        </span>
        </div>
        """, unsafe_allow_html=True)
        
        return page

def render_data_quality_dashboard(reports: List[DocumentReport]):
    """データ品質監視ダッシュボード"""
    # データ品質セクションヘッダー（建設管理AIタイトルは共通ヘッダーで表示済み）
    st.markdown("<div class='custom-header'>データ品質監視</div>", unsafe_allow_html=True)
    st.markdown("LLM出力の品質管理とシステムパフォーマンス監視")
    
    if not reports:
        st.warning("⚠️ 監視対象のレポートがありません。")
        return
    
    # 全体サマリー
    total_reports = len(reports)
    unexpected_reports = [r for r in reports if getattr(r, 'has_unexpected_values', False)]
    null_status = [r for r in reports if r.status_flag is None]
    null_categories = [r for r in reports if not r.category_labels]
    null_risk = [r for r in reports if r.risk_level is None]
    
    # シンプルメトリクス（3つに簡素化）
    col1, col2, col3 = st.columns(3)
    
    normal_reports = total_reports - len(unexpected_reports)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <h3>全レポート数</h3>
            <h2 style='color: #0052CC;'>{total_reports}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='metric-card'>
            <h3>異常値なし</h3>
            <h2 style='color: #28a745;'>{normal_reports}</h2>
            <p>{normal_reports/total_reports*100:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        unexpected_pct = len(unexpected_reports)/total_reports*100 if total_reports > 0 else 0
        color = "#FF6B35" if unexpected_pct > 10 else "#FFA500"
        st.markdown(f"""
        <div class='metric-card'>
            <h3>異常値あり</h3>
            <h2 style='color: {color};'>{len(unexpected_reports)}</h2>
            <p>{unexpected_pct:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 詳細分析
    if unexpected_reports:
        st.markdown("<div class='custom-header'>想定外値検出レポート</div>", unsafe_allow_html=True)
        
        for report in unexpected_reports:
            issues_count = len(getattr(report, 'validation_issues', []))
            with st.expander(f"{report.file_name} - {issues_count}件の問題"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write("**検出された問題:**")
                    for issue in getattr(report, 'validation_issues', []):
                        st.write(f"• {issue}")
                    
                    st.write("**現在の値:**")
                    st.write(f"• Status: {report.status_flag.value if report.status_flag else 'None'}")
                    st.write(f"• Categories: {[c.value for c in report.category_labels] if report.category_labels else 'None'}")
                    st.write(f"• Risk: {report.risk_level.value if report.risk_level else 'None'}")
                
                with col2:
                    st.text_area("内容", report.content[:200] + "...", height=150, key=f"content_{report.file_name}")
    
    # 問題タイプ別集計
    st.markdown("<div class='custom-header'>問題タイプ別統計</div>", unsafe_allow_html=True)
    
    if unexpected_reports:
        all_issues = []
        for report in unexpected_reports:
            all_issues.extend(getattr(report, 'validation_issues', []))
        
        issue_types = {}
        for issue in all_issues:
            issue_type = issue.split(':')[0] if ':' in issue else issue
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        st.bar_chart(issue_types)
    else:
        st.success("✓ 想定外値は検出されませんでした")
    
    # 対応提案
    st.markdown("<div class='custom-header'>推奨対応アクション</div>", unsafe_allow_html=True)
    
    if null_status or null_categories or null_risk:
        st.warning("**LLM出力の改善が必要:**")
        if null_status:
            st.write(f"• StatusFlag のNull値: {len(null_status)}件 → プロンプトの見直し")
        if null_categories:
            st.write(f"• CategoryLabel のNull値: {len(null_categories)}件 → キーワード辞書の拡充")
        if null_risk:
            st.write(f"• RiskLevel のNull値: {len(null_risk)}件 → リスク判定ロジックの改善")
    else:
        st.success("✓ 全フィールドが正常に設定されています")

def main():
    """メインアプリケーション"""
    try:
        # システムメインヘッダー
        st.markdown("""
        <div class='main-header'>
            <h1>建設管理アプリ</h1>
            <p>効率的なプロジェクト管理とAI支援分析システム</p>
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
        if 'reports' not in st.session_state or 'projects' not in st.session_state:
            with st.spinner("事前処理済みデータを読み込み中..."):
                st.session_state.reports = load_preprocessed_documents()
                st.session_state.projects = load_sample_construction_data()
        

        
        reports = st.session_state.reports
        projects = st.session_state.projects
        
        # ページルーティング
        if selected_page == "プロジェクト管理":
            # プロジェクト集約サービスでレポートを集約
            aggregator = ProjectAggregator()
            project_summaries = aggregator.aggregate_projects(reports)
            
            # 全件表示フラグの処理
            if st.session_state.get('show_all_projects', False):
                # 全プロジェクト表示
                st.markdown("<div class='custom-header'>全プロジェクト一覧</div>", unsafe_allow_html=True)
                from app.ui.project_dashboard import _render_all_projects_table
                _render_all_projects_table(project_summaries, show_more_link=False)
                
                if st.button("🔙 ダッシュボードに戻る", use_container_width=True):
                    st.session_state.show_all_projects = False
                    st.rerun()
            else:
                # 通常のダッシュボード表示
                render_project_dashboard(project_summaries, reports)
        elif selected_page == "プロジェクト一覧":
            # プロジェクト一覧ページ
            aggregator = ProjectAggregator()
            project_summaries = aggregator.aggregate_projects(reports)
            from app.ui.project_list import render_project_list
            render_project_list(project_summaries, reports)
        elif selected_page == "レポート一覧":
            render_report_list(reports)
        elif selected_page == "AI対話分析":
            render_analysis_panel(reports)
        elif selected_page == "データ品質監視":
            render_data_quality_dashboard(reports)
        
        # システムフッター
        st.markdown("""
        <div class='system-footer'>
            <strong>建設管理アプリ</strong> | Version """ + VERSION + """ | Powered by Ollama + llama3.3
        </div>
        """, unsafe_allow_html=True)
    
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error("アプリケーションエラーが発生しました。")
        st.exception(e)

if __name__ == "__main__":
    main()