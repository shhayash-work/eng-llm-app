"""
ダッシュボードUI
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
from datetime import datetime, timedelta
import hashlib

from app.models.report import DocumentReport, FlagType
from app.models.construction import ConstructionProject
from app.config.settings import RISK_FLAGS

def _generate_data_hash(reports: List[DocumentReport], projects: List[ConstructionProject] = None) -> str:
    """データのハッシュ値を生成（キャッシュキー用）"""
    report_data = []
    for report in reports:
        report_data.append({
            'file_name': report.file_name,
            'flags': [flag.value for flag in (report.flags or [])],
            'risk_level': getattr(report.analysis_result, 'risk_level', None) if report.analysis_result else None,
            'created_at': report.created_at.isoformat() if report.created_at else None
        })
    
    project_data = []
    if projects:
        for project in projects:
            project_data.append({
                'project_id': project.project_id,
                'progress': project.get_progress_percentage(),
                'risk_level': project.risk_level.value
            })
    
    combined_data = str(sorted(report_data, key=lambda x: x['file_name'])) + str(sorted(project_data, key=lambda x: x.get('project_id', '')))
    return hashlib.md5(combined_data.encode()).hexdigest()

def render_dashboard(reports: List[DocumentReport], projects: List[ConstructionProject]):
    """メインダッシュボードを描画"""
    st.title("🏗️ 建設管理システム - AI分析ダッシュボード")
    
    # サマリーメトリクス
    render_summary_metrics(reports, projects)
    
    # アラート情報
    render_alerts(reports)
    
    # グラフエリア
    col1, col2 = st.columns(2)
    
    with col1:
        render_flag_distribution_chart(reports)
        render_risk_level_chart(reports)
    
    with col2:
        render_timeline_chart(reports)
        render_project_progress_chart(projects)

def render_summary_metrics(reports: List[DocumentReport], projects: List[ConstructionProject]):
    """サマリーメトリクスを表示"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # 総レポート数
    with col1:
        st.metric(
            label="📄 総レポート数",
            value=len(reports)
        )
    
    # 緊急案件数
    with col2:
        emergency_count = len([
            r for r in reports 
            if FlagType.EMERGENCY_STOP in r.flags
        ])
        st.metric(
            label="🚨 緊急案件",
            value=emergency_count,
            delta=f"{emergency_count}件" if emergency_count > 0 else None
        )
    
    # 高リスク案件数
    with col3:
        high_risk_count = len([
            r for r in reports
            if r.analysis_result and r.analysis_result.risk_level in ["高"]
        ])
        st.metric(
            label="⚠️ 高リスク案件",
            value=high_risk_count
        )
    
    # 進行中プロジェクト
    with col4:
        active_projects = len([
            p for p in projects
            if any(phase.status.value == "進行中" for phase in p.phases)
        ])
        st.metric(
            label="🔧 進行中プロジェクト",
            value=active_projects
        )
    
    # 平均緊急度
    with col5:
        if reports:
            avg_urgency = sum(
                r.analysis_result.urgency_score if r.analysis_result else 0
                for r in reports
            ) / len(reports)
            st.metric(
                label="📊 平均緊急度",
                value=f"{avg_urgency:.1f}"
            )
        else:
            st.metric(
                label="📊 平均緊急度",
                value="0.0"
            )

def render_alerts(reports: List[DocumentReport]):
    """アラート情報を表示"""
    st.subheader("🔔 緊急アラート")
    
    # 緊急度の高いレポートを抽出
    high_priority_reports = [
        r for r in reports
        if r.analysis_result and r.analysis_result.urgency_score >= 7
    ]
    
    if high_priority_reports:
        for report in sorted(high_priority_reports, 
                           key=lambda x: x.analysis_result.urgency_score, 
                           reverse=True)[:5]:
            
            # フラグアイコンを取得
            flag_icons = []
            for flag in report.flags:
                flag_info = RISK_FLAGS.get(flag.value, {})
                flag_icons.append(flag_info.get('name', flag.value))
            
            flag_display = " ".join(flag_icons) if flag_icons else "❓"
            
            with st.expander(
                f"{flag_display} {report.file_name} (緊急度: {report.analysis_result.urgency_score})",
                expanded=False
            ):
                st.write(f"**ファイル:** {report.file_name}")
                st.write(f"**リスクレベル:** {report.analysis_result.risk_level}")
                st.write(f"**要約:** {report.analysis_result.summary}")
                
                if report.analysis_result.key_points:
                    st.write("**重要ポイント:**")
                    for point in report.analysis_result.key_points:
                        st.write(f"• {point}")
    else:
        st.info("現在、緊急アラートはありません。")

