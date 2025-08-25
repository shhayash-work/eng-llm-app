"""
案件レベル統合分析サービス
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from app.models.report import DocumentReport, StatusFlag, RiskLevel
from app.services.llm_service import LLMService
from app.config.prompts import (
    INTEGRATION_SYSTEM_PROMPT,
    INTEGRATION_ANALYSIS_PROMPT,
    INTEGRATION_FEW_SHOT_EXAMPLES
)

logger = logging.getLogger(__name__)

@dataclass
class ProjectContextAnalysis:
    """案件統合分析結果"""
    project_id: str
    overall_status: StatusFlag
    overall_risk: RiskLevel
    current_phase: str
    
    # 7ステップ建設工程詳細
    construction_phases: Dict[str, Dict[str, Any]]
    
    # 時系列分析
    progress_trend: str  # 改善/悪化/停滞
    issue_continuity: str  # 新規/継続/解決済み
    report_frequency: str  # 正常/減少/停止
    
    # 分析メタデータ
    analysis_confidence: float
    analysis_summary: str
    recommended_actions: List[str]
    
    # 遅延理由管理（複数対応）
    delay_reasons_management: List[Dict[str, Any]]
    
    # 信頼度・根拠詳細
    confidence_details: Dict[str, float]
    evidence_details: Dict[str, str]

class ProjectContextAnalyzer:
    """案件レベル統合分析サービス"""
    
    def __init__(self):
        self.llm_service = LLMService()
    
    def analyze_project_context(self, project_id: str, all_reports: List[DocumentReport]) -> Optional[ProjectContextAnalysis]:
        """案件の全報告書を文脈として統合分析"""
        
        # 該当案件の報告書を抽出・時系列順にソート
        project_reports = [r for r in all_reports if r.project_id == project_id]
        if not project_reports:
            logger.warning(f"No reports found for project {project_id}")
            return None
        
        project_reports.sort(key=lambda x: x.created_at or datetime.min)
        
        # 簡易版分析（LLMを使わない高速版）
        if len(project_reports) == 1:
            return self._analyze_single_report_context(project_id, project_reports[0])
        
        # 複数報告書の統合分析
        return self._analyze_multiple_reports_context(project_id, project_reports)
    
    def _analyze_single_report_context(self, project_id: str, report: DocumentReport) -> ProjectContextAnalysis:
        """単一報告書の簡易統合分析（LLM不使用）"""
        
        # 安全にEnum値を取得
        status_flag = getattr(report, 'status_flag', StatusFlag.NORMAL)
        if status_flag is None:
            status_flag = StatusFlag.NORMAL
            
        risk_level = getattr(report, 'risk_level', RiskLevel.LOW)
        if risk_level is None:
            risk_level = RiskLevel.LOW
            
        report_type = getattr(report, 'report_type', 'OTHER')
        report_type_str = report_type.value if hasattr(report_type, 'value') else str(report_type)
        
        # 基本的な統合分析結果を作成（単一報告書ベース）
        return ProjectContextAnalysis(
            project_id=project_id,
            overall_status=status_flag,
            overall_risk=risk_level,
            current_phase="基本同意",  # デフォルト
            construction_phases={
                "置局発注": {"status": "未着手", "confidence": 0.5, "evidence": "単一報告書のため推定"},
                "基本同意": {"status": "実施中", "confidence": 0.7, "evidence": "報告書の存在から推定"},
                "基本図承認": {"status": "未着手", "confidence": 0.8, "evidence": "工程順序から推定"},
                "内諾": {"status": "未着手", "confidence": 0.8, "evidence": "工程順序から推定"},
                "附帯着工": {"status": "未着手", "confidence": 0.8, "evidence": "工程順序から推定"},
                "電波発射": {"status": "未着手", "confidence": 0.8, "evidence": "工程順序から推定"},
                "工事検収": {"status": "未着手", "confidence": 0.8, "evidence": "工程順序から推定"}
            },
            progress_trend="停滞",
            issue_continuity="不明",
            report_frequency="不明",
            analysis_confidence=0.6,
            analysis_summary=f"単一報告書（{report_type_str}）による簡易分析",
            recommended_actions=["追加報告書の提出", "詳細な進捗確認"],
            delay_reasons_management=getattr(report, 'delay_reasons', []) or [],
            confidence_details={
                "overall_status": 0.6,
                "overall_risk": 0.6,
                "current_phase": 0.5,
                "progress_trend": 0.4,
                "issue_continuity": 0.3,
                "report_frequency": 0.3
            },
            evidence_details={"単一報告書": f"{getattr(report, 'file_name', '不明')}の内容に基づく"}
        )
    
    def _analyze_multiple_reports_context(self, project_id: str, project_reports: List[DocumentReport]) -> Optional[ProjectContextAnalysis]:
        """複数報告書の統合分析（LLM使用）"""
        
        try:
            # 統合分析プロンプトを構築
            prompt = self._build_context_analysis_prompt(project_id, project_reports)
            
            # LLMで統合分析実行
            # システムプロンプトとユーザープロンプトを結合
            full_prompt = f"{INTEGRATION_SYSTEM_PROMPT}\n\n{prompt}"
            response = self.llm_service.analyze_with_context(full_prompt)
            
            # 結果をパース
            if response:
                # analyze_with_contextは辞書を返すので、文字列として処理
                if isinstance(response, dict):
                    # 辞書の場合はJSON文字列に変換
                    import json
                    response_str = json.dumps(response, ensure_ascii=False)
                else:
                    response_str = str(response)
                return self._parse_context_analysis_response(project_id, response_str)
            else:
                logger.error(f"No response from LLM for project {project_id}")
                return None
            
        except Exception as e:
            logger.error(f"Context analysis error for project {project_id}: {e}")
            # LLM再試行または別プロバイダーでの処理を推奨
            return None
    
    def _build_context_analysis_prompt(self, project_id: str, project_reports: List[DocumentReport]) -> str:
        """統合分析用プロンプトを構築"""
        
        # 報告書データを時系列順に整理
        reports_data = ""
        for i, report in enumerate(project_reports, 1):
            # 安全に属性にアクセス
            file_name = getattr(report, 'file_name', f'報告書{i}')
            created_at = getattr(report, 'created_at', None)
            created_at_str = created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else '不明'
            report_type = getattr(report, 'report_type', 'OTHER')
            report_type = report_type.value if hasattr(report_type, 'value') else str(report_type)
            
            status_flag = getattr(report, 'status_flag', '不明')
            status_flag = status_flag.value if hasattr(status_flag, 'value') else str(status_flag)
            
            risk_level = getattr(report, 'risk_level', '不明')
            risk_level = risk_level.value if hasattr(risk_level, 'value') else str(risk_level)
            delay_reasons = getattr(report, 'delay_reasons', [])
            urgency_score = getattr(report, 'urgency_score', 0)
            
            reports_data += f"""
