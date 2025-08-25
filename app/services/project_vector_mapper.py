"""
プロジェクト専用ベクターマッピングサービス
軽量・高速・スケーラブルな実装
"""

import json
import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
import ollama
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProjectVectorInfo:
    """プロジェクトベクター情報"""
    project_id: str
    project_name: str
    location: str
    embedding: List[float]
    metadata: Dict[str, str]

@dataclass
class VectorSearchResult:
    """ベクター検索結果"""
    project_id: str
    similarity_score: float
    matched_keywords: List[str]

class ProjectVectorMapper:
    """軽量プロジェクトベクターマッピング"""
    
    def __init__(self):
        self.cache_dir = Path("data/vector_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        self.vector_cache_file = self.cache_dir / "project_vectors.pkl"
        self.metadata_cache_file = self.cache_dir / "project_metadata.json"
        
        self.ollama_client = ollama.Client()
        self.embedding_model = "mxbai-embed-large:latest"
        
        # キャッシュロード
        self.project_vectors = self._load_vector_cache()
        self.project_metadata = self._load_metadata_cache()
        
        logger.info(f"ProjectVectorMapper initialized: {len(self.project_vectors)} projects loaded")
    
    def _load_vector_cache(self) -> Dict[str, np.ndarray]:
        """ベクターキャッシュロード"""
        if self.vector_cache_file.exists():
            try:
                with open(self.vector_cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Failed to load vector cache: {e}")
        return {}
    
    def _save_vector_cache(self):
        """ベクターキャッシュ保存"""
        try:
            with open(self.vector_cache_file, 'wb') as f:
                pickle.dump(self.project_vectors, f)
            logger.info("Vector cache saved")
        except Exception as e:
            logger.error(f"Failed to save vector cache: {e}")
    
    def _load_metadata_cache(self) -> Dict[str, Dict]:
        """メタデータキャッシュロード"""
        if self.metadata_cache_file.exists():
            try:
                with open(self.metadata_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load metadata cache: {e}")
        return {}
    
    def _save_metadata_cache(self):
        """メタデータキャッシュ保存"""
        try:
            with open(self.metadata_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.project_metadata, f, ensure_ascii=False, indent=2)
            logger.info("Metadata cache saved")
        except Exception as e:
            logger.error(f"Failed to save metadata cache: {e}")
    
    def add_project(self, project_info: Dict[str, str]) -> bool:
        """
        プロジェクトをベクターデータベースに追加
        
        Args:
            project_info: プロジェクト情報 (project_id, project_name, location, etc.)
        """
        try:
            project_id = project_info['project_id']
            
            # 既存チェック
            if project_id in self.project_vectors:
                logger.info(f"Project {project_id} already exists, skipping")
                return True
            
            # プロジェクト記述文作成
            description = self._create_project_description(project_info)
            
            # エンベディング生成
            start_time = time.time()
            response = self.ollama_client.embeddings(
                model=self.embedding_model,
                prompt=description
            )
            embedding_time = time.time() - start_time
            
            # ベクター保存
            self.project_vectors[project_id] = np.array(response['embedding'])
            self.project_metadata[project_id] = {
                **project_info,
                'description': description,
                'embedding_time': embedding_time,
                'added_at': datetime.now().isoformat()
            }
            
            # キャッシュ保存（バッチ処理向け）
            if len(self.project_vectors) % 100 == 0:  # 100件ごとに保存
                self._save_vector_cache()
                self._save_metadata_cache()
            
            logger.info(f"Project {project_id} added (embedding: {embedding_time:.3f}s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add project {project_info.get('project_id', 'unknown')}: {e}")
            return False
    
    def _create_project_description(self, project_info: Dict[str, str]) -> str:
        """プロジェクト記述文作成（改善版：プロジェクトマスターデータをそのまま使用）"""
        parts = []
        
        # 基本情報
        if project_info.get('project_name'):
            parts.append(f"プロジェクト名: {project_info['project_name']}")
        
        if project_info.get('station_name'):
            parts.append(f"局名: {project_info['station_name']}")
        
        if project_info.get('station_number'):
            parts.append(f"局番: {project_info['station_number']}")
        
        if project_info.get('location'):
            parts.append(f"場所: {project_info['location']}")
        
        if project_info.get('aurora_plan'):
            parts.append(f"Aurora計画: {project_info['aurora_plan']}")
        
        if project_info.get('responsible_person'):
            parts.append(f"担当者: {project_info['responsible_person']}")
        
        if project_info.get('current_phase'):
            parts.append(f"現在フェーズ: {project_info['current_phase']}")
        
        return " ".join(parts)
    
    def search_similar_projects(
        self, 
        query_text: str, 
        top_k: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[VectorSearchResult]:
        """
        類似プロジェクト検索
        
        Args:
            query_text: 検索クエリ
            top_k: 上位何件取得するか
            similarity_threshold: 類似度の最低閾値
        """
        try:
            if not self.project_vectors:
                logger.warning("No project vectors available")
                return []
            
            # クエリエンベディング生成
            response = self.ollama_client.embeddings(
                model=self.embedding_model,
                prompt=query_text
            )
            query_vector = np.array(response['embedding'])
            
            # 全プロジェクトとの類似度計算
            similarities = []
            for project_id, project_vector in self.project_vectors.items():
                # コサイン類似度計算
                similarity = self._cosine_similarity(query_vector, project_vector)
                
                if similarity >= similarity_threshold:
                    similarities.append((project_id, similarity))
            
            # 類似度でソート
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # 結果作成
            results = []
            for project_id, similarity in similarities[:top_k]:
                metadata = self.project_metadata.get(project_id, {})
                matched_keywords = self._extract_matched_keywords(
                    query_text, 
                    metadata.get('description', '')
                )
                
                results.append(VectorSearchResult(
                    project_id=project_id,
                    similarity_score=similarity,
                    matched_keywords=matched_keywords
                ))
            
            logger.info(f"Vector search completed: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """コサイン類似度計算"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
        except Exception:
            return 0.0
    
    def _extract_matched_keywords(self, query: str, description: str) -> List[str]:
        """マッチしたキーワード抽出（表記ゆれ対応）"""
        import re
        from difflib import SequenceMatcher
        
        query_words = set(re.findall(r'[ぁ-んァ-ヶ一-龠a-zA-Z0-9]+', query))
        desc_words = set(re.findall(r'[ぁ-んァ-ヶ一-龠a-zA-Z0-9]+', description))
        
        # 完全一致
        exact_matched = query_words.intersection(desc_words)
        
        # 表記ゆれ対応（類似度0.8以上）
        fuzzy_matched = []
        for q_word in query_words:
            for d_word in desc_words:
                if q_word not in exact_matched and d_word not in exact_matched:
                    similarity = SequenceMatcher(None, q_word, d_word).ratio()
                    if similarity >= 0.8:
                        fuzzy_matched.append(f"{q_word}≈{d_word}")
        
        return list(exact_matched) + fuzzy_matched
    
    def generate_search_reasoning(self, query_text: str, search_results: List[VectorSearchResult]) -> Dict[str, Any]:
        """ベクター検索結果の詳細な根拠生成（表記ゆれ対応）"""
        if not search_results:
            return {
                "method": "vector_search",
                "status": "no_results",
                "reason": "該当するプロジェクトが見つかりませんでした",
                "confidence": 0.0
            }
        
        top_result = search_results[0]
        project_metadata = self.project_metadata.get(top_result.project_id, {})
        
        # プロジェクトマスターデータから詳細な根拠分析
        reasoning_details = {
            "method": "vector_search_with_fuzzy",
            "vector_similarity": top_result.similarity_score,
            "project_id": top_result.project_id,
            "project_name": project_metadata.get('project_name', '不明'),
            "matched_elements": [],
            "fuzzy_matches": [],
            "confidence": top_result.similarity_score
        }
        
        # プロジェクトマスターの各項目との一致度分析
        master_fields = {
            "station_name": "局名",
            "station_number": "局番", 
            "location": "所在地",
            "aurora_plan": "Auroraプラン",
            "responsible_person": "担当者"
        }
        
        from difflib import SequenceMatcher
        import re
        
        query_words = set(re.findall(r'[ぁ-んァ-ヶ一-龠a-zA-Z0-9\-]+', query_text))
        
        for field_key, field_name in master_fields.items():
            field_value = project_metadata.get(field_key, '')
            if not field_value or field_value == '不明':
                continue
                
            # 完全一致チェック
            if field_value in query_text:
                reasoning_details["matched_elements"].append({
                    "type": field_name,
                    "master_value": field_value,
                    "match_type": "完全一致",
                    "similarity": 1.0
                })
                continue
            
            # 部分一致・表記ゆれチェック
            field_words = set(re.findall(r'[ぁ-んァ-ヶ一-龠a-zA-Z0-9\-]+', field_value))
            
            for field_word in field_words:
                if len(field_word) < 2:  # 短すぎる単語はスキップ
                    continue
                    
                # 完全一致
                if field_word in query_words:
                    reasoning_details["matched_elements"].append({
                        "type": field_name,
                        "master_value": field_word,
                        "match_type": "部分一致",
                        "similarity": 1.0
                    })
                    continue
                
                # 表記ゆれチェック
                for query_word in query_words:
                    if len(query_word) < 2:
                        continue
                    similarity = SequenceMatcher(None, field_word, query_word).ratio()
                    if similarity >= 0.8:
                        reasoning_details["fuzzy_matches"].append({
                            "type": field_name,
                            "master_value": field_word,
                            "query_value": query_word,
                            "similarity": similarity,
                            "match_type": "表記ゆれ"
                        })
        
        # 総合的な根拠文生成
        reason_parts = []
        
        if reasoning_details["matched_elements"]:
            exact_matches = [m for m in reasoning_details["matched_elements"] if m["match_type"] in ["完全一致", "部分一致"]]
            if exact_matches:
                match_descriptions = [f"{m['type']}「{m['master_value']}」" for m in exact_matches]
                reason_parts.append(f"完全一致: {', '.join(match_descriptions)}")
        
        if reasoning_details["fuzzy_matches"]:
            fuzzy_descriptions = [f"{m['type']}「{m['master_value']}」≈「{m['query_value']}」({m['similarity']:.2f})" for m in reasoning_details["fuzzy_matches"]]
            reason_parts.append(f"表記ゆれ: {', '.join(fuzzy_descriptions)}")
        
        if reason_parts:
            reasoning_details["reason"] = f"ベクトル類似度は{top_result.similarity_score:.3f}と一番高く、{'; '.join(reason_parts)}が一致／類似しているためです"
        else:
            reasoning_details["reason"] = f"ベクトル類似度は{top_result.similarity_score:.3f}と一番高いですが、明確なキーワード一致はありません"
            reasoning_details["confidence"] = min(reasoning_details["confidence"], 0.6)  # キーワード一致がない場合は信頼度を下げる
        
        # 信頼度調整（より現実的な値に）
        match_count = len(reasoning_details["matched_elements"]) + len(reasoning_details["fuzzy_matches"])
        if match_count > 0:
            # マッチ数に応じて信頼度を上げるが、ベクター類似度を基準とする
            confidence_boost = match_count * 0.05  # より控えめな調整
            reasoning_details["confidence"] = min(reasoning_details["confidence"] + confidence_boost, 0.95)  # 最大0.95に制限
        else:
            # キーワード一致がない場合はベクター類似度のみ
            reasoning_details["confidence"] = reasoning_details["confidence"]
        
        return reasoning_details
    
    def update_project_vectors_from_master(self) -> int:
        """プロジェクトマスターからベクターデータを更新"""
        try:
            # プロジェクトマスター読み込み
            master_file = Path("data/sample_construction_data/project_reports_mapping.json")
            if not master_file.exists():
                logger.error("Project master file not found")
                return 0
            
            with open(master_file, 'r', encoding='utf-8') as f:
                projects = json.load(f)
            
            added_count = 0
            for project in projects:
                if self.add_project(project):
                    added_count += 1
            
            # 最終保存
            self._save_vector_cache()
            self._save_metadata_cache()
            
            logger.info(f"Vector update completed: {added_count} new projects added")
            return added_count
            
        except Exception as e:
            logger.error(f"Failed to update project vectors: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報取得"""
        return {
            "total_projects": len(self.project_vectors),
            "cache_files": {
                "vectors": self.vector_cache_file.exists(),
                "metadata": self.metadata_cache_file.exists()
            },
            "embedding_model": self.embedding_model
        }

# 使用例とベンチマーク用の補助関数
def benchmark_vector_operations():
    """ベクター操作のベンチマーク"""
    import time
    
    mapper = ProjectVectorMapper()
    
    # 初期化ベンチマーク
    start_time = time.time()
    added_count = mapper.update_project_vectors_from_master()
    init_time = time.time() - start_time
    
    print(f"🚀 初期化時間: {init_time:.3f}秒 ({added_count}プロジェクト)")
    
    # 検索ベンチマーク
    test_queries = [
        "横浜市港北区 5G基地局",
        "千葉県市川市 アンテナ工事",
        "埼玉県川口市 基地局建設"
    ]
    
    for query in test_queries:
        start_time = time.time()
        results = mapper.search_similar_projects(query, top_k=3)
        search_time = time.time() - start_time
        
        print(f"🔍 検索: '{query}' - {search_time:.3f}秒 ({len(results)}件)")
        for result in results:
            print(f"   → {result.project_id} (類似度: {result.similarity_score:.3f})")

if __name__ == "__main__":
    benchmark_vector_operations()