@st.cache_data(ttl=300)  # 5分間キャッシュ
def _generate_flag_distribution_chart(reports_hash: str, reports_data: List[Dict]) -> go.Figure:
    """フラグ分布チャートを生成（キャッシュ対応）"""
    # フラグの集計
    flag_counts = {}
    for report_data in reports_data:
        for flag_value in report_data.get('flags', []):
            flag_info = RISK_FLAGS.get(flag_value, {})
            flag_name = flag_info.get('name', flag_value)
            flag_counts[flag_name] = flag_counts.get(flag_name, 0) + 1
    
    if flag_counts:
        # 円グラフ作成
        fig = px.pie(
            values=list(flag_counts.values()),
            names=list(flag_counts.keys()),
            title="問題分類別件数"
        )
        fig.update_layout(showlegend=True, height=400)
        return fig
    return None

def render_flag_distribution_chart(reports: List[DocumentReport]):
    """フラグ分布チャートを表示"""
    st.subheader("📊 問題分類の分布")
    
    # キャッシュ用のデータ準備
    reports_hash = _generate_data_hash(reports)
    reports_data = [
        {
            'flags': [flag.value for flag in (report.flags or [])]
        }
        for report in reports
    ]
    
    # キャッシュされたチャート生成
    fig = _generate_flag_distribution_chart(reports_hash, reports_data)
    
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("フラグデータがありません。")

@st.cache_data(ttl=300)  # 5分間キャッシュ
def _generate_risk_level_chart(reports_hash: str, risk_data: List[str]) -> go.Figure:
    """リスクレベルチャートを生成（キャッシュ対応）"""
    # リスクレベルの集計
    risk_counts = {"低": 0, "中": 0, "高": 0}
    
    for risk_level in risk_data:
        if risk_level in risk_counts:
            risk_counts[risk_level] += 1
    
    # 棒グラフ作成
    colors = {"低": "#90EE90", "中": "#FFD700", "高": "#FFA500"}
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(risk_counts.keys()),
            y=list(risk_counts.values()),
            marker_color=[colors[level] for level in risk_counts.keys()],
            text=list(risk_counts.values()),
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title="リスクレベル別件数",
        xaxis_title="リスクレベル",
        yaxis_title="件数",
        height=400
    )
    
    return fig

def render_risk_level_chart(reports: List[DocumentReport]):
    """リスクレベルチャートを表示"""
    st.subheader("⚠️ リスクレベル分析")
    
    # キャッシュ用のデータ準備
    reports_hash = _generate_data_hash(reports)
    risk_data = [
        getattr(report.analysis_result, 'risk_level', '低') if report.analysis_result else '低'
        for report in reports
    ]
    
    # キャッシュされたチャート生成
    fig = _generate_risk_level_chart(reports_hash, risk_data)
    st.plotly_chart(fig, use_container_width=True)

def render_timeline_chart(reports: List[DocumentReport]):
    """タイムラインチャートを表示"""
    st.subheader("📅 時系列分析")
    
    if reports:
        # 日別のレポート数を集計
        df_data = []
        for report in reports:
            df_data.append({
                'date': report.created_at.date(),
                'count': 1,
                'urgency': report.analysis_result.urgency_score if report.analysis_result else 1
            })
        
        df = pd.DataFrame(df_data)
        daily_counts = df.groupby('date').agg({
            'count': 'sum',
            'urgency': 'mean'
        }).reset_index()
        
        # 線グラフ作成
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_counts['date'],
            y=daily_counts['count'],
            mode='lines+markers',
            name='レポート数',
            line=dict(color='blue')
        ))
        
        fig.update_layout(
            title="日別レポート数の推移",
            xaxis_title="日付",
            yaxis_title="レポート数",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("タイムラインデータがありません。")

def render_project_progress_chart(projects: List[ConstructionProject]):
    """プロジェクト進捗チャートを表示"""
    st.subheader("🏗️ プロジェクト進捗状況")
    
    if projects:
        # プロジェクトデータを準備
        project_data = []
        for project in projects:
            progress = project.get_progress_percentage()
            project_data.append({
                'name': project.project_name[:20] + "..." if len(project.project_name) > 20 else project.project_name,
                'progress': progress,
                'risk_level': project.risk_level.value,
                'location': project.location
            })
        
        df = pd.DataFrame(project_data)
        
        # 進捗バーチャート
        fig = px.bar(
            df,
            x='progress',
            y='name',
            orientation='h',
            color='risk_level',
            color_discrete_map={
                '低': '#90EE90',
                '中': '#FFD700', 
                '高': '#FFA500',
    
            },
            title="プロジェクト進捗率",
            labels={'progress': '進捗率(%)', 'name': 'プロジェクト名'}
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("プロジェクトデータがありません。")