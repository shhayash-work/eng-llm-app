"""
プロジェクトマッピングサービス
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
# from difflib import SequenceMatcher  # ファジーマッチング廃止のため不要
import logging

# ベクターマッパーのインポート（オプショナル）
try:
    from .project_vector_mapper import ProjectVectorMapper
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ProjectMapping:
    """プロジェクトマッピング結果"""
    project_id: Optional[str]
    confidence_score: float
    matching_method: str
    alternative_candidates: List[str]
    extracted_info: Dict[str, str]

class ProjectMapper:
    """マルチ戦略プロジェクトマッピングサービス"""
    
    def __init__(self):
        self.project_master = self._load_project_master()
        self.location_patterns = self._build_location_patterns()
        
        # ベクターマッパー初期化（オプショナル）
        self.vector_mapper = None
        logger.info(f"VECTOR_SEARCH_AVAILABLE: {VECTOR_SEARCH_AVAILABLE}")
        if VECTOR_SEARCH_AVAILABLE:
            try:
                self.vector_mapper = ProjectVectorMapper()
                logger.info("Vector search enabled successfully")
            except Exception as e:
                logger.error(f"Failed to initialize vector mapper: {e}")
                self.vector_mapper = None
        else:
            logger.warning("Vector search module not available (import failed)")
        
    def _load_project_master(self) -> List[Dict]:
        """プロジェクトマスターデータ読み込み"""
        try:
            master_file = Path("data/sample_construction_data/project_reports_mapping.json")
            if master_file.exists():
                with open(master_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Failed to load project master: {e}")
            return []
    
    def _build_location_patterns(self) -> Dict[str, List[str]]:
        """場所パターンマッピング構築"""
        patterns = {}
        for project in self.project_master:
            location = project.get('location', '')
            project_id = project.get('project_id', '')
            project_name = project.get('project_name', '')
            
            # 場所の正規化パターン
            location_variants = [
                location,
                location.replace('都', '').replace('県', '').replace('市', '').replace('区', ''),
                # 例: "東京都品川区" -> ["東京都品川区", "品川", "品川区"]
            ]
            
            # プロジェクト名からの場所抽出
            name_locations = self._extract_locations_from_name(project_name)
            location_variants.extend(name_locations)
            
            for variant in location_variants:
                if variant and len(variant) > 1:
                    if variant not in patterns:
                        patterns[variant] = []
                    patterns[variant].append(project_id)
                    
        return patterns
    
    def _extract_locations_from_name(self, project_name: str) -> List[str]:
        """プロジェクト名から場所を抽出"""
        locations = []
        
        # 都道府県・市区町村パターン
        prefecture_pattern = r'(東京都|神奈川県|埼玉県|千葉県|大阪府|京都府|兵庫県|奈良県|和歌山県|愛知県|静岡県|岐阜県|三重県|北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|新潟県|富山県|石川県|福井県|山梨県|長野県|滋賀県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)'
        city_pattern = r'([^\s]+市|[^\s]+区|[^\s]+町|[^\s]+村)'
        
        # 都道府県抽出
        prefecture_matches = re.findall(prefecture_pattern, project_name)
        locations.extend(prefecture_matches)
        
        # 市区町村抽出
        city_matches = re.findall(city_pattern, project_name)
        locations.extend(city_matches)
        
        return locations
    
    def map_project(self, report_content: str, llm_extracted_info: Dict) -> ProjectMapping:
        """
        シンプルな2段階プロジェクトマッピング
        
        1. 直接ID抽出（LLMのみ、成功時は信頼度100%）
        2. ベクターサーチ（失敗時のフォールバック、信頼度=類似度）
        """
        
        # 戦略1: 直接ID抽出（LLMのみ）
        direct_mapping = self._strategy_direct_id_extraction(report_content, llm_extracted_info)
        if direct_mapping.project_id:  # IDが抽出できた場合
            logger.info(f"Direct ID mapping successful: {direct_mapping.project_id}")
            return direct_mapping
        
        # 戦略2: ベクターサーチ（直接ID失敗時のみ）
        if self.vector_mapper:
            vector_mapping = self._strategy_vector_search(report_content, llm_extracted_info)
            logger.info(f"Vector search completed: {vector_mapping.project_id} (confidence: {vector_mapping.confidence_score:.3f})")
            return vector_mapping
        else:
            logger.warning(f"Vector search unavailable, returning failed direct mapping. VECTOR_SEARCH_AVAILABLE: {VECTOR_SEARCH_AVAILABLE}")
            # ベクターサーチが利用できない場合でも、マスターデータから最初のプロジェクトを返す
            if self.project_master:
                fallback_project = self.project_master[0]
                logger.info(f"Using fallback project: {fallback_project['project_id']}")
                return ProjectMapping(
                    project_id=fallback_project['project_id'],
                    confidence_score=0.1,  # 低い信頼度
                    matching_method="fallback_first_project",
                    alternative_candidates=[],
                    extracted_info={"reason": "Vector search unavailable, using fallback"}
                )
            return direct_mapping
    
    def _strategy_direct_id_extraction(self, content: str, llm_info: Dict) -> ProjectMapping:
        """戦略1: 直接ID抽出（LLMのみ）"""
        
        # LLMから抽出されたproject_idをチェック
        llm_project_id = None
        if 'project_info' in llm_info and llm_info['project_info']:
            llm_project_id = llm_info['project_info'].get('project_id', '').strip()
        
        # プロジェクトマスターとの照合
        master_ids = [p['project_id'] for p in self.project_master]
        
        # LLM抽出IDの検証
        if llm_project_id and llm_project_id != "不明":
            if llm_project_id in master_ids:
                return ProjectMapping(
                    project_id=llm_project_id,
                    confidence_score=1.0,  # 100%（ダミー値）
                    matching_method="llm_direct",
                    alternative_candidates=[],
                    extracted_info={"llm_extracted_id": llm_project_id}
                )
        
        # 抽出失敗
        return ProjectMapping(
            project_id=None,
            confidence_score=0.0,
            matching_method="direct_id_failed",
            alternative_candidates=[],
            extracted_info={
                "llm_extracted_id": llm_project_id,
                "reason": "LLMが不明を返すかマスターテーブルに存在しない"
            }
        )
    
    # ファジーマッチング削除：シンプルな2段階方式のため不要
    
    def _extract_locations_from_content(self, content: str) -> List[str]:
        """文書内容から場所を抽出"""
        locations = []
        
        # 場所パターン抽出
        location_patterns = [
            r'場所[：:\s]*([^\n\r]+)',
            r'所在地[：:\s]*([^\n\r]+)',
            r'工事場所[：:\s]*([^\n\r]+)',
            r'建設地[：:\s]*([^\n\r]+)',
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, content)
            locations.extend([m.strip() for m in matches if m.strip()])
        
        # 都道府県・市区町村の自動抽出
        locations.extend(self._extract_locations_from_name(content))
        
        return list(set(locations))  # 重複除去
    
    def _extract_project_names_from_content(self, content: str) -> List[str]:
        """文書内容からプロジェクト名を抽出"""
        names = []
        
        name_patterns = [
            r'プロジェクト名[：:\s]*([^\n\r]+)',
            r'工事名[：:\s]*([^\n\r]+)',
            r'案件名[：:\s]*([^\n\r]+)',
            r'建設工事[：:\s]*([^\n\r]+)',
            r'局名[：:\s]*([^\n\r]+)',
            r'auRoraプラン名[：:\s]*([^\n\r]+)',
            r'プラン名[：:\s]*([^\n\r]+)',
            r'局番[：:\s]*([^\n\r]+)',
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, content)
            names.extend([m.strip() for m in matches if m.strip()])
        
        return names
    
    # 類似度計算関数削除：ファジーマッチング廃止のため不要
    
    def _strategy_vector_search(self, content: str, llm_info: Dict) -> ProjectMapping:
        """戦略3: ベクターサーチによるセマンティックマッチング（改善版：LLM抽出情報のみ使用）"""
        
        if not self.vector_mapper:
            return ProjectMapping(
                project_id=None,
                confidence_score=0.0,
                matching_method="vector_search_unavailable",
                alternative_candidates=[],
                extracted_info={}
            )
        
        try:
            # 検索クエリ作成（LLM抽出情報のみ使用）
            query_parts = []
            
            # LLM抽出情報から追加（プロジェクトマスターと同じ構造）
            if 'project_info' in llm_info and llm_info['project_info']:
                project_info = llm_info['project_info']
                
                # 優先度順に追加
                if project_info.get('station_name'):
                    query_parts.append(f"局名: {project_info['station_name']}")
                
                if project_info.get('location'):
                    query_parts.append(f"場所: {project_info['location']}")
                
                if project_info.get('station_number'):
                    query_parts.append(f"局番: {project_info['station_number']}")
                
                if project_info.get('aurora_plan'):
                    query_parts.append(f"Aurora計画: {project_info['aurora_plan']}")
                
                if project_info.get('responsible_person'):
                    query_parts.append(f"担当者: {project_info['responsible_person']}")
            
            query_text = " ".join(query_parts)  # LLM抽出情報のみ
            
            if not query_text.strip():
                return ProjectMapping(
                    project_id=None,
                    confidence_score=0.0,
                    matching_method="vector_search_no_query",
                    alternative_candidates=[],
                    extracted_info={}
                )
            
            # ベクター検索実行（閾値0.0で必ず最高スコアのプロジェクトにマッピング）
            search_results = self.vector_mapper.search_similar_projects(
                query_text=query_text,
                top_k=5,
                similarity_threshold=0.0  # 閾値0.0で必ずマッピング
            )
            
            if search_results:
                best_result = search_results[0]
                
                # 信頼度 = ベクター類似度そのまま
                confidence = best_result.similarity_score
                
                return ProjectMapping(
                    project_id=best_result.project_id,
                    confidence_score=confidence,
                    matching_method="vector_search",
                    alternative_candidates=[r.project_id for r in search_results[1:3]],
                    extracted_info={
                        "query_text": query_text,
                        "vector_similarity": best_result.similarity_score,
                        "matched_keywords": best_result.matched_keywords
                    }
                )
            
            return ProjectMapping(
                project_id=None,
                confidence_score=0.0,
                matching_method="vector_search_no_match",
                alternative_candidates=[],
                extracted_info={"query_text": query_text}
            )
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return ProjectMapping(
                project_id=None,
                confidence_score=0.0,
                matching_method="vector_search_error",
                alternative_candidates=[],
                extracted_info={"error": str(e)}
            )