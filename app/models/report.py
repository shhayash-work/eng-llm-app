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
    OTHER = "OTHER"

# 新しいフラグ体系：状態フラグ（ステータス）
class StatusFlag(Enum):
    """状態フラグ（工事の現在状況）"""
    NORMAL = "normal"              # 順調
    DELAY_RISK_LOW = "delay_risk_low"    # 遅延リスク低
    DELAY_RISK_HIGH = "delay_risk_high"  # 遅延リスク高
    STOPPED = "stopped"            # 停止

# 新しいフラグ体系：原因ラベル（カテゴリ）
class CategoryLabel(Enum):
    """原因ラベル（建設業界包括カテゴリ）"""
    TECHNICAL = "technical"         # 技術課題（設計変更、工法問題、機器故障、地盤改良）
    ADMINISTRATIVE = "administrative"  # 行政手続き（免許申請、許可待ち、承認遅延）
    STAKEHOLDER = "stakeholder"     # 関係者調整（住民反対、理事会NG、近隣問題）
    FINANCIAL = "financial"         # 予算・契約（予算超過、契約変更、コスト問題）
    ENVIRONMENTAL = "environmental" # 環境・外的（天候、地盤条件、アクセス、災害）
    LEGAL = "legal"                # 法的問題（契約紛争、法令変更、責任分担）
    REQUIRES_REVIEW = "requires_review"  # 要人間確認（内容不明、分類困難）
    OTHER = "other"                # その他明確原因（上記以外の特定可能問題）

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
    """LLM分析結果"""
    project_info: Dict[str, str]
    status: str
    issues: List[str]
    risk_level: str
    recommended_flags: List[str]
    summary: str
    urgency_score: int
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
    
    @property
    def has_anomaly(self) -> bool:
        """後方互換性用プロパティ"""
        return self.is_anomaly
    
    @property
    def anomaly_score(self) -> float:
        """後方互換性用プロパティ"""
        return self.confidence
    
    @property
    def explanation(self) -> str:
        """後方互換性用プロパティ"""
        return self.anomaly_description

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
    category_labels: List[CategoryLabel] = None
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
    analysis_notes: Optional[str] = None          # LLMによる分析の備考・留意点
    
    # 📋 プロジェクトマッピング詳細情報
    project_mapping_info: Optional[Dict[str, Any]] = None  # マッピング詳細（信頼度、手法等）
    
    def __post_init__(self):
        if self.flags is None:
            self.flags = []
        if self.category_labels is None:
            self.category_labels = []
    
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
        if self.analysis_result:
            return self.analysis_result.urgency_score
        return 0