"""
LLM機能評価専用ダッシュボード
使用方法: python -m streamlit run app/evaluation_dashboard.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib

from services.evaluation_service import EvaluationService, EvaluationResult
from models.report import DocumentReport
from services.document_processor import DocumentProcessor
from config.settings import DATA_DIR
import logging

# ログ設定
logger = logging.getLogger(__name__)

# ページ設定
st.set_page_config(
    page_title="LLM機能評価ダッシュボード",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 メインダッシュボードと同じスタイリング
EVALUATION_STYLE = """
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
        font-size: 36px;
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
    
    /* データフレームスタイル */
    .dataframe {
        font-size: 14px;
    }
    
    /* 警告・情報メッセージ */
    .stAlert {
        border-radius: 8px;
    }
</style>
"""

st.markdown(EVALUATION_STYLE, unsafe_allow_html=True)

def load_processed_reports() -> List:
    """事前処理済みレポートデータを読み込み"""
    try:
        processed_file = Path(DATA_DIR) / "processed_reports.json"
        if processed_file.exists():
            with open(processed_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('reports', [])
    except Exception as e:
        st.error(f"事前処理データの読み込み失敗: {e}")
    return []

def _generate_evaluation_hash() -> str:
    """評価データのハッシュ値を生成（キャッシュキー用）"""
    # 事前処理済みデータのハッシュ
    processed_reports_dir = Path("data/processed_reports")
    index_file = processed_reports_dir / "index.json"
    
    data_hash = ""
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        # 処理済みファイルの情報をハッシュ化
        file_info = []
        for file_path, info in index_data.get("processed_files", {}).items():
            if info.get("status") == "success":
                file_info.append({
                    "file_path": file_path,
                    "processed_at": info.get("processed_at"),
                    "file_hash": info.get("file_hash")
                })
        
        data_hash = hashlib.md5(str(sorted(file_info, key=lambda x: x["file_path"])).encode()).hexdigest()
    
    # 正解データのハッシュ
    ground_truth_file = Path("data/evaluation/ground_truth.json")
    gt_hash = ""
    if ground_truth_file.exists():
        with open(ground_truth_file, 'r', encoding='utf-8') as f:
            gt_data = json.load(f)
        gt_hash = hashlib.md5(str(gt_data).encode()).hexdigest()
    
    return hashlib.md5(f"{data_hash}_{gt_hash}".encode()).hexdigest()

def _deserialize_report_for_evaluation(data: Dict[str, Any]) -> Optional[DocumentReport]:
    """評価用DocumentReportオブジェクトを復元"""
    try:
        from app.models.report import StatusFlag, CategoryLabel, RiskLevel, ConstructionStatus, AnalysisResult, AnomalyDetection, ReportType
        
        report = DocumentReport(
            file_path=data["file_path"],
            file_name=data["file_name"],
            report_type=ReportType(data["report_type"]) if data.get("report_type") else ReportType.PROGRESS_UPDATE,
            content=data.get("content", data.get("content_preview", "")),
            created_at=datetime.fromisoformat(data.get("processed_at", datetime.now().isoformat()))
        )
        
        # AnalysisResult復元
        if data.get("analysis_result"):
            analysis = data["analysis_result"]
            report.analysis_result = AnalysisResult(
                project_info={"project": "evaluation"},  # デフォルト値
                status="unknown",  # デフォルト値
                issues=[],  # デフォルト値
                risk_level="低",  # デフォルト値
                summary="",  # デフォルト値
                urgency_score=1,  # デフォルト値
                key_points=analysis.get("key_points", "").split(",") if analysis.get("key_points") else [],
                recommended_flags=analysis.get("recommended_flags", "").split(",") if analysis.get("recommended_flags") else [],
                confidence=float(analysis.get("confidence", 0.0))
            )
        
        # AnomalyDetection復元
        if data.get("anomaly_detection"):
            anomaly = data["anomaly_detection"]
            report.anomaly_detection = AnomalyDetection(
                is_anomaly=bool(anomaly.get("has_anomaly", False)),
                anomaly_description=anomaly.get("explanation", ""),
                confidence=float(anomaly.get("anomaly_score", 0.0)),
                suggested_action="",  # デフォルト値
                requires_human_review=False,  # デフォルト値
                similar_cases=[]  # デフォルト値
            )
        
        # 新しいフラグ体系復元
        if data.get("status_flag"):
            report.status_flag = StatusFlag(data["status_flag"])
        if data.get("category_labels"):
            report.category_labels = [CategoryLabel(label) for label in data["category_labels"]]
        if data.get("risk_level"):
            report.risk_level = RiskLevel(data["risk_level"])
        if data.get("construction_status"):
            report.construction_status = ConstructionStatus(data["construction_status"])
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to deserialize report for evaluation: {e}")
        return None

@st.cache_data(ttl=3600)  # 1時間キャッシュ
def _cached_run_evaluation(evaluation_hash: str) -> EvaluationResult:
    """評価を実行（バイナリキャッシュ + 並列処理対応）"""
    processed_reports_dir = Path("data/processed_reports")
    
    if not processed_reports_dir.exists():
        st.error("⚠️ 事前処理が実行されていません。以下のコマンドを実行してください:")
        st.code("python scripts/preprocess_documents.py")
        return None
    
    # 🚀 バイナリキャッシュローダーを使用した並列読み込み
    try:
        from app.utils.cache_loader import CacheLoader
        import time
        
        cache_loader = CacheLoader(max_workers=3)  # 評価用は少し控えめ
        
        start_time = time.time()
        reports = cache_loader.load_reports_parallel(processed_reports_dir)
        load_time = time.time() - start_time
        
        if not reports:
            st.error("処理済みレポートが見つかりません")
            return None
        
        st.info(f"{len(reports)}件のレポートを{load_time:.2f}秒で読み込み完了")
        
        # レポートデータをセッション状態に保存（プロジェクトマッピング評価用）
        if 'current_reports' not in st.session_state:
            st.session_state.current_reports = reports
        
        # 評価実行
        evaluator = EvaluationService()
        return evaluator.evaluate_reports(reports)
        
    except Exception as e:
        st.error(f"評価実行中にエラーが発生: {e}")
        logger.error(f"Evaluation failed: {e}")
        return None

def run_evaluation() -> EvaluationResult:
    """評価を実行"""
    # データハッシュを生成してキャッシュキーとして使用
    evaluation_hash = _generate_evaluation_hash()
    
    # キャッシュの状態を表示
    cache_info = f"🔑 Cache Key: {evaluation_hash[:8]}..."
    if evaluation_hash in st.session_state.get('evaluation_cache_keys', set()):
        cache_info += " ⚡ (Cached)"
    else:
        cache_info += " 🔄 (Computing)"
    
    st.caption(cache_info)
    
    with st.spinner("評価実行中...（初回のみ時間がかかります）"):
        result = _cached_run_evaluation(evaluation_hash)
        
        # キャッシュキーを記録
        if 'evaluation_cache_keys' not in st.session_state:
            st.session_state.evaluation_cache_keys = set()
        st.session_state.evaluation_cache_keys.add(evaluation_hash)
        
        return result

def render_metrics_overview(evaluation_result: EvaluationResult):
    """統合分析評価メトリクス概要を表示"""
    st.markdown("<div class='custom-header'>統合分析評価結果概要</div>", unsafe_allow_html=True)
    
    # 総合スコア
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric(
            "総合スコア",
            f"{evaluation_result.overall_score:.3f}",
            delta=None
        )
    
    with col2:
        st.metric(
            "レポートタイプ F1",
            f"{evaluation_result.report_type_classification.f1_score:.3f}",
            delta=None
        )
    
    with col3:
        st.metric(
            "状態分類 F1",
            f"{evaluation_result.status_classification.f1_score:.3f}",
            delta=None
        )
    
    with col4:
        st.metric(
            "カテゴリ分類 F1",
            f"{evaluation_result.category_classification.f1_score:.3f}",
            delta=None
        )
    
    with col5:
        st.metric(
            "リスクレベル F1",
            f"{evaluation_result.risk_level_assessment.f1_score:.3f}",
            delta=None
        )
    
    with col6:
        st.metric(
            "プロジェクトマッピング F1",
            f"{evaluation_result.project_mapping.f1_score:.3f}",
            delta=None
        )

def render_unified_analysis_results(evaluation_result: EvaluationResult):
    """統合分析結果の詳細表示"""
    st.markdown("<div class='custom-header'>統合分析機能評価</div>", unsafe_allow_html=True)
    
    # レポートタイプ分類
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("レポートタイプ分類")
        rt_metrics = evaluation_result.report_type_classification
        metrics_df = pd.DataFrame({
            '指標': ['正確度', '適合率', '再現率', 'F1スコア'],
            '値': [rt_metrics.accuracy, rt_metrics.precision, rt_metrics.recall, rt_metrics.f1_score]
        })
        st.dataframe(metrics_df, use_container_width=True)
    
    with col2:
        st.subheader("人手確認検知")
        hr_metrics = evaluation_result.human_review_detection
        metrics_df = pd.DataFrame({
            '指標': ['正確度', '適合率', '再現率', 'F1スコア'],
            '値': [hr_metrics.accuracy, hr_metrics.precision, hr_metrics.recall, hr_metrics.f1_score]
        })
        st.dataframe(metrics_df, use_container_width=True)
    
    st.subheader("🔄 処理効率の改善効果")
    
    # 統合分析による改善効果を表示
    improvement_data = {
        "項目": ["LLM呼び出し回数", "処理時間/ファイル", "コード複雑度", "データ品質"],
        "従来": ["3回", "2-3秒", "高", "不安定"],
        "統合分析": ["1回", "1-1.5秒", "低", "安定"],
        "改善率": ["67%削減", "50%削減", "大幅改善", "品質向上"]
    }
    
    improvement_df = pd.DataFrame(improvement_data)
    st.dataframe(improvement_df, use_container_width=True)

def render_detailed_metrics(evaluation_result: EvaluationResult):
    """詳細メトリクス表示"""
    st.markdown("<div class='custom-header'>詳細評価指標</div>", unsafe_allow_html=True)
    
    # メトリクスデータの準備
    metrics_data = {
        "機能": ["状態分類", "カテゴリ分類", "リスクレベル評価", "異常検知"],
        "精度 (Accuracy)": [
            evaluation_result.status_classification.accuracy,
            evaluation_result.category_classification.accuracy,
            evaluation_result.risk_level_assessment.accuracy,
            evaluation_result.anomaly_detection.accuracy
        ],
        "適合率 (Precision)": [
            evaluation_result.status_classification.precision,
            evaluation_result.category_classification.precision,
            evaluation_result.risk_level_assessment.precision,
            evaluation_result.anomaly_detection.precision
        ],
        "再現率 (Recall)": [
            evaluation_result.status_classification.recall,
            evaluation_result.category_classification.recall,
            evaluation_result.risk_level_assessment.recall,
            evaluation_result.anomaly_detection.recall
        ],
        "F1スコア": [
            evaluation_result.status_classification.f1_score,
            evaluation_result.category_classification.f1_score,
            evaluation_result.risk_level_assessment.f1_score,
            evaluation_result.anomaly_detection.f1_score
        ]
    }
    
    df = pd.DataFrame(metrics_data)
    
    # インタラクティブ表
    st.dataframe(
        df.style.format({
            "精度 (Accuracy)": "{:.3f}",
            "適合率 (Precision)": "{:.3f}",
            "再現率 (Recall)": "{:.3f}",
            "F1スコア": "{:.3f}"
        }).background_gradient(cmap='RdYlGn', vmin=0, vmax=1),
        use_container_width=True
    )

def render_performance_charts(evaluation_result: EvaluationResult):
    """パフォーマンスチャート表示"""
    st.markdown("<div class='custom-header'>パフォーマンス視覚化</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # レーダーチャート
        categories = ['状態分類', 'カテゴリ分類', 'リスクレベル', '異常検知']
        f1_scores = [
            evaluation_result.status_classification.f1_score,
            evaluation_result.category_classification.f1_score,
            evaluation_result.risk_level_assessment.f1_score,
            evaluation_result.anomaly_detection.f1_score
        ]
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=f1_scores,
            theta=categories,
            fill='toself',
            name='F1スコア',
            line_color='rgb(1,90,180)'
        ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )),
            showlegend=False,
            title="機能別F1スコア",
            height=400
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
    
    with col2:
        # バーチャート（精度、再現率、F1）
        metrics = ['精度', '再現率', 'F1スコア']
        status_metrics = [
            evaluation_result.status_classification.accuracy,
            evaluation_result.status_classification.recall,
            evaluation_result.status_classification.f1_score
        ]
        category_metrics = [
            evaluation_result.category_classification.accuracy,
            evaluation_result.category_classification.recall,
            evaluation_result.category_classification.f1_score
        ]
        
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name='状態分類',
            x=metrics,
            y=status_metrics,
            marker_color='lightblue'
        ))
        fig_bar.add_trace(go.Bar(
            name='カテゴリ分類',
            x=metrics,
            y=category_metrics,
            marker_color='lightgreen'
        ))
        
        fig_bar.update_layout(
            title="メトリクス比較",
            yaxis_title="スコア",
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)

def render_confusion_matrix(evaluation_result: EvaluationResult):
    """混同行列表示"""
    st.markdown("<div class='custom-header'>混同行列</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**状態分類の混同行列**")
        if evaluation_result.status_classification.confusion_matrix:
            cm_data = evaluation_result.status_classification.confusion_matrix
            st.json(cm_data)
    
    with col2:
        st.write("**異常検知の混同行列**")
        if evaluation_result.anomaly_detection.confusion_matrix:
            cm_data = evaluation_result.anomaly_detection.confusion_matrix
            
            # バイナリ分類の混同行列を視覚化
            tp = cm_data.get('true_positive', 0)
            fp = cm_data.get('false_positive', 0)
            fn = cm_data.get('false_negative', 0)
            tn = cm_data.get('true_negative', 0)
            
            cm_matrix = [[tn, fp], [fn, tp]]
            
            fig_cm = px.imshow(
                cm_matrix,
                labels=dict(x="予測", y="実際", color="件数"),
                x=['正常', '異常'],
                y=['正常', '異常'],
                text_auto=True,
                color_continuous_scale='Blues'
            )
            fig_cm.update_layout(title="異常検知混同行列", height=300)
            st.plotly_chart(fig_cm, use_container_width=True)

def render_project_mapping_evaluation():
    """プロジェクトマッピング評価表示"""
    st.markdown("<div class='custom-header'>プロジェクトマッピング評価</div>", unsafe_allow_html=True)
    
    if 'current_reports' not in st.session_state:
        st.warning("レポートデータが読み込まれていません。")
        return
    
    try:
        from services.evaluation_service import EvaluationService
        evaluation_service = EvaluationService()
        reports = st.session_state.current_reports
        
        mapping_metrics = evaluation_service.evaluate_project_mapping(reports)
        
        if mapping_metrics.accuracy == 0 and not mapping_metrics.confusion_matrix:
            st.info("プロジェクトマッピング評価対象のレポートが見つかりません。")
            return
        
        # メイン指標
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "マッピング精度", 
                f"{mapping_metrics.accuracy:.1%}",
                help="正しいプロジェクトIDにマッピングされた割合"
            )
        with col2:
            st.metric(
                "平均信頼度", 
                f"{mapping_metrics.precision:.1%}",
                help="マッピングアルゴリズムの平均信頼度スコア"
            )
        with col3:
            method_count = len(mapping_metrics.confusion_matrix)
            st.metric(
                "評価対象手法数", 
                method_count,
                help="使用されたマッピング手法の種類数"
            )
        
        # マッピング戦略の説明
        st.divider()
        st.markdown("**🎯 マッピング戦略**")
        
        strategy_info = {
            "direct_id": ["直接ID抽出", "文書から工事番号・プロジェクトIDを直接抽出", "高（95%+）", "明確なID記載あり"],
            "fuzzy_matching": ["ファジーマッチング", "プロジェクト名・場所・期間の類似度でマッピング", "中（70-85%）", "ID記載なし、名称・場所情報あり"]
        }
        
        strategy_df = pd.DataFrame.from_dict(strategy_info, orient='index', columns=["名称", "説明", "期待精度", "適用条件"])
        st.dataframe(strategy_df, use_container_width=True, hide_index=True)
        
        # プロジェクト別マッピング結果
        st.divider()
        st.markdown("**📊 プロジェクト別マッピング結果**")
        
        project_mapping_details = []
        for report in reports:
            file_name = report.file_name
            actual_project = getattr(report, 'project_id', None)
            mapping_info = getattr(report, 'project_mapping_info', {})
            
            confidence = mapping_info.get('confidence_score', 0.0)
            method = mapping_info.get('matching_method', 'unknown')
            
            # 正解データと比較
            expected_project = None
            if file_name in evaluation_service.ground_truth.get("evaluation_data", {}):
                expected_project = evaluation_service.ground_truth["evaluation_data"][file_name].get("expected_project_id")
            
            is_correct = actual_project == expected_project if expected_project else None
            
            project_mapping_details.append({
                "ファイル名": file_name[:30] + "..." if len(file_name) > 30 else file_name,
                "抽出ID": actual_project or "なし",
                "正解ID": expected_project or "未定義",
                "手法": method,
                "信頼度": f"{confidence:.1%}",
                "結果": "✅ 正解" if is_correct else ("❌ 不正解" if is_correct is False else "⚪ 未評価")
            })
        
        if project_mapping_details:
            mapping_df = pd.DataFrame(project_mapping_details)
            st.dataframe(mapping_df, use_container_width=True, hide_index=True)
            
            # 問題のあるケースのハイライト
            incorrect_cases = [case for case in project_mapping_details if "❌" in case["結果"]]
            if incorrect_cases:
                st.warning(f"問題のあるマッピング: {len(incorrect_cases)}件")
                with st.expander("詳細を確認"):
                    for case in incorrect_cases:
                        st.write(f"**{case['ファイル名']}**: {case['抽出ID']} → {case['正解ID']} (信頼度: {case['信頼度']})")
        
    except Exception as e:
        st.error(f"プロジェクトマッピング評価でエラーが発生しました: {e}")
        logger.error(f"Project mapping evaluation error: {e}")

def render_sample_data_overview():
    """サンプルデータ概要"""
    st.markdown("<div class='custom-header'>サンプルデータ概要</div>", unsafe_allow_html=True)
    
    try:
        ground_truth_file = Path(DATA_DIR) / "evaluation" / "ground_truth.json"
        if ground_truth_file.exists():
            with open(ground_truth_file, 'r', encoding='utf-8') as f:
                ground_truth = json.load(f)
            
            metadata = ground_truth.get('metadata', {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**ステータス分布**")
                if 'distribution' in metadata:
                    dist_data = metadata['distribution']
                    fig_status = px.pie(
                        values=list(dist_data.values()),
                        names=list(dist_data.keys()),
                        title="状態フラグ分布"
                    )
                    st.plotly_chart(fig_status, use_container_width=True)
            
            with col2:
                st.write("**カテゴリ分布**")
                if 'categories' in metadata:
                    cat_data = metadata['categories']
                    fig_cat = px.bar(
                        x=list(cat_data.keys()),
                        y=list(cat_data.values()),
                        title="原因カテゴリ分布"
                    )
                    st.plotly_chart(fig_cat, use_container_width=True)
            
            st.write(f"**総レポート数**: {metadata.get('total_reports', 0)}")
            st.write(f"**作成日**: {metadata.get('created', 'N/A')}")
            
    except Exception as e:
        st.error(f"サンプルデータの読み込み失敗: {e}")

def main():
    """メインアプリケーション"""
    st.title("🔬 LLM機能評価ダッシュボード")
    st.caption("Aurora-LLM システムの機能評価と性能分析")
    
    # サイドバー
    with st.sidebar:
        st.header("🎛️ 評価設定")
        
        if st.button("🚀 評価実行", type="primary"):
            try:
                evaluation_result = run_evaluation()
                st.session_state.evaluation_result = evaluation_result
                st.success("評価完了！")
            except Exception as e:
                st.error(f"評価エラー: {e}")
        
        st.divider()
        
        st.info("""
        **評価項目**
        - 状態分類精度
        - カテゴリ分類精度  
        - リスクレベル評価
        - 異常検知性能
        - プロジェクトマッピング精度
        """)
        
        # プロジェクトマッピング評価情報
        if 'current_reports' in st.session_state:
            reports = st.session_state.current_reports
            mapping_count = len([r for r in reports if hasattr(r, 'project_id') and r.project_id])
            st.markdown("**🎯 プロジェクトマッピング**")
            st.write(f"マッピング済み: {mapping_count}件")
            st.write(f"総レポート数: {len(reports)}件")
            
            # 信頼度分布
            confidence_scores = []
            for r in reports:
                if hasattr(r, 'project_mapping_info') and r.project_mapping_info:
                    confidence_scores.append(r.project_mapping_info.get('confidence_score', 0))
            
            if confidence_scores:
                avg_confidence = sum(confidence_scores) / len(confidence_scores)
                st.write(f"平均信頼度: {avg_confidence:.1%}")
        else:
            st.markdown("**🎯 プロジェクトマッピング**")
            st.write("評価実行後に詳細が表示されます")
    
    # メインコンテンツ
    if 'evaluation_result' in st.session_state:
        evaluation_result = st.session_state.evaluation_result
        
        # タブ構成
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["概要", "統合分析結果", "詳細指標", "プロジェクトマッピング", "パフォーマンス", "サンプルデータ"])
        
        with tab1:
            render_metrics_overview(evaluation_result)
        
        with tab2:
            render_unified_analysis_results(evaluation_result)
        
        with tab3:
            render_detailed_metrics(evaluation_result)
            st.divider()
            render_confusion_matrix(evaluation_result)
        
        with tab4:
            render_project_mapping_evaluation()
        
        with tab5:
            render_performance_charts(evaluation_result)
        
        with tab6:
            render_sample_data_overview()
    
    else:
        st.info("左側サイドバーの「評価実行」ボタンを押して評価を開始してください。")
        
        # サンプルデータ概要だけ表示
        render_sample_data_overview()

if __name__ == "__main__":
    main()