"""
プロジェクト中心のダッシュボードUI
建設プロジェクト管理に特化したダッシュボード表示
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.services.project_aggregator import ProjectSummary
from app.models.report import DocumentReport

def render_project_dashboard(projects: List[ProjectSummary], reports: List = None):
    """プロジェクト中心のメインダッシュボード"""
    
    # 最新レポート表示処理
    if st.session_state.get('show_project_report', False):
        selected_project_id = st.session_state.get('selected_project_for_report')
        if selected_project_id:
            _render_latest_project_report(projects, selected_project_id)
            if st.button("← ダッシュボードに戻る", key="back_to_dashboard"):
                st.session_state.show_project_report = False
                st.session_state.selected_project_for_report = None
                st.rerun()
            return
    
    if not projects:
        st.warning("表示可能なプロジェクトがありません。")
        return
    
    # プロジェクト管理ダッシュボードでは完了プロジェクトを除外
    active_projects = [p for p in projects if p.current_phase != "完了"]
    
    if not active_projects:
        st.warning("進行中のプロジェクトがありません。")
        return
    
    # ダッシュボードメトリクス計算
    from app.services.project_aggregator import ProjectAggregator
    aggregator = ProjectAggregator()
    metrics = aggregator.get_dashboard_metrics(active_projects)
    status_groups = aggregator.get_projects_by_status(active_projects)
    
    # メトリクス表示
    _render_project_metrics(metrics)
    
    # 要緊急対応案件アラート表示
    st.markdown("<div class='custom-header'>要緊急対応案件</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>緊急停止・長期未報告・高リスク案件など、現場確認と迅速な対応が必要な案件を表示</p>", unsafe_allow_html=True)
    _render_urgent_response_alerts(active_projects, reports)
    
    # 案件状況一覧
    st.markdown("<div class='custom-header'>案件状況一覧</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>ステータス別（最新報告・停止・重大な遅延・軽微な遅延・順調）に案件を分類し、緊急度順で表示</p>", unsafe_allow_html=True)
    
    # 重要度順タブ表示
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["最新報告", "停止", "重大な遅延", "軽微な遅延", "順調"])
    
    with tab1:
        # 最新報告案件（最新報告日順で上位5件）
        latest_projects = sorted(active_projects, key=lambda p: p.latest_report_date or datetime.min, reverse=True)[:5]
        _render_project_list_section(latest_projects, "最新報告", show_more_link=len(active_projects) > 5, reports=reports)
    
    with tab2:
        # 停止案件（緊急度上位5件）
        stopped_projects = [p for p in active_projects if p.current_status and p.current_status.value == 'stopped']
        stopped_projects = sorted(stopped_projects, key=lambda p: _get_urgency_score(p), reverse=True)[:5]
        _render_project_list_section(stopped_projects, "停止", show_more_link=len([p for p in active_projects if p.current_status and p.current_status.value == 'stopped']) > 5, reports=reports)
    
    with tab3:
        # 重大な遅延案件（緊急度上位5件）
        major_delay_projects = [p for p in active_projects if p.current_status and p.current_status.value == 'major_delay']
        major_delay_projects = sorted(major_delay_projects, key=lambda p: _get_urgency_score(p), reverse=True)[:5]
        _render_project_list_section(major_delay_projects, "重大な遅延", show_more_link=len([p for p in active_projects if p.current_status and p.current_status.value == 'major_delay']) > 5, reports=reports)
    
    with tab4:
        # 軽微な遅延案件（緊急度上位5件）
        minor_delay_projects = [p for p in active_projects if p.current_status and p.current_status.value == 'minor_delay']
        minor_delay_projects = sorted(minor_delay_projects, key=lambda p: _get_urgency_score(p), reverse=True)[:5]
        _render_project_list_section(minor_delay_projects, "軽微な遅延", show_more_link=len([p for p in active_projects if p.current_status and p.current_status.value == 'minor_delay']) > 5, reports=reports)
    
    with tab5:
        # 順調案件（緊急度上位5件）
        normal_projects = [p for p in active_projects if p.current_status and p.current_status.value == 'normal']
        normal_projects = sorted(normal_projects, key=lambda p: _get_urgency_score(p), reverse=True)[:5]
        _render_project_list_section(normal_projects, "順調", show_more_link=len([p for p in active_projects if p.current_status and p.current_status.value == 'normal']) > 5, reports=reports)
    
    # 案件分析チャート（個別のタイトルで表示）
    col1, col2 = st.columns(2)
    
    with col1:
        _render_category_distribution_chart(active_projects)
    
    with col2:
        _render_risk_distribution_chart(active_projects)
    
    # 完了予定タイムライン（下部に移動）
    st.markdown("<div class='custom-header'>案件完了予定タイムライン</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>月別の案件完了予定と進捗状況（完了済み・工事中・未着手）の推移を表示</p>", unsafe_allow_html=True)
    _render_timeline_chart(active_projects)

def _render_project_metrics(metrics: Dict[str, Any]):
    """プロジェクトメトリクス表示（現在の状況ベース）"""
    
    # キャッシュクリア（強制更新）
    st.cache_data.clear()
    
    # CSSスタイルを直接定義（キャッシュ回避）
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
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        color = "#FF6B35" if metrics['stopped_count'] > 0 else "#28a745"
        st.markdown(f"""
        <div class='metric-card-updated'>
            <h3>停止案件数</h3>
            <h2 style='color: {color};'>{metrics['stopped_count']}<sub style='font-size: 0.8em; color: #666;'>/{metrics['total_projects']}</sub></h2>
            <p>{metrics['stopped_percentage']:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        color = "#FF6B35" if metrics['major_delay_count'] > 0 else "#28a745"
        st.markdown(f"""
        <div class='metric-card-updated'>
            <h3>重大な遅延案件数</h3>
            <h2 style='color: {color};'>{metrics['major_delay_count']}<sub style='font-size: 0.8em; color: #666;'>/{metrics['total_projects']}</sub></h2>
            <p>{metrics['major_delay_percentage']:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        color = "#FFA500" if metrics['minor_delay_count'] > 0 else "#28a745"
        st.markdown(f"""
        <div class='metric-card-updated'>
            <h3>軽微な遅延案件数</h3>
            <h2 style='color: {color};'>{metrics['minor_delay_count']}<sub style='font-size: 0.8em; color: #666;'>/{metrics['total_projects']}</sub></h2>
            <p>{metrics['minor_delay_percentage']:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class='metric-card-updated'>
            <h3>順調案件数</h3>
            <h2 style='color: #28a745;'>{metrics['normal_count']}<sub style='font-size: 0.8em; color: #666;'>/{metrics['total_projects']}</sub></h2>
            <p>{metrics['normal_percentage']:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)

def _render_project_list_section(projects: List[ProjectSummary], section_title: str, show_more_link: bool = False, reports: List = None):
    """統一されたプロジェクト一覧表示"""
    
    if not projects:
        st.info(f"{section_title}に該当するプロジェクトはありません。")
        return
    
    for project in projects:
        _render_project_card(project, section_title, reports)
    
    # プロジェクト一覧ページへのリンク
    if show_more_link:
        if st.button("案件一覧ページで全件確認", key=f"goto_list_{section_title}", use_container_width=True):
            # 案件一覧ページに遷移
            st.session_state.current_page = "案件一覧"
            st.rerun()

def _render_project_card(project: ProjectSummary, section_name: str = "default", reports: List = None):
    """プロジェクトカード表示（ドリルダウン対応）"""
    
    status_color = _get_status_color(project.current_status)
    
    # ステータスラベルの日本語変換
    status_labels = {
        'stopped': '停止',
        'major_delay': '重大な遅延',
        'minor_delay': '軽微な遅延', 
        'normal': '順調'
    }
    status_text = status_labels.get(project.current_status.value, project.current_status.value) if project.current_status else '不明'
    
    # リスクレベル表示用（ステータスと重複しないように簡略化）
    risk_text = project.risk_level.value if project.risk_level else '不明'
    risk_colors = {
        '高': '#dc3545',
        '中': '#ffc107', 
        '低': '#28a745',
        '不明': '#6c757d'
    }
    risk_color = risk_colors.get(risk_text, '#6c757d')
    
    # 展開状態の管理
    expand_key = f"expand_{project.project_id}_{section_name}"
    is_expanded = st.session_state.get(expand_key, False)
    
    # プロジェクトカード表示（透明ボタン重ね合わせ版）
    background_color = '#f8f9fa' if is_expanded else 'white'
    border_color = '#007bff' if is_expanded else '#ddd'
    
    # カード内埋め込み詳細ボタン付きデザイン
    expand_icon = "▲" if is_expanded else "▼"
    unique_btn_id = f"detail_btn_{project.project_id}_{section_name}"
    
    # シンプルなカードデザイン（現在の状況 + 将来リスク）
    st.markdown(f"""
    <div style='border: 2px solid {border_color}; border-radius: 8px; padding: 16px; margin-bottom: 8px; background-color: {background_color}; transition: all 0.3s ease;'>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
            <h4 style='margin: 0; color: #2C3E50; font-size: 18px;'>{project.project_name}</h4>
            <div style='display: flex; gap: 8px;'>
                <span style='background-color: {status_color}; color: white; padding: 6px 12px; border-radius: 4px; font-size: 14px; font-weight: bold;'>
                    {status_text}
                </span>
                <span style='background-color: {risk_color}; color: white; padding: 6px 12px; border-radius: 4px; font-size: 14px; font-weight: bold;'>
                    リスク{risk_text}
                </span>
            </div>
        </div>
        <p style='margin: 4px 0; color: #7F8C8D; font-size: 16px;'><strong>場所:</strong> {project.location}</p>
        <p style='margin: 4px 0; color: #7F8C8D; font-size: 16px;'><strong>フェーズ:</strong> {project.current_phase}</p>
        <p style='margin: 4px 0; color: #7F8C8D; font-size: 16px;'><strong>担当者:</strong> {project.responsible_person}</p>
        <p style='margin: 4px 0; color: #7F8C8D; font-size: 16px;'><strong>最終報告:</strong> {project.days_since_last_report}日前</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 最新レポート表示をexpanderで実装（左端配置、スクロール問題解決）
    with st.expander(f"📄 {project.project_name} の最新レポート詳細", expanded=is_expanded):
        _render_latest_report_analysis(project, reports)

def _render_all_projects_table(projects: List[ProjectSummary], show_more_link: bool = False):
    """全プロジェクト一覧テーブル（展開可能形式）"""
    
    if not projects:
        st.info("表示可能なプロジェクトはありません。")
        return
    
    # ステータスラベルの日本語変換
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
    
    # プロジェクト一覧を展開可能形式で表示
    for i, project in enumerate(projects):
        # ステータス色の決定
        status_color = _get_status_color(project.current_status)
        status_text = status_labels.get(project.current_status.value, project.current_status.value) if project.current_status else '不明'
        risk_text = risk_labels.get(project.risk_level.value, project.risk_level.value) if project.risk_level else '不明'
        
        # 展開可能なプロジェクト行
        with st.expander(f"{project.project_name} ({status_text})", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                **プロジェクトID:** {project.project_id}  
                **場所:** {project.location}  
                **現在フェーズ:** {project.current_phase}  
                **担当者:** {project.responsible_person}
                """)
            
            with col2:
                st.markdown(f"""
                **ステータス:** <span style='color: {status_color}; font-weight: bold;'>{status_text}</span>  
                **リスクレベル:** {risk_text}  
                **最終報告:** {project.days_since_last_report}日前  
                **完了予定:** {project.estimated_completion.strftime('%Y-%m-%d') if project.estimated_completion else '未定'}
                """, unsafe_allow_html=True)
            
            # 最新報告書概要があれば表示
            if project.latest_report_summary:
                st.markdown("**最新報告書概要:**")
                st.markdown(f"> {project.latest_report_summary[:100]}...")
    
    # プロジェクト一覧ページへのリンク
    if show_more_link:
        if st.button("案件一覧ページで全件確認", key="goto_list_expandable", use_container_width=True):
            # 案件一覧ページに遷移
            st.session_state.current_page = "案件一覧"
            st.rerun()

def _render_status_distribution_chart(status_groups: Dict[str, List[ProjectSummary]]):
    """ステータス分布チャート"""
    st.markdown("<div class='custom-header'>プロジェクトステータス分布</div>", unsafe_allow_html=True)
    
    # データ準備
    status_labels = []
    status_counts = []
    colors = []
    
    status_config = {
        'stopped': ('停止', '#FF6B35'),
        'major_delay': ('重大な遅延', '#FFA500'),
        'minor_delay': ('軽微な遅延', '#FFD700'),
        'normal': ('順調', '#28a745'),
        'unknown': ('不明', '#6C757D')
    }
    
    for status, projects in status_groups.items():
        if projects:  # プロジェクトがある場合のみ表示
            label, color = status_config.get(status, (status, '#6C757D'))
            status_labels.append(label)
            status_counts.append(len(projects))
            colors.append(color)
    
    if status_counts:
        fig = go.Figure(data=[go.Pie(
            labels=status_labels,
            values=status_counts,
            hole=.4,
            marker_colors=colors
        )])
        
        fig.update_layout(
            title='',
            showlegend=True,
            height=300,
            margin=dict(t=20, b=20, l=20, r=20),
            font=dict(size=16),  # グラフ全体の文字サイズ
            legend=dict(font=dict(size=16))  # 凡例の文字サイズ
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("表示可能なデータがありません。")

def _render_category_distribution_chart(projects: List[ProjectSummary]):
    """遅延理由分布チャート（プロジェクトベース）"""
    # プロジェクトベースで遅延理由分布チャートを表示
    _render_project_based_delay_reason_chart(projects)

def _render_timeline_chart(projects: List[ProjectSummary]):
    """案件完了予定タイムライン（月別集計・過去1年〜未来2年）"""
    # タイトルは呼び出し元で表示済み
    
    # 期間設定：過去1年〜未来2年
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    import calendar
    
    now = datetime.now()
    start_date = now - relativedelta(years=1)
    end_date = now + relativedelta(years=2)
    
    # 完了予定のあるプロジェクトを期間内でフィルタ
    timeline_projects = [
        p for p in projects 
        if p.estimated_completion and start_date <= p.estimated_completion <= end_date
    ]
    
    if not timeline_projects:
        st.info("指定期間内に完了予定が設定されているプロジェクトがありません。")
        return
    
    # 月別データ集計
    from collections import defaultdict
    
    monthly_data = defaultdict(lambda: {"工事中": 0, "完了済み": 0, "未着手": 0})
    
    for project in timeline_projects:
        # 完了予定日を月初に変換
        completion_date = project.estimated_completion
        month_key = completion_date.replace(day=1).strftime('%Y-%m')
        
        # プロジェクトステータスを判定
        if project.current_status:
            if project.current_status.value in ['stopped']:
                status_category = "未着手"
            elif project.current_status.value in ['major_delay', 'minor_delay', 'normal']:
                # 完了予定日が過去なら完了済み、未来なら工事中
                if completion_date < now:
                    status_category = "完了済み"
                else:
                    status_category = "工事中"
            else:
                status_category = "工事中"
        else:
            status_category = "工事中"
        
        monthly_data[month_key][status_category] += 1
    
    # 期間内の全月を生成（データがない月も含む）
    months = []
    current = start_date.replace(day=1)
    while current <= end_date:
        months.append(current.strftime('%Y-%m'))
        current += relativedelta(months=1)
    
    # データ補完（データがない月は0で埋める）
    for month in months:
        if month not in monthly_data:
            monthly_data[month] = {"工事中": 0, "完了済み": 0, "未着手": 0}
    
    # ソート
    months = sorted(months)
    
    fig = go.Figure()
    
    # 各ステータス別に棒グラフを追加
    colors = {
        "完了済み": "#28a745",
        "工事中": "#FFA500", 
        "未着手": "#FF6B35"
    }
    
    for status in ["完了済み", "工事中", "未着手"]:
        values = [monthly_data[month][status] for month in months]
        fig.add_trace(go.Bar(
            name=status,
            x=months,
            y=values,
            marker_color=colors[status],
            hovertemplate=f'<b>{status}</b><br>月: %{{x}}<br>プロジェクト数: %{{y}}<extra></extra>'
        ))
    
    fig.update_layout(
        title='',
        xaxis_title='完了予定月',
        yaxis_title='プロジェクト数',
        height=400,
        margin=dict(t=20, b=40, l=40, r=20),
        font=dict(size=14),
        barmode='stack',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=16)
        )
    )
    
    # x軸の日付フォーマットを調整
    fig.update_xaxes(
        tickformat='%Y-%m',
        tickangle=45,
        dtick="M1"  # 月単位で表示
    )
    
    st.plotly_chart(fig, use_container_width=True)

def _render_latest_report_analysis(project: ProjectSummary, reports: List = None):
    """最新レポートの詳細をプロジェクト一覧ページのスタイルで表示"""
    st.markdown("---")
    
    if not reports:
        st.warning("レポートデータが提供されていません。")
        return
    
    # プロジェクトに紐づく最新レポートを検索
    project_reports = [r for r in reports if r.project_id == project.project_id]
    
    if not project_reports:
        st.info(f"プロジェクト {project.project_id} に紐づくレポートが見つかりません。")
        return
    
    # 最新レポートを取得（作成日時順）
    latest_report = max(project_reports, key=lambda x: x.created_at)
    
    # プロジェクト一覧ページと同じスタイルで表示
    st.markdown(f"**📄 {latest_report.file_name} の詳細**")
    
    # ステータスラベルの日本語化
    status_labels = {
        'stopped': '停止',
        'major_delay': '重大な遅延',
        'minor_delay': '軽微な遅延', 
        'normal': '順調'
    }
    
    # 問題区分の日本語化
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
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**レポート種別:** {latest_report.report_type.value}")
        st.markdown(f"**作成日時:** {latest_report.created_at.strftime('%Y-%m-%d %H:%M')}")
        status_text = status_labels.get(latest_report.status_flag.value, "不明") if latest_report.status_flag else "不明"
        st.markdown(f"**ステータス:** {status_text}")
    
    with col2:
        risk_text = latest_report.risk_level.value if latest_report.risk_level else "不明"
        st.markdown(f"**リスクレベル:** {risk_text}")
        urgency = getattr(latest_report, 'urgency_score', 0)
        st.markdown(f"**緊急度スコア:** {urgency}")
        
        # 問題区分（日本語化）
        # category_labels削除: 遅延理由体系に統一
        if False:  # 無効化
            st.markdown(f"**問題区分:** {', '.join(categories_jp)}")
    
    if latest_report.analysis_result:
        st.markdown("**📝 分析結果:**")
        st.markdown(f"**要約:** {latest_report.analysis_result.summary}")
        if latest_report.analysis_result.issues:
            st.markdown(f"**問題点:** {', '.join(latest_report.analysis_result.issues)}")
        if latest_report.analysis_result.key_points:
            st.markdown(f"**重要ポイント:** {', '.join(latest_report.analysis_result.key_points)}")

def _render_project_details_inline(project: ProjectSummary):
    """プロジェクト詳細をカード内にインライン表示（旧関数・互換性維持）"""
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**プロジェクト詳細**")
        st.markdown(f"• **プロジェクトID**: {project.project_id}")
        risk_text = project.risk_level.value if project.risk_level else '不明'
        st.markdown(f"• **リスクレベル**: {risk_text}")
        completion_text = project.estimated_completion.strftime('%Y-%m-%d') if project.estimated_completion else '未定'
        st.markdown(f"• **完了予定**: {completion_text}")
    
    with col2:
        st.markdown("**最新レポート要約**")
        if project.latest_report_summary:
            st.markdown(f"• {project.latest_report_summary}")
        else:
            st.markdown("• レポート要約データなし")
        
        # category_labels削除: 遅延理由体系に統一
        if False:  # 無効化
            st.markdown(f"• **問題区分**: {categories}")

def _render_latest_project_report(projects: List[ProjectSummary], project_id: str):
    """プロジェクトの最新レポートを表示"""
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
    st.markdown(f"<div class='custom-header'>{target_project.project_name} - 最新レポート</div>", unsafe_allow_html=True)
    
    # プロジェクト基本情報
    col1, col2, col3 = st.columns(3)
    with col1:
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
    
    st.divider()
    
    # 最新レポート要約
    if target_project.latest_report_summary:
        st.markdown("<div class='custom-header' style='font-size: 20px;'>最新レポート要約</div>", unsafe_allow_html=True)
        st.markdown(f"**要約:** {target_project.latest_report_summary}")
        st.divider()
    
    # 詳細レポート内容（実際のレポートファイルを読み込む場合）
    st.markdown("<div class='custom-header' style='font-size: 20px;'>詳細レポート内容</div>", unsafe_allow_html=True)
    
    # レポートデータの取得が必要
    st.info("詳細なレポート内容を表示するには、レポートデータとの連携が必要です。")

def _get_status_color(status):
    """ステータスに応じた色を取得"""
    if not status:
        return '#6C757D'
    
    color_map = {
        'stopped': '#FF6B35',
        'major_delay': '#FFA500',
        'minor_delay': '#FFD700',
        'normal': '#28a745'
    }
    return color_map.get(status.value, '#6C757D')

def _get_risk_color(risk_level):
    """リスクレベルに応じた色を取得"""
    if not risk_level:
        return '#6C757D'
    
    color_map = {
        '高': '#FF6B35',
        '中': '#FFA500',
        '低': '#28a745'
    }
    return color_map.get(risk_level.value, '#6C757D')

def _get_urgency_score(project: ProjectSummary) -> int:
    """プロジェクトの緊急度スコアを算出"""
    score = 0
    
    # ステータス基準
    if project.current_status:
        status_scores = {
            'stopped': 100,
            'major_delay': 80,
            'minor_delay': 40,
            'normal': 20
        }
        score += status_scores.get(project.current_status.value, 0)
    
    # リスクレベル基準
    if project.risk_level:
        risk_scores = {
            'high': 50,
            'medium': 30,
            'low': 10
        }
        score += risk_scores.get(project.risk_level.value, 0)
    
    # 最終報告からの経過日数（長いほど緊急）
    if project.days_since_last_report:
        score += min(project.days_since_last_report * 2, 50)
    
    return score

def _render_urgent_response_alerts(projects: List[ProjectSummary], reports: List = None):
    """要緊急対応案件アラート表示（使用者目線で本当に確認すべき案件）"""
    urgent_projects = []
    
    for project in projects:
        is_urgent = False
        urgent_reasons = []
        
        # 1. 今まで順調だったのに緊急停止した案件
        if project.current_status and project.current_status.value == 'stopped':
            # 過去のステータスが順調だったかどうかは履歴がないため、停止状態を緊急として扱う
            is_urgent = True
            urgent_reasons.append("案件が緊急停止状態")
        
        # 2. 最近報告書があがっていない案件（14日以上）
        if project.days_since_last_report >= 14:
            is_urgent = True
            urgent_reasons.append(f"最終報告から{project.days_since_last_report}日経過（長期未報告）")
        
        # 3. 重大な遅延かつ高リスクの案件
        if (project.current_status and project.current_status.value == 'major_delay' and 
            project.risk_level and project.risk_level.value == '高'):
            is_urgent = True
            urgent_reasons.append("重大遅延かつ高リスク")
        
        # 4. 工期が未定または大幅に過ぎている案件
        if project.estimated_completion:
            if '未定' in str(project.estimated_completion):
                is_urgent = True
                urgent_reasons.append("完了予定が未定")
            else:
                try:
                    from datetime import datetime
                    if isinstance(project.estimated_completion, datetime):
                        days_overdue = (datetime.now() - project.estimated_completion).days
                        if days_overdue > 30:  # 30日以上過ぎている
                            is_urgent = True
                            urgent_reasons.append(f"完了予定より{days_overdue}日過ぎている")
                except:
                    pass
        
        # 5. 特殊な遅延理由がある案件（重大問題や人的確認が必要）
        if hasattr(project, 'delay_reasons') and project.delay_reasons:
            for delay_reason in project.delay_reasons:
                if isinstance(delay_reason, dict):
                    category = delay_reason.get('category', '')
                    if category == '重大問題（要人的確認）':
                        is_urgent = True
                        urgent_reasons.append(f"特殊な問題: {delay_reason.get('description', category)}")
        
        if is_urgent:
            project.urgent_reasons = urgent_reasons
            urgent_projects.append(project)
    
    # 要緊急対応案件アラートの表示（ヘッダーは呼び出し元で表示済み）
    
    if urgent_projects:
        # 緊急度順でソート（停止 > 長期未報告 > 重大遅延+高リスク > その他）
        def get_urgency_priority(project):
            reasons = getattr(project, 'urgent_reasons', [])
            if any('緊急停止' in reason for reason in reasons):
                return 4
            elif any('長期未報告' in reason for reason in reasons):
                return 3
            elif any('重大遅延かつ高リスク' in reason for reason in reasons):
                return 2
            else:
                return 1
        
        urgent_projects.sort(key=get_urgency_priority, reverse=True)
        
        for project in urgent_projects[:5]:  # 上位5件のみ表示
            with st.container():
                reasons_text = "<br/>".join(getattr(project, 'urgent_reasons', ['確認が必要']))
                
                # ステータスラベルの日本語変換
                status_labels = {
                    'stopped': '停止',
                    'major_delay': '重大な遅延',
                    'minor_delay': '軽微な遅延', 
                    'normal': '順調'
                }
                status_text = status_labels.get(project.current_status.value, project.current_status.value) if project.current_status else '不明'
                
                st.markdown(f"""
                <div style="border: 2px solid #FF4B4B; border-radius: 8px; padding: 12px; margin: 8px 0; background-color: #FFF5F5;">
                    <h4 style="margin: 0; color: #FF4B4B;">⚠️ {project.project_name}</h4>
                    <p style="margin: 4px 0;"><strong>ステータス:</strong> {status_text}</p>
                    <p style="margin: 4px 0;"><strong>完了予定:</strong> {project.estimated_completion.strftime('%Y-%m-%d') if project.estimated_completion and hasattr(project.estimated_completion, 'strftime') else project.estimated_completion}</p>
                    <p style="margin: 4px 0; color: #FF4B4B;"><strong>緊急対応理由:</strong> {reasons_text}</p>
                    <p style="margin: 4px 0; color: #FF4B4B; font-weight: bold;">→ 現場確認・対応検討が必要です</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 最新報告書詳細ボタンを追加
                with st.expander("最新報告書詳細"):
                    _render_latest_report_details(project, reports)
    else:
        st.markdown("""
        <div style="border: 1px solid #28a745; border-radius: 8px; padding: 12px; margin: 8px 0; background-color: #F5FFF5;">
            <p style="margin: 0; color: #28a745;">✅ 現在緊急対応が必要な案件はありません</p>
        </div>
        """, unsafe_allow_html=True)

def _render_latest_report_details(project: ProjectSummary, reports: List = None):
    """最新レポート詳細表示"""
    if not reports:
        st.info("レポートデータが利用できません。")
        return
    
    # プロジェクトに関連する最新レポートを検索
    project_reports = [r for r in reports if getattr(r, 'project_id', None) == project.project_id]
    
    if not project_reports:
        st.info("このプロジェクトに関連するレポートが見つかりません。")
        return
    
    # 最新レポートを特定
    latest_report = max(project_reports, key=lambda r: r.created_at)
    
    # レポート詳細表示
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"**レポートタイプ:** {latest_report.report_type.value if latest_report.report_type else '不明'}")
        st.write(f"**ファイル名:** {latest_report.file_name}")
        st.write(f"**作成日時:** {latest_report.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        if hasattr(latest_report, 'current_construction_phase') and latest_report.current_construction_phase:
            st.write(f"**建設工程:** {latest_report.current_construction_phase}")
        
        if hasattr(latest_report, 'delay_reasons') and latest_report.delay_reasons:
            st.write("**遅延理由:**")
            for reason in latest_report.delay_reasons:
                if isinstance(reason, dict):
                    st.write(f"• {reason.get('category', '不明')}: {reason.get('description', '')}")
    
    with col2:
        # ステータス・リスク表示
        status_color = {
            'stopped': '#FF4B4B',
            'major_delay': '#FF6B35', 
            'minor_delay': '#FFA500',
            'normal': '#28a745'
        }
        
        current_status = getattr(latest_report, 'current_status', 'normal')
        color = status_color.get(current_status, '#666666')
        
        st.markdown(f"""
        <div style="padding: 8px; border-radius: 4px; background-color: {color}20; border-left: 4px solid {color};">
            <strong>ステータス:</strong> {current_status}<br/>
            <strong>リスクレベル:</strong> {getattr(latest_report, 'risk_level', '不明')}<br/>
            <strong>信頼度:</strong> {getattr(latest_report, 'analysis_confidence', 0.0):.1%}
        </div>
        """, unsafe_allow_html=True)

def _render_construction_phases_overview(projects: List[ProjectSummary]):
    """7ステップ建設工程概要表示"""
    st.markdown("### 📊 建設工程7ステップ概要")
    
    # 正しい7ステップの定義
    phases = [
        "置局発注", "基本同意", "基本図承認", "内諾", 
        "附帯着工", "電波発射", "工事検収"
    ]
    
    # 各ステップの進捗状況を集計（停止状態も追加）
    phase_counts = {phase: {"完了": 0, "進行中": 0, "未着手": 0, "停止": 0} for phase in phases}
    
    for project in projects:
        current_phase = project.current_phase
        
        # プロジェクトが停止状態かチェック
        is_stopped = (
            (project.current_status and project.current_status.value == 'stopped') or
            ('未定' in str(project.estimated_completion))
        )
        
        if current_phase in phases:
            current_index = phases.index(current_phase)
            
            for i, phase in enumerate(phases):
                if is_stopped and i == current_index:
                    # 停止プロジェクトは現在フェーズで停止
                    phase_counts[phase]["停止"] += 1
                elif i < current_index:
                    # 現在フェーズより前は完了
                    phase_counts[phase]["完了"] += 1
                elif i == current_index and not is_stopped:
                    # 現在フェーズで進行中（停止でない場合）
                    phase_counts[phase]["進行中"] += 1
                else:
                    # それ以降は未着手
                    phase_counts[phase]["未着手"] += 1
    
    # 進捗バーとして表示
    cols = st.columns(len(phases))
    
    for i, (phase, col) in enumerate(zip(phases, cols)):
        with col:
            total = sum(phase_counts[phase].values())
            if total > 0:
                completed = phase_counts[phase]["完了"]
                in_progress = phase_counts[phase]["進行中"]
                stopped = phase_counts[phase]["停止"]
                not_started = phase_counts[phase]["未着手"]
                
                completed_pct = (completed / total) * 100
                in_progress_pct = (in_progress / total) * 100
                stopped_pct = (stopped / total) * 100
                
                st.markdown(f"""
                <div style="text-align: center; padding: 8px;">
                    <div style="font-size: 12px; font-weight: bold; margin-bottom: 4px;">{i+1}. {phase}</div>
                    <div style="background-color: #f0f0f0; border-radius: 4px; height: 60px; position: relative; margin-bottom: 4px;">
                        <div style="background-color: #28a745; height: {completed_pct}%; border-radius: 4px 4px 0 0;"></div>
                        <div style="background-color: #ffc107; height: {in_progress_pct}%; "></div>
                        <div style="background-color: #dc3545; height: {stopped_pct}%; "></div>
                    </div>
                    <div style="font-size: 10px;">
                        完了: {completed}<br/>
                        進行中: {in_progress}<br/>
                        停止: {stopped}<br/>
                        未着手: {not_started}
                    </div>
                </div>
                """, unsafe_allow_html=True)

def _render_delay_reason_distribution_chart(reports: List[DocumentReport]):
    """遅延理由分布チャートを表示（15カテゴリ体系）"""
    st.markdown("### 📈 遅延理由分布")
    
    # 15カテゴリの遅延理由を統計
    delay_categories = [
        "工程ミス", "要件漏れ", "無線機不具合", "物件不具合", "設計不足",
        "電源遅延", "回線不具合", "免許不具合", "法規制", "産廃発生",
        "オーナー交渉難航", "近隣交渉難航", "他事業者交渉難航", "親局不具合", "イレギュラ発生"
    ]
    
    delay_counts = {category: 0 for category in delay_categories}
    delay_counts["遅延なし"] = 0  # 遅延なしカテゴリを追加
    
    # レポートから遅延理由を集計
    for report in reports:
        if hasattr(report, 'delay_reasons') and report.delay_reasons:
            # delay_reasonsフィールドがある場合
            for delay_reason in report.delay_reasons:
                if isinstance(delay_reason, dict):
                    category = delay_reason.get('category', '')
                    if category in delay_counts:
                        delay_counts[category] += 1
                    elif category:  # 未知のカテゴリ
                        if "重大問題（要人的確認）" not in delay_counts:
                            delay_counts["重大問題（要人的確認）"] = 0
                        delay_counts["重大問題（要人的確認）"] += 1
        else:
            # delay_reasonsフィールドがない、または空の場合
            delay_counts["遅延なし"] += 1
    
    # チャートデータを作成（ゼロ以外のみ）
    chart_data = {k: v for k, v in delay_counts.items() if v > 0}
    
    if chart_data:
        # バーチャートとして表示
        try:
            import plotly.express as px
            import pandas as pd
            
            df = pd.DataFrame(list(chart_data.items()), columns=['遅延理由', '件数'])
            fig = px.bar(df, x='遅延理由', y='件数', 
                         title='遅延理由別件数',
                         color='件数',
                         color_continuous_scale='reds')
            fig.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            # Plotlyが利用できない場合はシンプルなバーチャート
            st.bar_chart(chart_data)
        
        # 詳細テーブルは削除（ユーザーリクエストにより）
    else:
        st.info("現在、遅延理由のデータがありません。")
        st.markdown("📋 **原因の可能性:**")
        st.markdown("- データの事前処理が必要")
        st.markdown("- LLMによる遅延理由抽出が未完了")
        st.markdown("- delay_reasonsフィールドの設定問題")

def _render_risk_distribution_chart(projects: List[ProjectSummary]):
    """将来遅延リスク分布チャートを表示"""
    st.markdown("<div class='custom-header'>将来遅延リスク分布</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>将来リスク評価の可視化</p>", unsafe_allow_html=True)
    
    # リスクレベル別にカウント
    risk_counts = {'高': 0, '中': 0, '低': 0}
    
    for project in projects:
        if project.risk_level:
            risk_level = project.risk_level.value
            if risk_level in risk_counts:
                risk_counts[risk_level] += 1
    
    # チャートデータを作成（ゼロ以外のみ）
    chart_data = {k: v for k, v in risk_counts.items() if v > 0}
    
    if chart_data:
        try:
            import plotly.graph_objects as go
            
            labels = list(chart_data.keys())
            values = list(chart_data.values())
            colors = {'高': '#dc3545', '中': '#ffc107', '低': '#28a745'}
            chart_colors = [colors.get(label, '#6C757D') for label in labels]
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=.4,
                marker_colors=chart_colors
            )])
            
            fig.update_layout(
                title='',
                showlegend=True,
                height=300,
                margin=dict(t=20, b=20, l=20, r=20),
                font=dict(size=16),
                legend=dict(font=dict(size=16))
            )
            
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            # Plotlyが利用できない場合はシンプルなバーチャート
            st.bar_chart(chart_data)
    else:
        st.info("リスクレベルのデータがありません。")

def _render_project_based_delay_reason_chart(projects: List[ProjectSummary]):
    """プロジェクトベースで遅延理由分布チャートを表示（15カテゴリ体系）"""
    st.markdown("<div class='custom-header'>遅延理由分布</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>15カテゴリ遅延理由体系による問題分析</p>", unsafe_allow_html=True)
    
    # 15カテゴリの遅延理由を統計
    delay_categories = [
        "工程ミス", "要件漏れ", "無線機不具合", "物件不具合", "設計不足",
        "電源遅延", "回線不具合", "免許不具合", "法規制", "産廃発生",
        "オーナー交渉難航", "近隣交渉難航", "他事業者交渉難航", "親局不具合", "イレギュラ発生"
    ]
    
    delay_counts = {category: 0 for category in delay_categories}
    delay_counts["遅延なし"] = 0  # 遅延なしカテゴリを追加
    
    # プロジェクトから遅延理由を集計
    for project in projects:
        if hasattr(project, 'delay_reasons') and project.delay_reasons:
            # delay_reasonsフィールドがある場合
            for delay_reason in project.delay_reasons:
                if isinstance(delay_reason, dict):
                    category = delay_reason.get('category', '')
                    if category in delay_counts:
                        delay_counts[category] += 1
                    elif category:  # 未知のカテゴリ
                        if "重大問題（要人的確認）" not in delay_counts:
                            delay_counts["重大問題（要人的確認）"] = 0
                        delay_counts["重大問題（要人的確認）"] += 1
        else:
            # delay_reasonsフィールドがない、または空の場合
            delay_counts["遅延なし"] += 1
    
    # チャートデータを作成（ゼロ以外のみ）
    chart_data = {k: v for k, v in delay_counts.items() if v > 0}
    
    if chart_data:
        # パイチャートとして表示
        try:
            import plotly.graph_objects as go
            
            labels = list(chart_data.keys())
            values = list(chart_data.values())
            colors = ['#FF6B35', '#FFA500', '#FFD700', '#87CEEB', '#DDA0DD', '#98FB98', '#F0E68C', '#D3D3D3']
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=.4,
                marker_colors=colors[:len(labels)]
            )])
            
            fig.update_layout(
                title='',
                showlegend=True,
                height=300,
                margin=dict(t=20, b=20, l=20, r=20),
                font=dict(size=16),
                legend=dict(font=dict(size=16))
            )
            
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            # Plotlyが利用できない場合はシンプルなバーチャート
            st.bar_chart(chart_data)
        
        # 詳細テーブルは削除（ユーザーリクエストにより）
    else:
        st.info("現在、遅延理由のデータがありません。")
        st.markdown("📋 **原因の可能性:**")
        st.markdown("- プロジェクトに遅延理由が設定されていない")
        st.markdown("- 最新レポートに遅延理由が含まれていない")
        st.markdown("- delay_reasonsフィールドのプロジェクトへの反映が未完了")
