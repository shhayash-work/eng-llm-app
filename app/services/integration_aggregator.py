"""
統合分析結果ベースのプロジェクト集約サービス
統合分析結果から ProjectSummary オブジェクトを作成
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.services.project_aggregator import ProjectSummary
from app.models.report import DocumentReport, StatusFlag, RiskLevel
from app.models.construction import ConstructionProject

logger = logging.getLogger(__name__)

class IntegrationAggregator:
    """統合分析結果ベースのプロジェクト集約"""
    
    def create_project_summaries_from_context(
        self, 
        context_analysis: Dict[str, Any], 
        reports: List[DocumentReport],
        projects: List[ConstructionProject]
    ) -> List[ProjectSummary]:
        """統合分析結果から ProjectSummary リストを作成"""
        
        project_summaries = []
        
        # プロジェクトマスターデータをマップ化
        project_master_map = {p.project_id: p for p in projects}
        
        # 報告書をプロジェクトIDでグループ化
        reports_by_project = {}
        for report in reports:
            if hasattr(report, 'project_id') and report.project_id:
                if report.project_id not in reports_by_project:
                    reports_by_project[report.project_id] = []
                reports_by_project[report.project_id].append(report)
        
        for project_id, analysis in context_analysis.items():
            try:
                # プロジェクトマスターデータを取得
                master_project = project_master_map.get(project_id)
                if not master_project:
                    logger.warning(f"Project master data not found for {project_id}")
                    continue
                
                # 関連報告書を取得
                project_reports = reports_by_project.get(project_id, [])
                
                # ProjectSummary を作成
                project_summary = self._create_project_summary_from_analysis(
                    project_id, analysis, master_project, project_reports
                )
                
                if project_summary:
                    project_summaries.append(project_summary)
                    
            except Exception as e:
                logger.error(f"Failed to create ProjectSummary for {project_id}: {e}")
                continue
        
        logger.info(f"Created {len(project_summaries)} ProjectSummary objects from context analysis")
        return project_summaries
    
    def _create_project_summary_from_analysis(
        self,
        project_id: str,
        analysis: Dict[str, Any],
        master_project: ConstructionProject,
        project_reports: List[DocumentReport]
    ) -> Optional[ProjectSummary]:
        """統合分析結果から単一の ProjectSummary を作成"""
        
        try:
            # ステータスフラグの変換
            overall_status = analysis.get('overall_status', 'normal')
            status_flag_map = {
                'stopped': StatusFlag.STOPPED,
                'major_delay': StatusFlag.MAJOR_DELAY,
                'minor_delay': StatusFlag.MINOR_DELAY,
                'normal': StatusFlag.NORMAL
            }
            current_status = status_flag_map.get(overall_status, StatusFlag.NORMAL)
            
            # リスクレベルの変換
            overall_risk = analysis.get('overall_risk', '低')
            risk_level_map = {
                '高': RiskLevel.HIGH,
                '中': RiskLevel.MEDIUM,
                '低': RiskLevel.LOW
            }
            risk_level = risk_level_map.get(overall_risk, RiskLevel.LOW)
            
            # 最新報告書情報
            latest_report = None
            latest_report_date = None
            days_since_last_report = 0
            
            if project_reports:
                # 最新報告書を特定
                latest_report = max(project_reports, key=lambda r: r.created_at)
                latest_report_date = latest_report.created_at
                days_since_last_report = (datetime.now() - latest_report_date).days
            
            # 最新報告書要約（統合分析の要約を優先）
            latest_report_summary = analysis.get('analysis_summary', '')
            if not latest_report_summary and latest_report:
                if hasattr(latest_report, 'analysis_result') and latest_report.analysis_result:
                    if hasattr(latest_report.analysis_result, 'summary'):
                        latest_report_summary = latest_report.analysis_result.summary
                    elif isinstance(latest_report.analysis_result, dict):
                        latest_report_summary = latest_report.analysis_result.get('summary', '')
            
            # 遅延理由の取得
            delay_reasons = analysis.get('delay_reasons_management', [])
            
            # ProjectSummary を作成
            project_summary = ProjectSummary(
                project_id=project_id,
                project_name=master_project.project_name,
                location=master_project.location,
                current_phase=analysis.get('current_phase', master_project.current_phase),
                start_date=master_project.start_date,
                estimated_completion=master_project.estimated_completion,
                responsible_person=master_project.responsible_person,
                current_status=current_status,
                risk_level=risk_level,
                latest_report_date=latest_report_date,
                latest_report_summary=latest_report_summary,
                total_reports=len(project_reports),
                days_since_last_report=days_since_last_report
            )
            
            # 🆕 統合分析固有の情報を追加
            project_summary.integration_analysis = analysis
            project_summary.delay_reasons = delay_reasons
            project_summary.recommended_actions = analysis.get('recommended_actions', [])
            project_summary.analysis_confidence = analysis.get('analysis_confidence', 0.0)
            
            # 建設工程詳細
            if 'construction_phases' in analysis:
                project_summary.construction_phases = analysis['construction_phases']
            
            return project_summary
            
        except Exception as e:
            logger.error(f"Failed to create ProjectSummary for {project_id}: {e}")
            return None

