"""
レポート表示UI
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.report import DocumentReport, ReportType, StatusFlag
from app.config.settings import RISK_FLAGS

def render_report_list(reports: List[DocumentReport]):
    """レポート一覧を表示"""
    st.markdown("<div class='custom-header'>レポート一覧</div>", unsafe_allow_html=True)
    
    if not reports:
        st.info("レポートがありません。")
        return
    
    # フィルター機能
    render_report_filters(reports)
    
    # ソートされたレポート一覧
    filtered_reports = apply_filters(reports)
    
    # テーブル表示
    render_report_table(filtered_reports)
    
    # 詳細表示
    if 'selected_report_index' in st.session_state:
        selected_report = filtered_reports[st.session_state.selected_report_index]
        render_report_detail(selected_report)

def render_report_filters(reports: List[DocumentReport]):
    """レポートフィルターを表示（表項目順に配置）"""
    st.markdown("<div class='custom-header'>フィルター設定</div>", unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        # プロジェクトIDフィルター（表項目順で先頭付近）
        project_ids = list({r.project_id for r in reports if r.project_id})
        project_options = ["全て"] + sorted(project_ids) + ["未抽出"]
        st.session_state.filter_project_id = st.selectbox(
            "プロジェクトID",
            project_options,
            key="project_id_filter"
        )
    
    with col2:
        # レポートタイプフィルター（ファイル名の次、レポート種別に対応）
        report_types = ["全て"] + [rt.value for rt in ReportType]
        st.session_state.filter_report_type = st.selectbox(
            "レポート種別",
            report_types,
            key="report_type_filter"
        )
    
    with col3:
        # ステータスフィルター（表項目順）
        status_labels = {
            'stopped': '停止',
            'major_delay': '重大な遅延',
            'minor_delay': '軽微な遅延',
            'normal': '順調'
        }
        status_options = ["全て"] + list(status_labels.values())
        selected_status_jp = st.selectbox(
            "ステータス",
            status_options,
            key="status_filter"
        )
        # 日本語から英語に変換
        if selected_status_jp == "全て":
            st.session_state.filter_status = "全て"
        else:
            status_value_map = {v: k for k, v in status_labels.items()}
            st.session_state.filter_status = status_value_map.get(selected_status_jp, "全て")
    
    with col4:
        # リスクレベルフィルター（表項目順）
        risk_levels = ["全て", "低", "中", "高"]
        st.session_state.filter_risk_level = st.selectbox(
            "リスクレベル",
            risk_levels,
            key="risk_level_filter"
        )
    
    with col5:
        # 緊急度フィルター（表項目順）
        st.session_state.filter_urgency = st.slider(
            "最小緊急度",
            min_value=1,
            max_value=10,
            value=1,
            key="urgency_filter"
        )
    
    with col6:
        # カテゴリーラベルフィルター（問題区分）
        category_labels = {
            'technical': '技術課題',
            'administrative': '事務課題',
            'stakeholder': 'ステークホルダー',
            'financial': '財務',
            'environmental': '環境課題',
            'legal': '法的問題',
            'requires_review': '要確認',
            'other': 'その他'
        }
        category_options = ["全て"] + list(category_labels.values())
        selected_category_jp = st.selectbox(
            "問題区分",
            category_options,
            key="category_filter"
        )
        # 日本語から英語に変換
        if selected_category_jp == "全て":
            st.session_state.filter_category = "全て"
        else:
            category_value_map = {v: k for k, v in category_labels.items()}
            st.session_state.filter_category = category_value_map.get(selected_category_jp, "全て")

def apply_filters(reports: List[DocumentReport]) -> List[DocumentReport]:
    """フィルターを適用"""
    filtered_reports = reports.copy()
    
    # プロジェクトIDフィルター
    if hasattr(st.session_state, 'filter_project_id') and st.session_state.filter_project_id != "全て":
        if st.session_state.filter_project_id == "未抽出":
            filtered_reports = [
                r for r in filtered_reports
                if not r.project_id
            ]
        else:
            filtered_reports = [
                r for r in filtered_reports
                if r.project_id == st.session_state.filter_project_id
            ]
    
    # レポートタイプフィルター
    if hasattr(st.session_state, 'filter_report_type') and st.session_state.filter_report_type != "全て":
        filtered_reports = [
            r for r in filtered_reports
            if r.report_type.value == st.session_state.filter_report_type
        ]
    
    # リスクレベルフィルター
    if hasattr(st.session_state, 'filter_risk_level') and st.session_state.filter_risk_level != "全て":
        filtered_reports = [
            r for r in filtered_reports
            if r.risk_level and r.risk_level.value == st.session_state.filter_risk_level
        ]
    
    # ステータスフィルター
    if hasattr(st.session_state, 'filter_status') and st.session_state.filter_status != "全て":
        filter_status = StatusFlag(st.session_state.filter_status)
        filtered_reports = [
            r for r in filtered_reports
            if r.status_flag == filter_status
        ]
    
    # カテゴリーフィルター削除: 15カテゴリ遅延理由体系に統一
    
    # 緊急度フィルター
    if hasattr(st.session_state, 'filter_urgency'):
        filtered_reports = [
            r for r in filtered_reports
            if getattr(r, 'urgency_score', 0) >= st.session_state.filter_urgency
        ]
    
    # 緊急度でソート
    filtered_reports.sort(
        key=lambda x: getattr(x, 'urgency_score', 0),
        reverse=True
    )
    
    return filtered_reports

def render_report_table(reports: List[DocumentReport]):
    """レポートテーブルを表示"""
    if not reports:
        st.info("フィルター条件に合うレポートがありません。")
        return
    
    # テーブルデータ準備
    table_data = []
    for i, report in enumerate(reports):
        # フラグアイコン
        flag_icons = []
        for flag in report.flags:
            flag_info = RISK_FLAGS.get(flag.value, {})
            flag_icons.append(flag_info.get('name', flag.value))
        flag_display = " ".join(flag_icons) if flag_icons else "-"
        
        # 分析結果
        if report.analysis_result:
            risk_level = report.risk_level.value if report.risk_level else "-"
            urgency_score = getattr(report, 'urgency_score', 0)
            summary = report.analysis_result.summary[:50] + "..." if len(report.analysis_result.summary) > 50 else report.analysis_result.summary
        else:
            risk_level = "-"
            urgency_score = 0
            summary = "分析なし"
        
        # 新フラグシステムの日本語化
        status_labels = {
            'stopped': '停止',
            'major_delay': '重大な遅延',
            'minor_delay': '軽微な遅延',
            'normal': '順調'
        }
        
        risk_labels = {
            'high': '高',
            'medium': '中', 
            'low': '低'
        }
        
        # ステータスとリスクレベルの日本語表示
        status_display = status_labels.get(report.status_flag.value, report.status_flag.value) if report.status_flag else "-"
        risk_display = risk_labels.get(report.risk_level.value, report.risk_level.value) if report.risk_level else risk_level
        
        table_data.append({
            "選択": False,
            "ファイル名": report.file_name,
            "プロジェクトID": report.project_id or "未抽出",
            "レポート種別": report.report_type.value,
            "ステータス": status_display,
            "リスクレベル": risk_display,
            "緊急度": urgency_score,
            "要約": summary,
            "作成日時": report.created_at.strftime("%Y-%m-%d %H:%M")
        })
    
    # データフレーム作成
    df = pd.DataFrame(table_data)
    
    # 選択可能なテーブル表示
    edited_df = st.data_editor(
        df,
        column_config={
            "選択": st.column_config.CheckboxColumn(
                "選択",
                help="詳細を表示するレポートを選択",
                default=False,
            )
        },
        disabled=["ファイル名", "レポート種別", "フラグ", "リスクレベル", "緊急度", "要約", "作成日時"],
        hide_index=True,
        use_container_width=True
    )
    
    # 選択されたレポートのインデックスを取得
    selected_indices = edited_df[edited_df["選択"] == True].index.tolist()
    if selected_indices:
        st.session_state.selected_report_index = selected_indices[0]

def render_report_detail(report: DocumentReport):
    """レポート詳細を表示"""
    st.divider()
    st.markdown(f"<div class='custom-header'>{report.file_name} - 詳細</div>", unsafe_allow_html=True)
    
    # 基本情報
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**基本情報**")
        st.write(f"**ファイル名:** {report.file_name}")
        st.write(f"**レポート種別:** {report.report_type.value}")
        st.write(f"**作成日時:** {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"**ファイルパス:** {report.file_path}")
    
    with col2:
        if report.analysis_result:
            st.write("**分析結果**")
            st.write(f"**リスクレベル:** {report.risk_level.value if report.risk_level else '不明'}")
            st.write(f"**緊急度スコア:** {getattr(report, 'urgency_score', 0)}/10")
            
            # フラグ表示
            if report.flags:
                flag_displays = []
                for flag in report.flags:
                    flag_info = RISK_FLAGS.get(flag.value, {})
                    flag_displays.append(flag_info.get('name', flag.value))
                st.write(f"**フラグ:** {' '.join(flag_displays)}")
    
    # タブ表示
    tab1, tab2, tab3, tab4 = st.tabs(["内容", "分析結果", "異常検知", "プロジェクト情報"])
    
    with tab1:
        render_content_tab(report)
    
    with tab2:
        render_analysis_tab(report)
    
    with tab3:
        render_anomaly_tab(report)
    
    with tab4:
        render_project_info_tab(report)

def render_content_tab(report: DocumentReport):
    """内容タブを表示"""
    st.subheader("文書内容")
    
    # 内容表示（スクロール可能）
    with st.container():
        st.text_area(
            "文書内容",
            value=report.content,
            height=400,
            disabled=True,
            label_visibility="collapsed"
        )

def render_analysis_tab(report: DocumentReport):
    """分析結果タブを表示"""
    if not report.analysis_result:
        st.info("分析結果がありません。")
        return
    
    analysis = report.analysis_result
    
    st.subheader("LLM分析結果")
    
    # 要約
    st.write("**要約**")
    st.info(analysis.summary)
    
    # 重要ポイント
    if analysis.key_points:
        st.write("**重要ポイント**")
        for point in analysis.key_points:
            st.write(f"• {point}")
    
    # 問題・課題
    if analysis.issues:
        st.write("**検出された問題・課題**")
        for issue in analysis.issues:
            st.warning(f"⚠️ {issue}")
    
    # プロジェクト情報
    # プロジェクト情報（reportから直接取得）
    if report.project_id:
        st.write("**プロジェクト情報**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**プロジェクトID:** {report.project_id}")
        with col2:
            st.write("**場所:** 不明")  # 現在DocumentReportに保存されていない
        with col3:
            st.write("**担当者:** 不明")  # 現在DocumentReportに保存されていない

def render_anomaly_tab(report: DocumentReport):
    """異常検知タブを表示"""
    if not report.anomaly_detection:
        st.info("異常検知結果がありません。")
        return
    
    anomaly = report.anomaly_detection
    
    st.subheader("異常検知結果")
    
    # 異常判定
    if anomaly.is_anomaly:
        st.error(f"🚨 異常が検出されました（信頼度: {anomaly.confidence:.2f}）")
        st.write("**異常内容:**")
        st.write(anomaly.anomaly_description)
    else:
        st.success("✅ 既知のパターンです")
    
    # 推奨対応
    if anomaly.suggested_action:
        st.write("**推奨対応:**")
        st.info(anomaly.suggested_action)
    
    # 人間確認の必要性
    if anomaly.requires_human_review:
        st.warning("👤 人間による確認が推奨されます")
    
    # 類似ケース
    if anomaly.similar_cases:
        st.write("**類似ケース:**")
        for case in anomaly.similar_cases:
            st.write(f"• {case}")

def render_project_info_tab(report: DocumentReport):
    """プロジェクト情報タブを表示"""
    # project_infoはAnalysisResultから削除されたため、直接DocumentReportから情報を取得
    
    st.subheader("プロジェクト詳細情報")
    
    # 情報表示
    info_cols = st.columns(2)
    
    with info_cols[0]:
        st.write("**基本情報**")
        st.write(f"**プロジェクトID:** {report.project_id or '不明'}")
        st.write(f"**プロジェクト名:** 不明")  # DocumentReportに保存されていない
        st.write(f"**場所:** 不明")  # DocumentReportに保存されていない
    
    with info_cols[1]:
        st.write("**担当者情報**")
        st.write(f"**責任者:** 不明")  # DocumentReportに保存されていない
        st.write(f"**現場代理人:** 不明")  # DocumentReportに保存されていない
        st.write(f"**連絡先:** 不明")  # DocumentReportに保存されていない
    
    # プロジェクトマッピング情報を表示
    if hasattr(report, 'project_mapping_info') and report.project_mapping_info:
        st.write("**マッピング情報**")
        mapping_info = report.project_mapping_info
        st.write(f"**信頼度スコア:** {mapping_info.get('confidence_score', 'N/A')}")
        st.write(f"**マッピング手法:** {mapping_info.get('matching_method', 'N/A')}")
        
        if mapping_info.get('extracted_info'):
            st.write("**抽出された情報:**")
            for key, value in mapping_info['extracted_info'].items():
                st.write(f"• {key}: {value}")