==================================================
報告書{i}: {file_name}
作成日時: {created_at_str}
レポートタイプ: {report_type}
ステータス: {status_flag}
リスクレベル: {risk_level}
要約: {self._get_report_summary(report)}
問題: {self._get_report_issues(report)}
遅延理由: {delay_reasons if delay_reasons else []}
緊急度スコア: {urgency_score}

=================================================="""

        # プロンプトを構築（新しい構造を使用）
        main_prompt = INTEGRATION_ANALYSIS_PROMPT.format(
            project_id=project_id,
            report_count=len(project_reports),
            reports_data=reports_data
        )
        
        # Few-shot例を追加
        full_prompt = f"{main_prompt}\n\n{INTEGRATION_FEW_SHOT_EXAMPLES}"
        
        return full_prompt
    
    def _get_report_summary(self, report) -> str:
        """報告書の要約を取得"""
        return getattr(report, 'summary', None) or "要約なし"
    
    def _get_report_issues(self, report) -> str:
        """報告書の問題を取得"""
        issues = getattr(report, 'issues', None)
        if issues:
            return str(issues)
        return "問題なし"
    
    def _parse_context_analysis_response(self, project_id: str, response: str) -> Optional[ProjectContextAnalysis]:
        """LLM応答から統合分析結果をパース"""
        
        try:
            # JSONレスポンスをパース
            import json
            
            # JSONブロックを抽出
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.error(f"No JSON found in response for project {project_id}")
                return None
            
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            # StatusFlagとRiskLevelの変換
            status_mapping = {
                "停止": StatusFlag.STOPPED,
                "重大な遅延": StatusFlag.MAJOR_DELAY,
                "軽微な遅延": StatusFlag.MINOR_DELAY,
                "順調": StatusFlag.NORMAL
            }
            
            risk_mapping = {
                "高": RiskLevel.HIGH,
                "中": RiskLevel.MEDIUM,
                "低": RiskLevel.LOW
            }
            
            return ProjectContextAnalysis(
                project_id=project_id,
                overall_status=status_mapping.get(data.get('overall_status'), StatusFlag.NORMAL),
                overall_risk=risk_mapping.get(data.get('overall_risk'), RiskLevel.LOW),
                current_phase=data.get('current_phase', '基本同意'),
                construction_phases=data.get('construction_phases', {}),
                progress_trend=data.get('progress_trend', '停滞'),
                issue_continuity=data.get('issue_continuity', '不明'),
                report_frequency=data.get('report_frequency', '不明'),
                analysis_confidence=data.get('analysis_metadata', {}).get('overall_confidence', 0.5),
                analysis_summary=data.get('analysis_metadata', {}).get('analysis_summary', ''),
                recommended_actions=data.get('recommended_actions', []),
                delay_reasons_management=data.get('delay_reasons_management', []),
                confidence_details={
                    'overall_status': data.get('overall_status_confidence', 0.5),
                    'overall_risk': data.get('overall_risk_confidence', 0.5),
                    'current_phase': data.get('current_phase_confidence', 0.5),
                    'progress_trend': data.get('progress_trend_confidence', 0.5),
                    'issue_continuity': data.get('issue_continuity_confidence', 0.5),
                    'report_frequency': data.get('report_frequency_confidence', 0.5)
                },
                evidence_details={
                    'overall_status': data.get('overall_status_evidence', ''),
                    'overall_risk': data.get('overall_risk_evidence', ''),
                    'current_phase': data.get('current_phase_evidence', ''),
                    'progress_trend': data.get('progress_trend_evidence', ''),
                    'issue_continuity': data.get('issue_continuity_evidence', ''),
                    'report_frequency': data.get('report_frequency_evidence', '')
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to parse context analysis response for project {project_id}: {e}")
            return None