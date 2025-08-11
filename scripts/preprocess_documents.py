#!/usr/bin/env python3
"""
事前処理スクリプト: レポート投入時の処理を実行
使用方法: python scripts/preprocess_documents.py [--provider ollama]
"""
import sys
import os
import json
import pickle
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStoreService
from app.config.settings import SHAREPOINT_DOCS_DIR

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PreprocessingService:
    """事前処理サービス"""
    
    def __init__(self, llm_provider: str = "ollama"):
        self.document_processor = DocumentProcessor(llm_provider=llm_provider, create_vector_store=True)
        self.vector_store = VectorStoreService(create_mode=True)
        self.results_dir = project_root / "data" / "processed_reports"
        self.index_file = self.results_dir / "index.json"
        
        # ディレクトリを作成
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_index(self) -> Dict[str, Any]:
        """処理済みファイルのインデックスを読み込み"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"processed_files": {}, "last_updated": datetime.now().isoformat(), "version": "1.0"}
    
    def _save_index(self, index: Dict[str, Any]):
        """インデックスを保存"""
        index["last_updated"] = datetime.now().isoformat()
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    
    def _get_file_hash(self, file_path: Path) -> str:
        """ファイルのハッシュ値を計算（変更検出用）"""
        import hashlib
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _is_file_processed(self, file_path: Path, index: Dict[str, Any]) -> bool:
        """ファイルが処理済みかチェック"""
        file_key = str(file_path.relative_to(project_root))
        if file_key not in index["processed_files"]:
            return False
        
        # ファイルの変更をハッシュで検出
        current_hash = self._get_file_hash(file_path)
        stored_info = index["processed_files"][file_key]
        return stored_info.get("file_hash") == current_hash
    
    def process_single_file(self, file_path: Path, force: bool = False) -> Dict[str, Any]:
        """単一ファイルの事前処理"""
        index = self._load_index()
        file_key = str(file_path.relative_to(project_root))
        
        # 処理済みチェック
        if not force and self._is_file_processed(file_path, index):
            logger.info(f"⏭️ スキップ（処理済み）: {file_path.name}")
            return {"status": "skipped", "reason": "already_processed"}
        
        try:
            logger.info(f"🔄 処理中: {file_path.name}")
            start_time = datetime.now()
            
            # ドキュメント処理
            report = self.document_processor.process_single_document(file_path)
            
            if report:
                # ベクターストアに追加
                self.vector_store.add_document(
                    content=report.content,
                    metadata={
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "report_type": report.report_type.value if report.report_type else "unknown",
                        "processed_at": datetime.now().isoformat(),
                        "flags": ",".join([flag.value for flag in report.flags]) if report.flags else "",
                        "risk_level": report.risk_level.value if report.risk_level else "低",
                        "has_anomaly": report.anomaly_detection.has_anomaly if report.anomaly_detection else False
                    }
                )
                
                # 個別ファイルとして結果保存
                result_data = self._serialize_report(report)
                result_file = self.results_dir / f"{file_path.stem}.json"
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                
                # 🚀 バイナリキャッシュファイル生成（高速読み込み用）
                cache_file = self.results_dir / f"{file_path.stem}.cache"
                try:
                    with open(cache_file, 'wb') as f:
                        pickle.dump(report, f)
                    logger.debug(f"💾 Binary cache saved: {cache_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to save binary cache {cache_file}: {e}")
                
                # インデックス更新
                processing_time = (datetime.now() - start_time).total_seconds()
                index["processed_files"][file_key] = {
                    "file_hash": self._get_file_hash(file_path),
                    "processed_at": datetime.now().isoformat(),
                    "processing_time": processing_time,
                    "result_file": str(result_file.relative_to(project_root)),
                    "cache_file": str(cache_file.relative_to(project_root)),
                    "status": "success"
                }
                self._save_index(index)
                
                logger.info(f"✅ 処理完了: {file_path.name} ({processing_time:.1f}秒)")
                return {"status": "success", "processing_time": processing_time}
            else:
                raise Exception("Document processing failed")
                
        except Exception as e:
            # エラー情報をインデックスに記録
            index["processed_files"][file_key] = {
                "file_hash": self._get_file_hash(file_path),
                "processed_at": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
            self._save_index(index)
            
            logger.error(f"❌ エラー: {file_path.name} - {str(e)}")
            return {"status": "error", "error": str(e)}
        
    def process_all_documents(self, force: bool = False) -> Dict[str, Any]:
        """全ドキュメントの事前処理を実行"""
        logger.info("事前処理を開始します...")
        start_time = datetime.now()
        
        # SharePointドキュメントフォルダから全ファイルを取得
        doc_files = self._get_all_document_files()
        logger.info(f"処理対象ファイル数: {len(doc_files)}")
        
        successful = 0
        skipped = 0
        failed = 0
        errors = []
        
        for file_path in doc_files:
            result = self.process_single_file(file_path, force=force)
            
            if result["status"] == "success":
                successful += 1
            elif result["status"] == "skipped":
                skipped += 1
            else:
                failed += 1
                errors.append(f"{file_path.name}: {result.get('error', 'Unknown error')}")
        
        # サマリー結果
        processing_result = {
            "processed_at": datetime.now().isoformat(),
            "total_files": len(doc_files),
            "successful": successful,
            "skipped": skipped,
            "failed": failed,
            "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
            "errors": errors
        }
        
        # サマリーログ出力
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"""
=== 事前処理完了 ===
処理時間: {duration.total_seconds():.1f}秒
成功: {successful}件
スキップ: {skipped}件
失敗: {failed}件
結果保存先: {self.results_dir}
        """)
        
        return processing_result
    
    def _get_all_document_files(self) -> List[Path]:
        """SharePointドキュメントフォルダから全ファイルを取得"""
        doc_dir = Path(SHAREPOINT_DOCS_DIR)
        if not doc_dir.exists():
            logger.warning(f"ドキュメントディレクトリが存在しません: {doc_dir}")
            return []
        
        # サポートする拡張子
        supported_extensions = {'.txt', '.pdf', '.docx', '.xlsx'}
        files = []
        
        for ext in supported_extensions:
            files.extend(doc_dir.rglob(f"*{ext}"))
        
        return sorted(files)
    
    def _serialize_report(self, report) -> Dict[str, Any]:
        """レポートオブジェクトをシリアライズ"""
        return {
            "file_path": report.file_path,
            "file_name": report.file_name,
            "content_preview": report.content[:200] + "..." if len(report.content) > 200 else report.content,
            "report_type": report.report_type.value if report.report_type else None,
            
            # プロジェクトID（マルチ戦略マッピング）
            "project_id": getattr(report, 'project_id', None),
            "project_mapping_info": getattr(report, 'project_mapping_info', None),
            
            # 🎯 新フラグ体系のシリアライズ
            "status_flag": report.status_flag.value if report.status_flag else None,
            "category_labels": [cat.value for cat in report.category_labels] if report.category_labels else None,
            "risk_level": report.risk_level.value if report.risk_level else None,
            
            # 🚨 データ品質監視フィールド
            "has_unexpected_values": getattr(report, 'has_unexpected_values', False),
            "validation_issues": getattr(report, 'validation_issues', []),
            
            # 🤖 統合分析結果フィールド
            "requires_human_review": getattr(report, 'requires_human_review', False),
            "analysis_confidence": getattr(report, 'analysis_confidence', 0.0),
            "analysis_notes": getattr(report, 'analysis_notes', None),
            
            # 🔍 建設工程情報
            "current_construction_phase": getattr(report, 'current_construction_phase', None),
            "construction_progress": getattr(report, 'construction_progress', None),
            
            "analysis_result": {
                "key_points": ",".join(report.analysis_result.key_points) if report.analysis_result and report.analysis_result.key_points else "",
                "recommended_flags": ",".join(report.analysis_result.recommended_flags) if report.analysis_result and report.analysis_result.recommended_flags else "",
                "confidence": report.analysis_result.confidence if report.analysis_result else 0.0
            } if report.analysis_result else None,
            "anomaly_detection": {
                "has_anomaly": report.anomaly_detection.has_anomaly if report.anomaly_detection else False,
                "anomaly_score": report.anomaly_detection.anomaly_score if report.anomaly_detection else 0.0,
                "explanation": report.anomaly_detection.explanation if report.anomaly_detection else ""
            } if report.anomaly_detection else None,
            "processed_at": datetime.now().isoformat()
        }
    


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="ドキュメント事前処理スクリプト")
    parser.add_argument(
        "--provider", 
        choices=["ollama", "openai", "anthropic"],
        default="ollama",
        help="使用するLLMプロバイダー (デフォルト: ollama)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="処理済みファイルも再処理する"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="特定のファイルのみ処理する（ファイル名指定）"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="詳細ログを表示"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # --forceオプション使用時の確認
    if args.force and not args.file:
        print("⚠️  --forceオプションが指定されました。")
        print("   これにより以下のデータが削除されます:")
        print("   - data/processed_reports/ (全ての処理済みファイル)")
        print("   - vector_store/ (全てのベクターデータ)")
        print()
        
        # 削除対象の確認
        processed_dir = Path("data/processed_reports")
        vector_dir = Path("vector_store")
        
        if processed_dir.exists():
            file_count = len(list(processed_dir.glob("*.json")))
            print(f"   📄 処理済みレポート: {file_count}件")
        
        if vector_dir.exists():
            vector_size = sum(f.stat().st_size for f in vector_dir.rglob('*') if f.is_file()) / (1024*1024)
            print(f"   🗂️  ベクターストア: {vector_size:.1f}MB")
        
        print()
        confirmation = input("続行しますか？ (y/N): ").strip().lower()
        if confirmation not in ['y', 'yes']:
            print("処理を中止しました。")
            return 0
        
        # データ削除実行
        import shutil
        if processed_dir.exists():
            shutil.rmtree(processed_dir)
            print("🗑️  data/processed_reports/ を削除しました")
        if vector_dir.exists():
            shutil.rmtree(vector_dir)
            print("🗑️  vector_store/ を削除しました")
        print()
    
    # 事前処理実行
    preprocessor = PreprocessingService(llm_provider=args.provider)
    
    if args.file:
        # 特定ファイルのみ処理
        file_path = Path(SHAREPOINT_DOCS_DIR).rglob(args.file)
        file_path = next(file_path, None)
        if file_path:
            result = preprocessor.process_single_file(file_path, force=args.force)
            print(f"ファイル処理結果: {result}")
        else:
            print(f"ファイルが見つかりません: {args.file}")
            return 1
    else:
        # 全ファイル処理
        result = preprocessor.process_all_documents(force=args.force)
    
    # 結果サマリー表示
    print(f"\n=== 事前処理結果 ===")
    
    if args.file:
        # 単一ファイル処理の場合
        print(f"ファイル: {args.file}")
        print(f"処理結果: {result.get('status', 'unknown')}")
        if 'processing_time' in result:
            print(f"処理時間: {result['processing_time']:.1f}秒")
    else:
        # 全ファイル処理の場合
        print(f"総ファイル数: {result['total_files']}")
        print(f"成功: {result['successful']}")
        print(f"スキップ: {result.get('skipped', 0)}")
        print(f"失敗: {result['failed']}")
        print(f"処理時間: {result['processing_time_seconds']:.1f}秒")
    
    if result.get('errors'):
        print(f"\nエラー:")
        for error in result['errors']:
            print(f"  - {error}")
    
    # 終了コード（失敗があった場合は1、成功の場合は0）
    if args.file:
        # 単一ファイル処理の場合
        return 0 if result.get('status') != 'error' else 1
    else:
        # 全ファイル処理の場合
        return 0 if result.get('failed', 0) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())