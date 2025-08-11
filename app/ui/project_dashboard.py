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
    
    # プロジェクト状況概要
    st.markdown("<div class='custom-header'>プロジェクト状況一覧</div>", unsafe_allow_html=True)
    
    # 重要度順タブ表示
    tab1, tab2, tab3 = st.tabs(["最新報告プロジェクト", "要緊急対応プロジェクト", "通常監視プロジェクト"])
    
    with tab1:
        # 最新報告プロジェクト（最新報告日順で上位5件）
        latest_projects = sorted(active_projects, key=lambda p: p.latest_report_date or datetime.min, reverse=True)[:5]
        _render_project_list_section(latest_projects, "最新報告プロジェクト", show_more_link=len(active_projects) > 5, reports=reports)
    
    with tab2:
        # 緊急対応要（停止・遅延リスク高のうち緊急度上位5件）
        urgent_projects = [p for p in active_projects if p.current_status and p.current_status.value in ['stopped', 'delay_risk_high']]
        urgent_projects = sorted(urgent_projects, key=lambda p: _get_urgency_score(p), reverse=True)[:5]
        _render_project_list_section(urgent_projects, "要緊急対応プロジェクト", show_more_link=len([p for p in active_projects if p.current_status and p.current_status.value in ['stopped', 'delay_risk_high']]) > 5, reports=reports)
    
    with tab3:
        # 通常監視（遅延リスク低・順調のうち緊急度上位5件）
        normal_projects = [p for p in active_projects if p.current_status and p.current_status.value in ['delay_risk_low', 'normal']]
        normal_projects = sorted(normal_projects, key=lambda p: _get_urgency_score(p), reverse=True)[:5]
        _render_project_list_section(normal_projects, "通常監視プロジェクト", show_more_link=len([p for p in active_projects if p.current_status and p.current_status.value in ['delay_risk_low', 'normal']]) > 5, reports=reports)
    
    # プロジェクト分析チャート
    col1, col2 = st.columns(2)
    
    with col1:
        _render_status_distribution_chart(status_groups)
    
    with col2:
        _render_category_distribution_chart(active_projects)
    
    # 完了予定タイムライン（下部に移動）
    _render_timeline_chart(active_projects)

