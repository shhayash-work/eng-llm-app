"""
ベクターストア管理サービス
"""
import os
import sys
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# SQLiteの問題を解決するためにpysqlite3を使用
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import ollama
from app.config.settings import (
    VECTOR_STORE_DIR, 
    EMBEDDING_MODEL, 
    CHUNK_SIZE, 
    CHUNK_OVERLAP
)

logger = logging.getLogger(__name__)

class VectorStoreService:
    """ベクターストアサービス"""
    
    def __init__(self, create_mode: bool = False):
        """
        VectorStoreService初期化
        
        Args:
            create_mode (bool): True=事前処理モード（削除・再作成）, False=読み込みモード（既存利用）
        """
        self.vector_store_dir = VECTOR_STORE_DIR
        self.collection_name = "construction_documents"
        self.create_mode = create_mode
        
        # ディレクトリ作成
        os.makedirs(self.vector_store_dir, exist_ok=True)
        
        # ChromaDBクライアント初期化
        self.client = chromadb.PersistentClient(
            path=str(self.vector_store_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Ollama埋め込みモデル設定
        self.embedding_model_name = EMBEDDING_MODEL
        self.ollama_client = ollama.Client()
        
        # テキスト分割器初期化（事前処理時のみ）
        if create_mode:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                separators=["\n\n", "\n", "。", "、", " ", ""]
            )
        
        # コレクション取得または作成
        self._setup_collection()
    
    def _setup_collection(self):
        """コレクションのセットアップ"""
        try:
            if self.create_mode:
                # 事前処理モード: 削除・再作成
                try:
                    self.client.delete_collection(name=self.collection_name)
                    logger.info(f"🗑️ Deleted existing collection: {self.collection_name}")
                except Exception:
                    pass  # コレクションが存在しない場合は無視
                
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": f"建設文書のベクターストア ({EMBEDDING_MODEL})"}
                )
                logger.info(f"✨ New collection created for {EMBEDDING_MODEL}: {self.collection_name}")
            else:
                # 読み込みモード: 既存コレクションを再利用
                try:
                    self.collection = self.client.get_collection(name=self.collection_name)
                    logger.info(f"⚡ Reusing existing collection: {self.collection_name}")
                except Exception:
                    # 既存コレクションが存在しない場合
                    logger.warning(f"⚠️ Collection {self.collection_name} not found. Creating new one.")
                    self.collection = self.client.create_collection(
                        name=self.collection_name,
                        metadata={"description": f"建設文書のベクターストア ({EMBEDDING_MODEL})"}
                    )
                    logger.info(f"🆕 Created new collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to setup collection: {e}")
            raise
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> bool:
        """文書をベクターストアに追加"""
        try:
            # コレクションの存在確認と再取得
            try:
                self.collection = self.client.get_collection(self.collection_name)
            except Exception:
                # コレクションが存在しない場合は新規作成
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": f"建設文書のベクターストア ({EMBEDDING_MODEL})"}
                )
                logger.info(f"Collection recreated: {self.collection_name}")
            
            # テキストをチャンクに分割
            chunks = self.text_splitter.split_text(content)
            
            # Ollamaエンベディング生成
            embeddings = []
            for chunk in chunks:
                response = self.ollama_client.embeddings(
                    model=self.embedding_model_name,
                    prompt=chunk
                )
                embeddings.append(response['embedding'])
            
            # チャンクIDを生成
            doc_id = metadata.get('file_name', 'unknown')
            chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            
            # メタデータをチャンクごとに複製
            chunk_metadatas = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    'chunk_id': i,
                    'chunk_text': chunk[:100] + "..." if len(chunk) > 100 else chunk
                })
                chunk_metadatas.append(chunk_metadata)
            
            # ベクターストアに追加
            self.collection.add(
                embeddings=embeddings,
                documents=chunks,
                metadatas=chunk_metadatas,
                ids=chunk_ids
            )
            
            logger.info(f"Document added: {doc_id} ({len(chunks)} chunks)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return False
    
    def add_context_analysis(self, project_id: str, analysis_data: Dict[str, Any]) -> bool:
        """統合分析結果をベクターストアに追加"""
        try:
            # コレクションの存在確認と再取得
            try:
                self.collection = self.client.get_collection(self.collection_name)
            except Exception:
                # コレクションが存在しない場合は新規作成
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": f"建設文書のベクターストア ({EMBEDDING_MODEL})"}
                )
                logger.info(f"Collection recreated: {self.collection_name}")
            
            # 統合分析結果をテキスト化
            analysis_text = self._format_context_analysis_for_embedding(analysis_data)
            
            # Ollamaエンベディング生成
            response = self.ollama_client.embeddings(
                model=self.embedding_model_name,
                prompt=analysis_text
            )
            embedding = response['embedding']
            
            # メタデータ作成（報告書と区別するため）
            metadata = {
                'type': 'context_analysis',
                'project_id': project_id,
                'overall_status': analysis_data.get('overall_status', '不明'),
                'overall_risk': analysis_data.get('overall_risk', '不明'),
                'current_phase': analysis_data.get('current_phase', '不明'),
                'progress_trend': analysis_data.get('progress_trend', '不明'),
                'issue_continuity': analysis_data.get('issue_continuity', '不明'),
                'analysis_confidence': analysis_data.get('analysis_confidence', 0.0),
                'reports_count': analysis_data.get('reports_count', 0),
                'last_updated': analysis_data.get('last_updated', '')
            }
            
            # ベクターストアに追加
            doc_id = f"context_analysis_{project_id}"
            self.collection.upsert(  # upsertで既存データを更新
                embeddings=[embedding],
                documents=[analysis_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            logger.info(f"Context analysis added: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add context analysis for {project_id}: {e}")
            return False
    
    def _format_context_analysis_for_embedding(self, analysis_data: Dict[str, Any]) -> str:
        """統合分析結果をエンベディング用テキストに変換"""
        parts = []
        
        # 基本情報
        parts.append(f"案件ID: {analysis_data.get('project_id', '不明')}")
        parts.append(f"総合ステータス: {analysis_data.get('overall_status', '不明')}")
        parts.append(f"総合リスク: {analysis_data.get('overall_risk', '不明')}")
        parts.append(f"現在工程: {analysis_data.get('current_phase', '不明')}")
        parts.append(f"進捗傾向: {analysis_data.get('progress_trend', '不明')}")
        parts.append(f"問題継続性: {analysis_data.get('issue_continuity', '不明')}")
        
        # 分析サマリ
        if analysis_data.get('analysis_summary'):
            parts.append(f"分析サマリ: {analysis_data['analysis_summary']}")
        
        # 建設工程詳細
        construction_phases = analysis_data.get('construction_phases', {})
        if construction_phases:
            parts.append("建設工程状況:")
            for phase, info in construction_phases.items():
                if isinstance(info, dict):
                    status = info.get('status', '不明')
                    parts.append(f"  {phase}: {status}")
        
        # 遅延理由管理
        delay_reasons = analysis_data.get('delay_reasons_management', [])
        if delay_reasons:
            parts.append("遅延理由:")
            for reason in delay_reasons[:3]:  # 上位3件
                category = reason.get('delay_category', '')
                description = reason.get('description', '')
                status = reason.get('status', '')
                parts.append(f"  {category}: {description} (ステータス: {status})")
        
        # 推奨アクション
        actions = analysis_data.get('recommended_actions', [])
        if actions:
            parts.append(f"推奨アクション: {', '.join(actions[:3])}")
        
        return "\n".join(parts)
    
    def search_similar_documents(
        self, 
        query: str, 
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """類似文書を検索"""
        try:
            # コレクションの存在確認
            try:
                self.collection = self.client.get_collection(self.collection_name)
            except Exception:
                logger.warning(f"Collection {self.collection_name} not found")
                return []
            
            # クエリのエンベディングを生成
            # Ollamaクエリエンベディング生成
            response = self.ollama_client.embeddings(
                model=self.embedding_model_name,
                prompt=query
            )
            query_embedding = response['embedding']
            
            # 検索実行
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata
            )
            
            # 結果を整形
            search_results = []
            for i in range(len(results['documents'][0])):
                result = {
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else 0.0,
                    'id': results['ids'][0][i]
                }
                search_results.append(result)
            
            logger.info(f"Search completed: {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_document_count(self) -> int:
        """保存されている文書数を取得"""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0
    
    def delete_document(self, doc_id: str) -> bool:
        """文書を削除"""
        try:
            # doc_idで始まるすべてのチャンクを削除
            all_results = self.collection.get()
            ids_to_delete = [
                id for id in all_results['ids'] 
                if id.startswith(f"{doc_id}_chunk_")
            ]
            
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"Document deleted: {doc_id} ({len(ids_to_delete)} chunks)")
                return True
            else:
                logger.warning(f"Document not found: {doc_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    def clear_all_documents(self) -> bool:
        """すべての文書を削除"""
        try:
            # コレクションを削除して再作成
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "建設文書のベクターストア"}
            )
            logger.info("All documents cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear documents: {e}")
            return False