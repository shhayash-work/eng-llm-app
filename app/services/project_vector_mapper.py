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
        """マッチしたキーワード抽出"""
        import re
        
        query_words = set(re.findall(r'[ぁ-んァ-ヶ一-龠a-zA-Z0-9]+', query))
        desc_words = set(re.findall(r'[ぁ-んァ-ヶ一-龠a-zA-Z0-9]+', description))
        
        matched = query_words.intersection(desc_words)
        return list(matched)
    
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