def _render_project_metrics(metrics: Dict[str, Any]):
    """プロジェクトメトリクス表示"""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <h3>総プロジェクト数</h3>
            <h2>{metrics['total_projects']}</h2>
            <p>100.0%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        color = "#FF6B35" if metrics['stopped_count'] > 0 else "#28a745"
        st.markdown(f"""
        <div class='metric-card'>
            <h3>停止プロジェクト</h3>
            <h2 style='color: {color};'>{metrics['stopped_count']}</h2>
            <p>{metrics['stopped_percentage']:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        color = "#FFA500" if metrics['high_risk_count'] > 0 else "#28a745"
        st.markdown(f"""
        <div class='metric-card'>
            <h3>遅延リスク高</h3>
            <h2 style='color: {color};'>{metrics['high_risk_count']}</h2>
            <p>{metrics['high_risk_percentage']:.1f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        low_risk_normal_count = metrics.get('low_risk_normal_count', 0)
        total_projects = metrics.get('total_projects', 1)
        low_risk_normal_percentage = (low_risk_normal_count / total_projects * 100) if total_projects > 0 else 0
        st.markdown(f"""
        <div class='metric-card'>
            <h3>遅延リスク低・順調</h3>
            <h2 style='color: #28a745;'>{low_risk_normal_count}</h2>
            <p>{low_risk_normal_percentage:.1f}%</p>
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
        if st.button("プロジェクト一覧ページで全件確認", key=f"goto_list_{section_title}", use_container_width=True):
            # プロジェクト一覧ページに遷移
            st.session_state.current_page = "プロジェクト一覧"
            st.rerun()

def _render_project_card(project: ProjectSummary, section_name: str = "default", reports: List = None):
    """プロジェクトカード表示（ドリルダウン対応）"""
    
    status_color = _get_status_color(project.current_status)
    
    # ステータスラベルの日本語変換
    status_labels = {
        'stopped': '停止',
        'delay_risk_high': '遅延リスク高',
        'delay_risk_low': '遅延リスク低', 
        'normal': '順調'
    }
    status_text = status_labels.get(project.current_status.value, project.current_status.value) if project.current_status else '不明'
    
    # 展開状態の管理
    expand_key = f"expand_{project.project_id}_{section_name}"
    is_expanded = st.session_state.get(expand_key, False)
    
    # プロジェクトカード表示（透明ボタン重ね合わせ版）
    background_color = '#f8f9fa' if is_expanded else 'white'
    border_color = '#007bff' if is_expanded else '#ddd'
    
    # カード内埋め込み詳細ボタン付きデザイン
    expand_icon = "▲" if is_expanded else "▼"
    unique_btn_id = f"detail_btn_{project.project_id}_{section_name}"
    
    # シンプルなカードデザイン
    st.markdown(f"""
    <div style='border: 2px solid {border_color}; border-radius: 8px; padding: 16px; margin-bottom: 8px; background-color: {background_color}; transition: all 0.3s ease;'>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
            <h4 style='margin: 0; color: #2C3E50; font-size: 18px;'>{project.project_name}</h4>
            <span style='background-color: {status_color}; color: white; padding: 6px 12px; border-radius: 4px; font-size: 14px; font-weight: bold;'>
                {status_text}
            </span>
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
        'delay_risk_high': '遅延リスク高',
        'delay_risk_low': '遅延リスク低', 
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
            
            # 最新レポート概要があれば表示
            if project.latest_report_summary:
                st.markdown("**最新報告概要:**")
                st.markdown(f"> {project.latest_report_summary[:100]}...")
    
    # プロジェクト一覧ページへのリンク
    if show_more_link:
        if st.button("プロジェクト一覧ページで全件確認", key="goto_list_expandable", use_container_width=True):
            # プロジェクト一覧ページに遷移
            st.session_state.current_page = "プロジェクト一覧"
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
        'delay_risk_high': ('遅延リスク高', '#FFA500'),
        'delay_risk_low': ('遅延リスク低', '#FFD700'),
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
    """問題区分分布チャート"""
    st.markdown("<div class='custom-header'>問題区分分布</div>", unsafe_allow_html=True)
    
    # カテゴリーラベルを集計
    category_counts = {}
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
    
    for project in projects:
        if project.category_labels:
            for category in project.category_labels:
                category_name = category_labels.get(category.value, category.value)
                category_counts[category_name] = category_counts.get(category_name, 0) + 1
    
    if category_counts:
        labels = list(category_counts.keys())
        values = list(category_counts.values())
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
    else:
        st.info("表示可能なカテゴリーデータがありません。")

def _render_timeline_chart(projects: List[ProjectSummary]):
    """プロジェクト完了予定タイムライン（月別集計・過去1年〜未来2年）"""
    st.markdown("<div class='custom-header'>プロジェクト完了予定タイムライン（月別）</div>", unsafe_allow_html=True)
    
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
            elif project.current_status.value in ['delay_risk_high', 'delay_risk_low', 'normal']:
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
        'delay_risk_high': '遅延リスク高',
        'delay_risk_low': '遅延リスク低', 
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
        urgency = latest_report.analysis_result.urgency_score if latest_report.analysis_result else 0
        st.markdown(f"**緊急度スコア:** {urgency}")
        
        # 問題区分（日本語化）
        if latest_report.category_labels:
            categories_jp = [category_labels.get(label.value, label.value) for label in latest_report.category_labels]
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
        
        if hasattr(project, 'category_labels') and project.category_labels:
            categories = ', '.join([label.value for label in project.category_labels])
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
            'delay_risk_high': '遅延リスク高',
            'delay_risk_low': '遅延リスク低', 
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
        'delay_risk_high': '#FFA500',
        'delay_risk_low': '#FFD700',
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
            'delay_risk_high': 80,
            'delay_risk_low': 40,
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