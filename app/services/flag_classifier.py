"""
フラグ分類サービス
"""
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
from datetime import datetime, timedelta

from app.models.report import DocumentReport, FlagType, AnalysisResult
from app.config.settings import RISK_FLAGS

logger = logging.getLogger(__name__)

class FlagClassifier:
    """フラグ分類・管理クラス"""
    
    def __init__(self):
        self.flag_definitions = RISK_FLAGS
    
    def classify_report(self, report: DocumentReport) -> List[FlagType]:
        """レポートを分析してフラグを分類"""
        if not report.analysis_result:
            return [FlagType.REQUIRES_REVIEW]
        
        flags = []
        # recommended_flags削除: 新しいAnalysisResult構造では使用しない
        
        # 内容ベースで分類
        flags = self._content_based_classification(report)
        
        # 重複を除去
        return list(set(flags))
    
    def _content_based_classification(self, report: DocumentReport) -> List[FlagType]:
        """内容ベースでのフラグ分類"""
        content_lower = report.content.lower()
        flags = []
        
        # 緊急停止の判定
        emergency_keywords = [
            '緊急', '停止', '中止', '事故', '火災', '怪我', '反対', '抗議'
        ]
        if any(keyword in content_lower for keyword in emergency_keywords):
            flags.append(FlagType.EMERGENCY_STOP)
        
        # 遅延リスクの判定
        delay_keywords = [
            '遅延', '延期', '遅れ', 'スケジュール', '工期'
        ]
        if any(keyword in content_lower for keyword in delay_keywords):
            flags.append(FlagType.DELAY_RISK)
        
        # 技術課題の判定
        technical_keywords = [
            '不具合', '故障', '問題', 'トラブル', '設計', '工法', '技術'
        ]
        if any(keyword in content_lower for keyword in technical_keywords):
            flags.append(FlagType.TECHNICAL_ISSUE)
        
        # 手続き問題の判定
        procedure_keywords = [
            '申請', '許可', '免許', '承認', '手続き', '審査'
        ]
        if any(keyword in content_lower for keyword in procedure_keywords):
            flags.append(FlagType.PROCEDURE_PROBLEM)
        
        # フラグが見つからない場合
        if not flags:
            flags.append(FlagType.REQUIRES_REVIEW)
        
        return flags
    
    def get_flag_priority(self, flag: FlagType) -> int:
        """フラグの優先度を取得"""
        flag_priorities = {
            FlagType.EMERGENCY_STOP: 1,
            FlagType.DELAY_RISK: 2,
            FlagType.TECHNICAL_ISSUE: 3,
            FlagType.PROCEDURE_PROBLEM: 4,
            FlagType.REQUIRES_REVIEW: 5
        }
        return flag_priorities.get(flag, 5)
    
    def get_flag_info(self, flag: FlagType) -> Dict[str, Any]:
        """フラグの詳細情報を取得"""
        flag_key = flag.value
        if flag_key in self.flag_definitions:
            return self.flag_definitions[flag_key]
        else:
            return {
                "name": f"❓ {flag.value}",
                "description": "未定義のフラグ",
                "priority": 5,
                "color": "#808080"
            }
    
    def analyze_flag_trends(self, reports: List[DocumentReport]) -> Dict[str, Any]:
        """フラグのトレンド分析"""
        # 期間別フラグ統計
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        recent_reports = [r for r in reports if r.created_at >= week_ago]
        monthly_reports = [r for r in reports if r.created_at >= month_ago]
        
        # フラグの集計
        all_flags = []
        recent_flags = []
        
        for report in reports:
            all_flags.extend(report.flags)
        
        for report in recent_reports:
            recent_flags.extend(report.flags)
        
        # 統計データ作成
        flag_counts = Counter(flag.value for flag in all_flags)
        recent_flag_counts = Counter(flag.value for flag in recent_flags)
        
        # リスク分布
        risk_levels = []
        for report in reports:
            if report.analysis_result:
                risk_levels.append(report.analysis_result.risk_level)
        
        risk_distribution = Counter(risk_levels)
        
        return {
            "total_reports": len(reports),
            "recent_reports": len(recent_reports),
            "flag_distribution": dict(flag_counts),
            "recent_flag_distribution": dict(recent_flag_counts),
            "risk_distribution": dict(risk_distribution),
            "high_priority_count": len([
                r for r in reports 
                if r.analysis_result and r.analysis_result.urgency_score >= 7
            ]),
            "trends": self._calculate_trends(monthly_reports, recent_reports)
        }
    
    def _calculate_trends(self, monthly_reports: List[DocumentReport], recent_reports: List[DocumentReport]) -> Dict[str, str]:
        """トレンドの変化を計算"""
        trends = {}
        
        # 月次と週次のフラグ数を比較
        monthly_flag_count = sum(len(r.flags) for r in monthly_reports)
        recent_flag_count = sum(len(r.flags) for r in recent_reports)
        
        if len(recent_reports) > 0:
            recent_avg = recent_flag_count / len(recent_reports)
            monthly_avg = monthly_flag_count / len(monthly_reports) if len(monthly_reports) > 0 else 0
            
            if recent_avg > monthly_avg * 1.2:
                trends["overall"] = "増加傾向"
            elif recent_avg < monthly_avg * 0.8:
                trends["overall"] = "減少傾向"
            else:
                trends["overall"] = "安定"
        else:
            trends["overall"] = "データ不足"
        
        return trends
    
    def get_priority_reports(self, reports: List[DocumentReport], limit: int = 10) -> List[DocumentReport]:
        """優先度の高いレポートを取得"""
        # 緊急度スコアでソート
        sorted_reports = sorted(
            reports,
            key=lambda r: (
                r.analysis_result.urgency_score if r.analysis_result else 0,
                len([f for f in r.flags if f == FlagType.EMERGENCY_STOP])
            ),
            reverse=True
        )
        
        return sorted_reports[:limit]