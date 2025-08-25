"""
建設工程データモデル
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class PhaseStatus(Enum):
    """工程ステータス"""
    COMPLETED = "完了"
    IN_PROGRESS = "進行中" 
    NOT_STARTED = "未着手"
    SUSPENDED = "停止中"

class RiskLevel(Enum):
    """リスクレベル"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"

@dataclass
class ConstructionPhase:
    """建設工程フェーズ"""
    name: str
    status: PhaseStatus
    date: Optional[datetime] = None
    description: Optional[str] = None

@dataclass
class ConstructionProject:
    """建設プロジェクト"""
    project_id: str
    project_name: str
    location: str
    current_phase: str
    phases: List[ConstructionPhase]
    risk_level: RiskLevel
    start_date: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    responsible_person: Optional[str] = None
    notes: Optional[str] = None
    
    def get_current_phase_obj(self) -> Optional[ConstructionPhase]:
        """現在のフェーズオブジェクトを取得"""
        for phase in self.phases:
            if phase.name == self.current_phase:
                return phase
        return None
    
    def get_completed_phases(self) -> List[ConstructionPhase]:
        """完了済みフェーズを取得"""
        return [p for p in self.phases if p.status == PhaseStatus.COMPLETED]
    
    def get_progress_percentage(self) -> float:
        """進捗率を計算"""
        if not self.phases:
            return 0.0
        completed = len(self.get_completed_phases())
        return (completed / len(self.phases)) * 100