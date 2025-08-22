"""
レポートデータモデル
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ReportType(Enum):
    """レポートタイプ"""
    CONSTRUCTION_REPORT = "CONSTRUCTION_REPORT"
    TROUBLE_REPORT = "TROUBLE_REPORT"
    PROGRESS_UPDATE = "PROGRESS_UPDATE"
    # 新しい報告書タイプ
    CONSTRUCTION_ESTIMATE = "CONSTRUCTION_ESTIMATE"       # 工事見積書
    NEGOTIATION_PROGRESS = "NEGOTIATION_PROGRESS"         # 交渉経緯報告書
    STRUCTURAL_DESIGN = "STRUCTURAL_DESIGN"               # 強度計算結果報告書
    OTHER = "OTHER"

# 新しいフラグ体系：状態フラグ（ステータス）
class StatusFlag(Enum):
    """状態フラグ（現時点の客観的状況）"""
    NORMAL = "normal"              # 順調
    MINOR_DELAY = "minor_delay"    # 軽微な遅延
    MAJOR_DELAY = "major_delay"    # 重大な遅延
    STOPPED = "stopped"            # 停止



# 後方互換性のため旧フラグ定義も残す
class FlagType(Enum):
    """フラグタイプ（旧定義・後方互換性用）"""
    EMERGENCY_STOP = "emergency_stop"
    DELAY_RISK = "delay_risk"
    TECHNICAL_ISSUE = "technical_issue"
    PROCEDURE_PROBLEM = "procedure_problem"
    REQUIRES_REVIEW = "requires_review"

class RiskLevel(Enum):
    """リスクレベル"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"

class ConstructionStatus(Enum):
    """工程ステータス"""
    NOT_STARTED = "未着手"
    IN_PROGRESS = "進行中"
    COMPLETED = "完了"
    SUSPENDED = "中断"

@dataclass
class AnalysisResult:
    """LLM分析結果（簡素化）"""
    summary: str
    issues: List[str]
    key_points: List[str]
    confidence: float = 0.0
    
@dataclass
class AnomalyDetection:
    """異常検知結果"""
    is_anomaly: bool
    anomaly_description: str
    confidence: float
    suggested_action: str
    requires_human_review: bool
    similar_cases: List[str]
    
    # 後方互換性プロパティ削除: 使用されていないため

@dataclass
class DocumentReport:
    """文書レポート"""
    file_path: str
    file_name: str
    report_type: ReportType
    content: str
    created_at: datetime
    project_id: Optional[str] = None               # プロジェクトID（LLMで抽出）
    analysis_result: Optional[AnalysisResult] = None
    anomaly_detection: Optional[AnomalyDetection] = None
    flags: List[FlagType] = None
    # 新しいフラグ体系
    status_flag: Optional[StatusFlag] = None
    # category_labels削除: 15カテゴリ遅延理由体系に統一
    risk_level: Optional[RiskLevel] = None
    construction_status: Optional[ConstructionStatus] = None
    # 建設工程情報（LLMで抽出）
    current_construction_phase: Optional[str] = None    # 現在の建設工程フェーズ
    construction_progress: Optional[Dict[str, str]] = None  # 各工程の進捗状況
    
    # 🚨 データ品質監視フィールド
    has_unexpected_values: bool = False            # 想定外値の存在フラグ
    validation_issues: List[str] = field(default_factory=list)  # 検出された問題の詳細
    
    # 🤖 統合分析結果フィールド
    requires_human_review: bool = False            # LLMが分類困難と判定したかのフラグ
    analysis_confidence: float = 0.0              # LLMによる分析の確実性（0.0-1.0）
    # analysis_notes削除: summaryに統合
    
    # 📋 プロジェクトマッピング詳細情報
    project_mapping_info: Optional[Dict[str, Any]] = None  # マッピング詳細（信頼度、手法等）
    
    # 🚧 遅延理由情報（15カテゴリ体系）
    delay_reasons: List[Dict[str, str]] = field(default_factory=list)  # 新しい遅延理由体系
    
    # 🎯 緊急度スコア（将来の遅延可能性）
    urgency_score: int = 1  # 1-10スケール
    
    # current_status削除: status_flagで統一
    
    def __post_init__(self):
        if self.flags is None:
            self.flags = []
        # category_labels削除: 15カテゴリ遅延理由体系に統一
    
    def add_flag(self, flag: FlagType):
        """フラグを追加"""
        if flag not in self.flags:
            self.flags.append(flag)
    
    def remove_flag(self, flag: FlagType):
        """フラグを削除"""
        if flag in self.flags:
            self.flags.remove(flag)
    
    def get_priority_score(self) -> int:
        """優先度スコアを取得"""
        return self.urgency_score