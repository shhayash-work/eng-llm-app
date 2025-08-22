"""
プロジェクト一覧UI
フィルター・表形式・進捗ステップ表示機能付きプロジェクト一覧ページ
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime

from app.services.project_aggregator import ProjectSummary
from app.models.report import DocumentReport

def render_project_list(project_summaries: List[ProjectSummary], reports: List[DocumentReport] = None):
    """プロジェクト一覧ページを表示"""
    
    # プロジェクト詳細表示処理
    if st.session_state.get('show_project_details', False):
        selected_project_id = st.session_state.get('selected_project_id')
        if selected_project_id:
            _render_project_details(project_summaries, selected_project_id, reports)
            if st.button("← プロジェクト一覧に戻る", key="back_to_project_list"):
                st.session_state.show_project_details = False
                st.session_state.selected_project_id = None
                st.rerun()
            return
    
    st.markdown("<div class='custom-header'>プロジェクト一覧</div>", unsafe_allow_html=True)
    
    if not project_summaries:
        st.warning("表示可能なプロジェクトがありません。")
        return
    
    # フィルター表示
    render_project_filters(project_summaries)
    
    # フィルター適用
    filtered_projects = apply_project_filters(project_summaries)
    
    # 結果表示
    st.markdown(f"**表示件数:** {len(filtered_projects)} / {len(project_summaries)} プロジェクト")
    
    # 詳細表示
    render_project_table(filtered_projects)

def render_project_filters(projects: List[ProjectSummary]):
    """プロジェクトフィルターを表示（表項目順に配置）"""
    st.markdown("<div class='custom-header'>フィルター設定</div>", unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        # 場所フィルター（表の順番に合わせて先頭）
        locations = list({p.location for p in projects if p.location})
        location_options = ["全て"] + sorted(locations)
        st.session_state.filter_project_location = st.selectbox(
            "場所",
            location_options,
            key="project_location_filter"
        )
    
    with col2:
        # 現在フェーズフィルター
        phases = list({p.current_phase for p in projects if p.current_phase})
        phase_options = ["全て"] + sorted(phases)
        st.session_state.filter_project_phase = st.selectbox(
            "現在フェーズ",
            phase_options,
            key="project_phase_filter"
        )
    
    with col3:
        # ステータスフィルター
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
            key="project_status_filter"
        )
        # 日本語から英語に変換
        if selected_status_jp == "全て":
            st.session_state.filter_project_status = "全て"
        else:
            status_value_map = {v: k for k, v in status_labels.items()}
            st.session_state.filter_project_status = status_value_map.get(selected_status_jp, "全て")
    
    with col4:
        # リスクレベルフィルター
        risk_levels = ["全て", "低", "中", "高"]
        st.session_state.filter_project_risk = st.selectbox(
            "リスクレベル",
            risk_levels,
            key="project_risk_filter"
        )
    
    with col5:
        # 担当者フィルター
        responsible_persons = list({p.responsible_person for p in projects if p.responsible_person})
        person_options = ["全て"] + sorted(responsible_persons)
        st.session_state.filter_project_person = st.selectbox(
            "担当者",
            person_options,
            key="project_person_filter"
        )
    
    with col6:
        # 完了予定フィルター（期間指定）
        st.session_state.filter_project_completion = st.selectbox(
            "完了予定",
            ["全て", "今月", "来月", "3ヶ月以内", "未定"],
            key="project_completion_filter"
        )

def apply_project_filters(projects: List[ProjectSummary]) -> List[ProjectSummary]:
    """フィルターを適用"""
    filtered_projects = projects.copy()
    
    # ステータスフィルター
    if hasattr(st.session_state, 'filter_project_status') and st.session_state.filter_project_status != "全て":
        from app.models.report import StatusFlag
        filter_status = StatusFlag(st.session_state.filter_project_status)
        filtered_projects = [
            p for p in filtered_projects
            if p.current_status == filter_status
        ]
    
    # リスクレベルフィルター
    if hasattr(st.session_state, 'filter_project_risk') and st.session_state.filter_project_risk != "全て":
        risk_map = {"低": "low", "中": "medium", "高": "high"}
        filter_risk = risk_map.get(st.session_state.filter_project_risk)
        if filter_risk:
            filtered_projects = [
                p for p in filtered_projects
                if p.risk_level and p.risk_level.value == filter_risk
            ]
    
    # フェーズフィルター
    if hasattr(st.session_state, 'filter_project_phase') and st.session_state.filter_project_phase != "全て":
        filtered_projects = [
            p for p in filtered_projects
            if p.current_phase == st.session_state.filter_project_phase
        ]
    
    # 場所フィルター
    if hasattr(st.session_state, 'filter_project_location') and st.session_state.filter_project_location != "全て":
        filtered_projects = [
            p for p in filtered_projects
            if p.location == st.session_state.filter_project_location
        ]
    
    # 担当者フィルター
    if hasattr(st.session_state, 'filter_project_person') and st.session_state.filter_project_person != "全て":
        filtered_projects = [
            p for p in filtered_projects
            if p.responsible_person == st.session_state.filter_project_person
        ]
    
    # 完了予定フィルター
    if hasattr(st.session_state, 'filter_project_completion') and st.session_state.filter_project_completion != "全て":
        from datetime import datetime, timedelta
        now = datetime.now()
        
        if st.session_state.filter_project_completion == "今月":
            month_end = now.replace(day=1) + timedelta(days=32)
            month_end = month_end.replace(day=1) - timedelta(days=1)
            filtered_projects = [p for p in filtered_projects if p.estimated_completion and now <= p.estimated_completion <= month_end]
        elif st.session_state.filter_project_completion == "来月":
            next_month = now.replace(day=1) + timedelta(days=32)
            next_month_end = next_month.replace(day=1) + timedelta(days=32)
            next_month_end = next_month_end.replace(day=1) - timedelta(days=1)
            filtered_projects = [p for p in filtered_projects if p.estimated_completion and next_month <= p.estimated_completion <= next_month_end]
        elif st.session_state.filter_project_completion == "3ヶ月以内":
            three_months = now + timedelta(days=90)
            filtered_projects = [p for p in filtered_projects if p.estimated_completion and now <= p.estimated_completion <= three_months]
        elif st.session_state.filter_project_completion == "未定":
            filtered_projects = [p for p in filtered_projects if not p.estimated_completion]
    
    # ステータス順でソート
    status_priority = {
        'stopped': 1,
        'major_delay': 2,
        'minor_delay': 3,
        'normal': 4
    }
    
    filtered_projects.sort(
        key=lambda x: (
            status_priority.get(x.current_status.value if x.current_status else 'normal', 5),
            x.project_name
        )
    )
    
    return filtered_projects

def render_project_table(projects: List[ProjectSummary]):
    """プロジェクト表を表示（カテゴリ別タブ）"""
    if not projects:
        st.info("フィルター条件に合致するプロジェクトがありません。")
        return
    
    # ステータス・リスクレベル日本語化
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
    
    # タブで基本情報と工事詳細を分離
    tab1, tab2 = st.tabs(["基本情報", "工事詳細状況"])
    
    with tab1:
        # 基本情報テーブル
        basic_data = []
        for project in projects:
            basic_data.append({
                "プロジェクトID": project.project_id,
                "プロジェクト名": project.project_name,
                "場所": project.location,
                "現在フェーズ": project.current_phase,
                "ステータス": status_labels.get(project.current_status.value, project.current_status.value) if project.current_status else '不明',
                "リスクレベル": risk_labels.get(project.risk_level.value, project.risk_level.value) if project.risk_level else '不明',
                "担当者": project.responsible_person,
                "最終報告": f"{project.days_since_last_report}日前" if project.days_since_last_report else "未報告",
                "完了予定": project.estimated_completion.strftime('%Y-%m-%d') if project.estimated_completion else '未定'
            })
        
        basic_df = pd.DataFrame(basic_data)
        
        # プロジェクト選択機能付きテーブル表示
        selected_indices = st.dataframe(
            basic_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                'ステータス': st.column_config.TextColumn(
                    'ステータス',
                    width='medium'
                ),
                'リスクレベル': st.column_config.TextColumn(
                    'リスクレベル',
                    width='small'
                ),
                '完了予定': st.column_config.TextColumn(
                    '完了予定',
                    width='medium'
                )
            }
        )
        
        # 選択されたプロジェクトがある場合の詳細表示ボタン
        if selected_indices.selection.rows:
            selected_row = selected_indices.selection.rows[0]
            selected_project = projects[selected_row]
            
            if st.button(f"📋 {selected_project.project_name} の詳細とレポート一覧を表示", key="view_project_details", use_container_width=True):
                st.session_state.selected_project_id = selected_project.project_id
                st.session_state.show_project_details = True
                st.rerun()
    
    with tab2:
        # 工事詳細状況テーブル
        construction_data = []
        for project in projects:
            # 建設工程ステップの進捗状況を取得
            phase_status = _get_construction_phases_status(project)
            
            construction_data.append({
                "プロジェクトID": project.project_id,
                "プロジェクト名": project.project_name,
                "置局発注": phase_status.get("置局発注", "不明"),
                "基本同意": phase_status.get("基本同意", "不明"),
                "基本図承認": phase_status.get("基本図承認", "不明"),
                "内諾": phase_status.get("内諾", "不明"),
                "附帯着工": phase_status.get("附帯着工", "不明"),
                "電波発射": phase_status.get("電波発射", "不明"),
                "工事検収": phase_status.get("工事検収", "不明")
            })
        
        construction_df = pd.DataFrame(construction_data)
        
        st.dataframe(
            construction_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "プロジェクトID": st.column_config.TextColumn(
                    "プロジェクトID",
                    width='small'
                ),
                "プロジェクト名": st.column_config.TextColumn(
                    "プロジェクト名", 
                    width='medium'
                ),
                **{
                    col: st.column_config.TextColumn(
                        col,
                        width='small'
                    ) for col in construction_df.columns if col not in ["プロジェクトID", "プロジェクト名"]
                }
            }
        )

def _get_construction_phases_status(project: ProjectSummary) -> Dict[str, str]:
    """建設工程7ステップの進捗状況を取得"""
    # 正しい7ステップ建設工程
    seven_steps = [
        "置局発注",
        "基本同意", 
        "基本図承認",
        "内諾",
        "附帯着工",
        "電波発射",
        "工事検収"
    ]
    
    phase_status = {}
    
    # 現在フェーズから7ステップの進捗状況を推定
    current_phase = project.current_phase
    current_phase_index = -1
    
    # 現在のフェーズが7ステップのどの段階かを判定
    for i, phase in enumerate(seven_steps):
        if phase == current_phase:
            current_phase_index = i
            break
    
    # プロジェクトのステータスを確認（停止状態のチェック）
    is_stopped = (
        (project.current_status and project.current_status.value == 'stopped') or
        ('未定' in str(project.estimated_completion))
    )
    
    # 7ステップの状態を設定
    for i, phase in enumerate(seven_steps):
        if current_phase_index == -1:
            # 現在フェーズが不明な場合はすべて未着手
            phase_status[phase] = "未着手"
        elif i < current_phase_index:
            # 現在フェーズより前は完了
            phase_status[phase] = "完了"
        elif i == current_phase_index:
            # 現在フェーズ
            if is_stopped:
                phase_status[phase] = "停止中"
            else:
                phase_status[phase] = "進行中"
        else:
            # 現在フェーズより後は未着手
            phase_status[phase] = "未着手"
    
    return phase_status

def _render_project_details(projects: List[ProjectSummary], project_id: str, reports: List[DocumentReport] = None):
    """プロジェクト詳細とレポート一覧を表示"""
    # 該当プロジェクトを検索
    target_project = None
    for project in projects:
        if project.project_id == project_id:
            target_project = project
            break
    
    if not target_project:
        st.error(f"プロジェクト {project_id} が見つかりません。")
        return
    
    # ヘッダー表示
    st.markdown(f"<div class='custom-header'>{target_project.project_name} - プロジェクト詳細</div>", unsafe_allow_html=True)
    
    # プロジェクト基本情報
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**プロジェクトID:** {target_project.project_id}")
        st.markdown(f"**場所:** {target_project.location}")
        st.markdown(f"**現在フェーズ:** {target_project.current_phase}")
    with col2:
        status_labels = {
            'stopped': '停止',
            'major_delay': '重大な遅延',
            'minor_delay': '軽微な遅延', 
            'normal': '順調'
        }
        status_text = status_labels.get(target_project.current_status.value, target_project.current_status.value) if target_project.current_status else '不明'
        st.markdown(f"**ステータス:** {status_text}")
        risk_text = target_project.risk_level.value if target_project.risk_level else '不明'
        st.markdown(f"**リスクレベル:** {risk_text}")
    with col3:
        st.markdown(f"**担当者:** {target_project.responsible_person}")
        st.markdown(f"**最終報告:** {target_project.days_since_last_report}日前")
        completion_text = target_project.estimated_completion.strftime('%Y-%m-%d') if target_project.estimated_completion else '未定'
        st.markdown(f"**完了予定:** {completion_text}")
    
    st.divider()
    
    # レポート一覧セクション
    st.markdown("<div class='custom-header' style='font-size: 20px;'>このプロジェクトのレポート一覧</div>", unsafe_allow_html=True)
    
    if reports:
        # プロジェクトに紐づくレポートをフィルタリング
        project_reports = [r for r in reports if r.project_id == project_id]
        
        if project_reports:
            st.markdown(f"**該当レポート数:** {len(project_reports)}件")
            
            # レポート一覧をテーブル形式で表示
            report_data = []
            for report in sorted(project_reports, key=lambda x: x.created_at, reverse=True):
                # ステータス表示
                status_text = "不明"
                if report.status_flag:
                    status_labels = {
                        'stopped': '停止',
                        'major_delay': '重大な遅延',
                        'minor_delay': '軽微な遅延', 
                        'normal': '順調'
                    }
                    status_text = status_labels.get(report.status_flag.value, report.status_flag.value)
                
                # リスクレベル表示
                risk_text = "不明"
                if report.risk_level:
                    risk_text = report.risk_level.value
                
                # 要約取得
                summary = "要約なし"
                if report.analysis_result and report.analysis_result.summary:
                    summary = report.analysis_result.summary[:100] + "..." if len(report.analysis_result.summary) > 100 else report.analysis_result.summary
                
                report_data.append({
                    "ファイル名": report.file_name,
                    "レポート種別": report.report_type.value,
                    "ステータス": status_text,
                    "リスクレベル": risk_text,
                    "要約": summary,
                    "作成日時": report.created_at.strftime("%Y-%m-%d %H:%M")
                })
            
            report_df = pd.DataFrame(report_data)
            st.dataframe(report_df, use_container_width=True, hide_index=True)
            
            # レポート詳細表示
            st.markdown("---")
            selected_report_idx = st.selectbox(
                "詳細を表示するレポートを選択:",
                range(len(project_reports)),
                format_func=lambda x: f"{project_reports[x].file_name} ({project_reports[x].created_at.strftime('%Y-%m-%d')})"
            )
            
            if selected_report_idx is not None:
                selected_report = project_reports[selected_report_idx]
                st.markdown(f"**📄 {selected_report.file_name} の詳細**")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**レポート種別:** {selected_report.report_type.value}")
                    st.markdown(f"**作成日時:** {selected_report.created_at.strftime('%Y-%m-%d %H:%M')}")
                    status_text = status_labels.get(selected_report.status_flag.value, "不明") if selected_report.status_flag else "不明"
                    st.markdown(f"**ステータス:** {status_text}")
                
                with col2:
                    risk_text = selected_report.risk_level.value if selected_report.risk_level else "不明"
                    st.markdown(f"**リスクレベル:** {risk_text}")
                    urgency = getattr(selected_report, 'urgency_score', 0)
                    st.markdown(f"**緊急度スコア:** {urgency}")
                
                if selected_report.analysis_result:
                    st.markdown("**📝 分析結果:**")
                    st.markdown(f"**要約:** {selected_report.analysis_result.summary}")
                    if selected_report.analysis_result.issues:
                        st.markdown(f"**問題点:** {', '.join(selected_report.analysis_result.issues)}")
                    if selected_report.analysis_result.key_points:
                        st.markdown(f"**重要ポイント:** {', '.join(selected_report.analysis_result.key_points)}")
        else:
            st.info(f"プロジェクト {project_id} に紐づくレポートが見つかりません。")
    else:
        st.warning("レポートデータが提供されていません。")
    
    # 工事進捗状況
    st.markdown("<div class='custom-header' style='font-size: 20px;'>工事進捗状況</div>", unsafe_allow_html=True)
    
    phase_status = _get_construction_phases_status(target_project)
    
    # 進捗状況を表形式で表示
    progress_data = []
    for phase, status in phase_status.items():
        progress_data.append({
            "工程": phase,
            "状況": status
        })
    
    progress_df = pd.DataFrame(progress_data)
    st.dataframe(progress_df, use_container_width=True, hide_index=True)