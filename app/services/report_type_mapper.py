"""
報告書タイプから建設工程関連性マッピングサービス
"""

from typing import Dict, List, Optional
from app.models.report import ReportType

class ReportTypeMapper:
    """報告書タイプと建設工程の関連性マッピング"""
    
    # 報告書タイプと建設工程の関連性マップ
    REPORT_TYPE_PHASE_MAPPING = {
        ReportType.CONSTRUCTION_ESTIMATE: {
            "primary_phase": "置局発注",
            "related_phases": ["置局発注"],
            "description": "工事見積書は置局発注段階で作成される",
            "confidence": 0.95
        },
        ReportType.NEGOTIATION_PROGRESS: {
            "primary_phase": "基本同意", 
            "related_phases": ["基本同意", "内諾"],
            "description": "交渉経緯報告書は基本同意や内諾段階での交渉過程で作成される",
            "confidence": 0.90
        },
        ReportType.STRUCTURAL_DESIGN: {
            "primary_phase": "基本図承認",
            "related_phases": ["基本図承認"],
            "description": "強度計算結果報告書は基本図承認段階で作成される",
            "confidence": 0.95
        },
        ReportType.CONSTRUCTION_REPORT: {
            "primary_phase": "附帯着工",
            "related_phases": ["附帯着工", "電波発射", "工事検収"],
            "description": "建設工事報告書は附帯着工以降の実工事段階で作成される",
            "confidence": 0.85
        },
        ReportType.PROGRESS_UPDATE: {
            "primary_phase": "不明",
            "related_phases": ["置局発注", "基本同意", "基本図承認", "内諾", "附帯着工", "電波発射", "工事検収"],
            "description": "進捗報告書は全工程で作成される可能性がある",
            "confidence": 0.60
        },
        ReportType.TROUBLE_REPORT: {
            "primary_phase": "不明",
            "related_phases": ["置局発注", "基本同意", "基本図承認", "内諾", "附帯着工", "電波発射", "工事検収"],
            "description": "トラブル報告書は全工程で発生する可能性がある",
            "confidence": 0.60
        },
        ReportType.OTHER: {
            "primary_phase": "不明",
            "related_phases": [],
            "description": "その他の報告書は工程との関連性が不明",
            "confidence": 0.30
        }
    }
    
    @classmethod
    def get_phase_mapping(cls, report_type: ReportType) -> Dict[str, any]:
        """報告書タイプから建設工程関連性を取得"""
        return cls.REPORT_TYPE_PHASE_MAPPING.get(report_type, {
            "primary_phase": "不明",
            "related_phases": [],
            "description": "未定義の報告書タイプ",
            "confidence": 0.20
        })
    
    @classmethod
    def get_expected_phase_from_report_type(cls, report_type: ReportType) -> str:
        """報告書タイプから期待される主要工程を取得"""
        mapping = cls.get_phase_mapping(report_type)
        return mapping.get("primary_phase", "不明")
    
    @classmethod
    def is_phase_consistent(cls, report_type: ReportType, current_phase: str) -> bool:
        """報告書タイプと現在工程の整合性をチェック"""
        mapping = cls.get_phase_mapping(report_type)
        related_phases = mapping.get("related_phases", [])
        return current_phase in related_phases
    
    @classmethod
    def get_phase_analysis_for_report(cls, report_type: ReportType) -> Dict[str, any]:
        """報告書の工程分析情報を取得（統合分析用）"""
        mapping = cls.get_phase_mapping(report_type)
        
        return {
            "report_type_phase_mapping": {
                "expected_primary_phase": mapping.get("primary_phase", "不明"),
                "possible_phases": mapping.get("related_phases", []),
                "mapping_confidence": mapping.get("confidence", 0.0),
                "mapping_description": mapping.get("description", ""),
                "phase_consistency_check": True  # 後で実際の工程と比較
            }
        }
    
    @classmethod
    def get_all_mappings(cls) -> Dict[str, Dict[str, any]]:
        """全ての報告書タイプマッピングを取得"""
        result = {}
        for report_type, mapping in cls.REPORT_TYPE_PHASE_MAPPING.items():
            result[report_type.value] = mapping
        return result





