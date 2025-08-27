"""
プロジェクト集約サービス
建設プロジェクトとレポートを関連付けて集約表示するためのサービス
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from app.models.report import DocumentReport, StatusFlag, RiskLevel

logger = logging.getLogger(__name__)

@dataclass
class ProjectSummary:
    """プロジェクト要約データ"""
    project_id: str
    project_name: str
    location: str
    current_phase: str
    start_date: Optional[datetime]
    estimated_completion: Optional[datetime]
    responsible_person: str
    phases: List[Dict[str, str]] = None  # 詳細フェーズデータ
    
    # 最新レポートから導出
    current_status: Optional[StatusFlag] = None
    risk_level: Optional[RiskLevel] = None
    latest_report_date: Optional[datetime] = None
    latest_report_summary: str = ""
    # category_labels削除: 15カテゴリ遅延理由体系に統一
    delay_reasons: List[Dict[str, str]] = field(default_factory=list)  # 最新レポートの遅延理由
    
    # プロジェクト指標
    total_reports: int = 0
    recent_issues_count: int = 0
    days_since_last_report: int = 0
    
    def __post_init__(self):
        # category_labels削除: 15カテゴリ遅延理由体系に統一
        if self.phases is None:
            self.phases = []

class ProjectAggregator:
    """プロジェクト集約サービス"""
    
    def __init__(self):
        self.project_mapping_file = Path("data/sample_construction_data/project_reports_mapping.json")
    
    def aggregate_projects(self, reports: List[DocumentReport]) -> List[ProjectSummary]:
        """プロジェクト単位でレポートを集約"""
        try:
            # プロジェクトマッピングを読み込み
            project_mapping = self._load_project_mapping()
            
            # ファイル名 -> レポートのマッピングを作成
            reports_by_filename = {report.file_name: report for report in reports}
            
            project_summaries = []
            
            for project_data in project_mapping:
                # プロジェクト基本情報
                project_summary = ProjectSummary(
                    project_id=project_data["project_id"],
                    project_name=project_data["project_name"],
                    location=project_data["location"],
                    current_phase=project_data["current_phase"],
                    start_date=self._parse_date(project_data.get("start_date")),
                    estimated_completion=self._parse_date(project_data.get("estimated_completion")),
                    responsible_person=project_data.get("responsible_person", "不明"),
                    phases=project_data.get("phases", [])  # 詳細フェーズデータ
                )
                
                # プロジェクトに紐づくレポートを集約（project_idで直接マッチング）
                project_reports = []
                latest_report = None
                latest_date = None
                
                # project_idが一致するレポートを検索
                for report in reports:
                    if report.project_id == project_data["project_id"]:
                        project_reports.append(report)
                        
                        # 最新レポートを特定（created_atで判定）
                        if latest_date is None or report.created_at > latest_date:
                            latest_report = report
                            latest_date = report.created_at
                
                # 最新レポートの情報をプロジェクトサマリーに反映
                if latest_report:
                    # status_flagを直接使用（簡素化）
                    project_summary.current_status = latest_report.status_flag or StatusFlag.NORMAL
                    
                    # risk_levelを直接使用（簡素化）
                    project_summary.risk_level = latest_report.risk_level or RiskLevel.LOW
                    project_summary.latest_report_date = latest_date
                    project_summary.latest_report_summary = getattr(latest_report.analysis_result, 'summary', '') if latest_report.analysis_result else ""
                    
                    # 🚧 最新レポートの遅延理由をプロジェクトサマリーに反映
                    if hasattr(latest_report, 'delay_reasons') and latest_report.delay_reasons:
                        project_summary.delay_reasons = latest_report.delay_reasons
                    else:
                        project_summary.delay_reasons = []
                
                # プロジェクト指標を計算
                project_summary.total_reports = len(project_reports)
                project_summary.recent_issues_count = sum(1 for r in project_reports 
                                                        if r.status_flag and r.status_flag in [StatusFlag.STOPPED, StatusFlag.MAJOR_DELAY])
                
                if latest_date and isinstance(latest_date, datetime):
                    project_summary.days_since_last_report = (datetime.now() - latest_date).days
                else:
                    project_summary.days_since_last_report = 0
                
                project_summaries.append(project_summary)
            
            # リスクレベルと状態で並び替え（優先度順）
            return sorted(project_summaries, key=self._get_priority_score, reverse=True)
            
        except Exception as e:
            logger.error(f"プロジェクト集約でエラー: {e}")
            return []
    
    def _load_project_mapping(self) -> List[Dict[str, Any]]:
        """プロジェクトマッピングファイルを読み込み（フェーズデータをマージ）"""
        try:
            # プロジェクトマッピングファイル読み込み
            with open(self.project_mapping_file, 'r', encoding='utf-8') as f:
                project_mapping = json.load(f)
            
            # construction_phases.jsonから詳細フェーズデータを読み込み
            from app.config.settings import CONSTRUCTION_DATA_DIR
            phases_file = CONSTRUCTION_DATA_DIR / "construction_phases.json"
            phases_data = {}
            if phases_file.exists():
                with open(phases_file, 'r', encoding='utf-8') as f:
                    phases_list = json.load(f)
                phases_data = {item["project_id"]: item.get("phases", []) for item in phases_list}
            
            # フェーズデータをマージ
            for project_data in project_mapping:
                project_id = project_data.get("project_id")
                if project_id in phases_data:
                    project_data["phases"] = phases_data[project_id]
                else:
                    project_data["phases"] = []
            
            return project_mapping
        except Exception as e:
            logger.error(f"プロジェクトマッピング読み込みエラー: {e}")
            return []
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """日付文字列をdatetimeに変換"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str)
        except:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except:
                return None
    
    def _get_priority_score(self, project: ProjectSummary) -> int:
        """プロジェクトの優先度スコアを計算（高い方が優先）"""
        score = 0
        
        # ステータスによる重み
        if project.current_status == StatusFlag.STOPPED:
            score += 1000  # 最高優先度
        elif project.current_status == StatusFlag.MAJOR_DELAY:
            score += 800
        elif project.current_status == StatusFlag.MINOR_DELAY:
            score += 400
        
        # リスクレベルによる重み
        if project.risk_level == RiskLevel.HIGH:
            score += 300
        elif project.risk_level == RiskLevel.MEDIUM:
            score += 200
        elif project.risk_level == RiskLevel.LOW:
            score += 100
        
        # 最近の課題数
        score += project.recent_issues_count * 50
        
        # 報告の新しさ（古いレポートほど注意が必要）
        if project.days_since_last_report > 14:
            score += 100
        elif project.days_since_last_report > 7:
            score += 50
        
        return score
    
    def get_projects_by_status(self, projects: List[ProjectSummary]) -> Dict[str, List[ProjectSummary]]:
        """ステータス別にプロジェクトを分類"""
        status_groups = {
            'stopped': [],
            'major_delay': [],
            'minor_delay': [],
            'normal': [],
            'unknown': []
        }
        
        for project in projects:
            if project.current_status:
                status_groups[project.current_status.value].append(project)
            else:
                status_groups['unknown'].append(project)
        
        return status_groups
    
    def get_dashboard_metrics(self, projects: List[ProjectSummary]) -> Dict[str, Any]:
        """ダッシュボード用のメトリクスを計算"""
        total_projects = len(projects)
        
        if total_projects == 0:
            return {
                'total_projects': 0,
                'stopped_count': 0,
                'major_delay_count': 0,
                'minor_delay_count': 0,
                'unknown_count': 0,
                'normal_count': 0,
                'high_risk_count': 0,
                'overdue_reports_count': 0
            }
        
        # 現在の状況ベースでカウント（実際の報告書データから算出）
        stopped_count = sum(1 for p in projects if p.current_status == StatusFlag.STOPPED)
        major_delay_count = sum(1 for p in projects if p.current_status == StatusFlag.MAJOR_DELAY)
        minor_delay_count = sum(1 for p in projects if p.current_status == StatusFlag.MINOR_DELAY)
        
        # 不明工程数：ステータスがNoneまたは明確でない工程
        unknown_count = sum(1 for p in projects if (
            p.current_status is None or 
            (hasattr(p, 'project_id') and (not p.project_id or p.project_id == '不明')) or
            (hasattr(p, 'total_reports') and p.total_reports == 0)
        ))
        
        # 順調工程数：全工程数 - 停止 - 重大遅延 - 軽微遅延 - 不明
        normal_count = max(0, total_projects - stopped_count - major_delay_count - minor_delay_count - unknown_count)
        
        return {
            'total_projects': total_projects,
            'stopped_count': stopped_count,
            'major_delay_count': major_delay_count,
            'minor_delay_count': minor_delay_count,
            'unknown_count': unknown_count,
            'normal_count': normal_count,  # 自動計算された順調工程数
            # 分数表示用
            'stopped_fraction': f"{stopped_count}/{total_projects}",
            'major_delay_fraction': f"{major_delay_count}/{total_projects}",
            'minor_delay_fraction': f"{minor_delay_count}/{total_projects}",
            'unknown_fraction': f"{unknown_count}/{total_projects}",
            'normal_fraction': f"{normal_count}/{total_projects}",
            # パーセンテージ
            'stopped_percentage': (stopped_count / total_projects) * 100,
            'major_delay_percentage': (major_delay_count / total_projects) * 100,
            'minor_delay_percentage': (minor_delay_count / total_projects) * 100,
            'unknown_percentage': (unknown_count / total_projects) * 100,
            'normal_percentage': (normal_count / total_projects) * 100
        }