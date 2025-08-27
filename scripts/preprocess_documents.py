#!/usr/bin/env python3
"""
事前処理スクリプト: レポート投入時の処理を実行
使用方法: 
  python scripts/preprocess_documents.py [--provider ollama]
  python scripts/preprocess_documents.py --force  # 全データ削除して再処理
  python scripts/preprocess_documents.py --clear-summaries  # 報告書要約のみ削除
  python scripts/preprocess_documents.py --clear-integration  # 統合分析結果のみ削除
  python scripts/preprocess_documents.py --integration-only  # 統合分析のみ実行
"""
import sys
import os
import json
import pickle
import argparse
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStoreService
from app.services.project_context_analyzer import ProjectContextAnalyzer
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
        self.context_analyzer = ProjectContextAnalyzer()  # 🆕 統合分析サービス
        self.results_dir = project_root / "data" / "processed_reports"
        self.context_results_dir = project_root / "data" / "context_analysis"  # 🆕 統合分析結果保存
        self.index_file = self.results_dir / "index.json"
        
        # ディレクトリを作成
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.context_results_dir.mkdir(parents=True, exist_ok=True)
    
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
                        "has_anomaly": report.anomaly_detection.is_anomaly if report.anomaly_detection else False
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
        
        # ファイル作成時間順にソート（古いものから新しいものへ）
        return sorted(files, key=lambda f: f.stat().st_mtime)
    
    def _serialize_report(self, report) -> Dict[str, Any]:
        """レポートオブジェクトをシリアライズ"""
        return {
            "file_path": report.file_path,
            "file_name": report.file_name,
            "content": report.content,  # 全文を保存
            "content_preview": report.content[:200] + "..." if len(report.content) > 200 else report.content,  # プレビュー用（後方互換性）
            "report_type": report.report_type.value if report.report_type else None,
            
            # 🆕 元報告書の更新時間を明示的に保存
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "original_file_mtime": report.created_at.isoformat() if report.created_at else None,  # 明示的な名前
            
            # プロジェクトID（マルチ戦略マッピング）
            "project_id": getattr(report, 'project_id', None),
            "project_mapping_info": getattr(report, 'project_mapping_info', None),
            
            # 🎯 新フラグ体系のシリアライズ
            "status_flag": report.status_flag.value if report.status_flag else None,
            # "category_labels" 削除: 15カテゴリ遅延理由体系に統一
            "risk_level": report.risk_level.value if report.risk_level else None,
            
            # 🚨 データ品質監視フィールド
            "has_unexpected_values": getattr(report, 'has_unexpected_values', False),
            "validation_issues": getattr(report, 'validation_issues', []),
            
            # 🤖 統合分析結果フィールド
            "requires_human_review": getattr(report, 'requires_human_review', False),
            "analysis_confidence": getattr(report, 'analysis_confidence', 0.0),
            # "analysis_notes" 削除: summaryに統合
            
            # 🔍 建設工程情報
            "current_construction_phase": getattr(report, 'current_construction_phase', None),
            "construction_progress": getattr(report, 'construction_progress', None),
            
            # 🚧 遅延理由情報（15カテゴリ体系）
            "delay_reasons": getattr(report, 'delay_reasons', []),
            
            # 🎯 緊急度スコア
            "urgency_score": getattr(report, 'urgency_score', 1),
            
            # current_status削除: status_flagで統一
            
            "analysis_result": {
                "summary": report.analysis_result.summary if report.analysis_result else "",
                "issues": report.analysis_result.issues if report.analysis_result else [],
                "key_points": ",".join(report.analysis_result.key_points) if report.analysis_result and report.analysis_result.key_points else "",
                "confidence": report.analysis_result.confidence if report.analysis_result else 0.0
            } if report.analysis_result else None,
            "anomaly_detection": {
                "is_anomaly": report.anomaly_detection.is_anomaly if report.anomaly_detection else False,
                "anomaly_description": report.anomaly_detection.anomaly_description if report.anomaly_detection else "",
                "confidence": report.anomaly_detection.confidence if report.anomaly_detection else 0.0,
                "suggested_action": report.anomaly_detection.suggested_action if report.anomaly_detection else "",
                "requires_human_review": report.anomaly_detection.requires_human_review if report.anomaly_detection else False
            } if report.anomaly_detection else None,
            "processed_at": datetime.now().isoformat()
        }
    
    def run_context_analysis(self, reports: List[Any]) -> Dict[str, Any]:
        """統合分析を実行（最新報告書が追加された案件のみ）"""
        logger.info("🔄 統合分析を開始...")
        
        # プロジェクトIDごとにグループ化
        projects_map = {}
        for report in reports:
            project_id = getattr(report, 'project_id', None)
            if project_id and project_id != '不明':
                if project_id not in projects_map:
                    projects_map[project_id] = []
                projects_map[project_id].append(report)
        
        # 既存の統合分析結果を読み込み
        existing_analysis = self._load_existing_context_analysis()
        
        analysis_results = {}
        updated_projects = []
        
        for project_id, project_reports in projects_map.items():
            # 最新報告書の日付を確認
            latest_report_date = max(
                (r.created_at for r in project_reports if hasattr(r, 'created_at') and r.created_at),
                default=None
            )
            
            # 既存分析の最終更新日と比較
            existing_date = existing_analysis.get(project_id, {}).get('last_updated')
            should_update = True
            
            if existing_date and latest_report_date:
                try:
                    existing_datetime = datetime.fromisoformat(existing_date.replace('Z', '+00:00'))
                    should_update = latest_report_date > existing_datetime
                except:
                    should_update = True
            
            if should_update:
                logger.info(f"🔄 統合分析実行: {project_id} ({len(project_reports)}件の報告書)")
                
                try:
                    # DocumentReportオブジェクトに変換（必要に応じて）
                    document_reports = []
                    for report in project_reports:
                        if hasattr(report, 'report_type'):  # 既にDocumentReportオブジェクト
                            document_reports.append(report)
                        else:  # 辞書形式の場合は変換が必要
                            # ここでは既にDocumentReportオブジェクトと仮定
                            document_reports.append(report)
                    
                    # 統合分析実行
                    context_analysis = self.context_analyzer.analyze_project_context(project_id, document_reports)
                    
                    if context_analysis:
                        analysis_results[project_id] = {
                            'project_id': context_analysis.project_id,
                            'overall_status': context_analysis.overall_status.value,
                            'overall_risk': context_analysis.overall_risk.value,
                            'current_phase': context_analysis.current_phase,
                            'construction_phases': context_analysis.construction_phases,
                            'progress_trend': context_analysis.progress_trend,
                            'issue_continuity': context_analysis.issue_continuity,
                            'report_frequency': context_analysis.report_frequency,
                            'analysis_confidence': context_analysis.analysis_confidence,
                            'analysis_summary': context_analysis.analysis_summary,
                            'recommended_actions': context_analysis.recommended_actions,
                            'delay_reasons_management': context_analysis.delay_reasons_management,
                            'confidence_details': context_analysis.confidence_details,
                            'evidence_details': context_analysis.evidence_details,
                            'last_updated': datetime.now().isoformat(),
                            'reports_count': len(document_reports)
                        }
                        updated_projects.append(project_id)
                        logger.info(f"✅ 統合分析完了: {project_id}")
                    else:
                        logger.warning(f"⚠️ 統合分析失敗: {project_id}")
                        
                except Exception as e:
                    logger.error(f"❌ 統合分析エラー: {project_id} - {e}")
            else:
                logger.info(f"⏭️ 統合分析スキップ: {project_id} (最新)")
                # 既存の分析結果を保持
                analysis_results[project_id] = existing_analysis[project_id]
        
        # 統合分析結果を保存
        self._save_context_analysis(analysis_results)
        
        # 🆕 統合分析結果をベクターDBに保存
        self._save_context_analysis_to_vector_store(analysis_results, updated_projects)
        
        logger.info(f"🎉 統合分析完了: {len(updated_projects)}件更新, {len(analysis_results)}件総数")
        
        return {
            'total_projects': len(analysis_results),
            'updated_projects': len(updated_projects),
            'updated_project_ids': updated_projects
        }
    
    def _load_existing_context_analysis(self) -> Dict[str, Any]:
        """既存の統合分析結果を読み込み"""
        context_file = self.context_results_dir / "context_analysis.json"
        if context_file.exists():
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"統合分析結果の読み込み失敗: {e}")
        return {}
    
    def _save_context_analysis(self, analysis_results: Dict[str, Any]):
        """統合分析結果を保存"""
        context_file = self.context_results_dir / "context_analysis.json"
        try:
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_results, f, ensure_ascii=False, indent=2)
            logger.info(f"統合分析結果保存: {context_file}")
        except Exception as e:
            logger.error(f"統合分析結果保存失敗: {e}")
    
    def _save_context_analysis_to_vector_store(self, analysis_results: Dict[str, Any], updated_projects: List[str]):
        """統合分析結果をベクターDBに保存"""
        try:
            logger.info(f"🔄 統合分析結果をベクターDBに保存中...")
            
            success_count = 0
            for project_id in updated_projects:
                if project_id in analysis_results:
                    analysis_data = analysis_results[project_id]
                    if self.vector_store.add_context_analysis(project_id, analysis_data):
                        success_count += 1
                    else:
                        logger.warning(f"⚠️ ベクターDB保存失敗: {project_id}")
            
            logger.info(f"✅ 統合分析結果のベクターDB保存完了: {success_count}/{len(updated_projects)}件")
            
        except Exception as e:
            logger.error(f"❌ 統合分析結果のベクターDB保存でエラー: {e}")
    
    def load_all_processed_reports(self) -> List[Any]:
        """処理済みレポートを全て読み込み"""
        reports = []
        
        # バイナリキャッシュから読み込み
        binary_cache_file = self.results_dir / "processed_reports.pkl"
        if binary_cache_file.exists():
            try:
                with open(binary_cache_file, 'rb') as f:
                    reports = pickle.load(f)
                logger.info(f"バイナリキャッシュから{len(reports)}件のレポートを読み込み")
                return reports
            except Exception as e:
                logger.warning(f"バイナリキャッシュ読み込み失敗: {e}")
        
        # JSONファイルから読み込み（フォールバック）
        for json_file in self.results_dir.glob("*.json"):
            if json_file.name == "index.json":
                continue
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                    # 簡易的なオブジェクト作成（統合分析用）
                    from types import SimpleNamespace
                    report = SimpleNamespace(**report_data)
                    
                    # 🆕 元報告書の更新時間を正確に復元
                    # 1. まず明示的に保存された original_file_mtime を確認
                    if hasattr(report, 'original_file_mtime') and report.original_file_mtime:
                        try:
                            report.created_at = datetime.fromisoformat(report.original_file_mtime.replace('Z', '+00:00'))
                        except:
                            report.created_at = datetime.min
                    # 2. 次に created_at フィールドを確認
                    elif hasattr(report, 'created_at') and isinstance(report.created_at, str):
                        try:
                            report.created_at = datetime.fromisoformat(report.created_at.replace('Z', '+00:00'))
                        except:
                            report.created_at = datetime.min
                    # 3. どちらも存在しない場合はファイルの更新時間を使用（フォールバック）
                    elif not hasattr(report, 'created_at') or report.created_at is None:
                        try:
                            file_path = Path(report.file_path) if hasattr(report, 'file_path') else json_file
                            report.created_at = datetime.fromtimestamp(file_path.stat().st_mtime)
                            logger.info(f"Using file mtime as fallback for {report.file_name if hasattr(report, 'file_name') else 'unknown'}")
                        except:
                            report.created_at = datetime.min
                    
                    # その他の必要な属性を確保
                    if not hasattr(report, 'project_id'):
                        report.project_id = getattr(report, 'project_id', '不明')
                    if not hasattr(report, 'report_type'):
                        report.report_type = getattr(report, 'report_type', 'OTHER')
                    
                    reports.append(report)
            except Exception as e:
                logger.warning(f"レポート読み込み失敗: {json_file} - {e}")
        
        logger.info(f"JSONファイルから{len(reports)}件のレポートを読み込み")
        return reports


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
        "--integration-only",
        action="store_true",
        help="統合分析のみ実行する（報告書処理をスキップ）"
    )
    parser.add_argument(
        "--clear-summaries",
        action="store_true",
        help="報告書要約結果のみを削除する"
    )
    parser.add_argument(
        "--clear-integration",
        action="store_true",
        help="統合分析結果のみを削除する"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="詳細ログを表示"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 個別削除オプションの処理
    if args.clear_summaries:
        print("⚠️  --clear-summariesオプションが指定されました。")
        print("   報告書要約結果を削除します:")
        print("   - data/processed_reports/ (全ての処理済みファイル)")
        print("   - vector_store/ (全てのベクターデータ)")
        print()
        
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
        
        import shutil
        if processed_dir.exists():
            shutil.rmtree(processed_dir)
            print("🗑️  data/processed_reports/ を削除しました")
        if vector_dir.exists():
            shutil.rmtree(vector_dir)
            print("🗑️  vector_store/ を削除しました")
        print("✅ 報告書要約結果の削除が完了しました。")
        return 0
    
    if args.clear_integration:
        print("⚠️  --clear-integrationオプションが指定されました。")
        print("   統合分析結果を削除します:")
        print("   - data/context_analysis/ (全ての統合分析結果)")
        print()
        
        context_dir = Path("data/context_analysis")
        
        if context_dir.exists():
            file_count = len(list(context_dir.glob("*.json")))
            print(f"   📊 統合分析結果: {file_count}件")
        
        print()
        confirmation = input("続行しますか？ (y/N): ").strip().lower()
        if confirmation not in ['y', 'yes']:
            print("処理を中止しました。")
            return 0
        
        import shutil
        if context_dir.exists():
            shutil.rmtree(context_dir)
            print("🗑️  data/context_analysis/ を削除しました")
        print("✅ 統合分析結果の削除が完了しました。")
        return 0

    # --forceオプション使用時の確認
    if args.force and not args.file:
        print("⚠️  --forceオプションが指定されました。")
        print("   これにより以下のデータが削除されます:")
        print("   - data/processed_reports/ (全ての処理済みファイル)")
        print("   - data/context_analysis/ (全ての統合分析結果)")
        print("   - vector_store/ (全てのベクターデータ)")
        print("   - data/confirmed_mappings.json (確定済みマッピング)")
        print()
        
        # 削除対象の確認
        processed_dir = Path("data/processed_reports")
        context_dir = Path("data/context_analysis")
        vector_dir = Path("vector_store")
        confirmed_mappings_file = Path("data/confirmed_mappings.json")
        
        if processed_dir.exists():
            file_count = len(list(processed_dir.glob("*.json")))
            print(f"   📄 処理済みレポート: {file_count}件")
        
        if context_dir.exists():
            context_count = len(list(context_dir.glob("*.json")))
            print(f"   📊 統合分析結果: {context_count}件")
        
        if vector_dir.exists():
            vector_size = sum(f.stat().st_size for f in vector_dir.rglob('*') if f.is_file()) / (1024*1024)
            print(f"   🗂️  ベクターストア: {vector_size:.1f}MB")
        
        if confirmed_mappings_file.exists():
            print(f"   📋 確定済みマッピング: 存在")
        
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
        if context_dir.exists():
            shutil.rmtree(context_dir)
            print("🗑️  data/context_analysis/ を削除しました")
        if vector_dir.exists():
            shutil.rmtree(vector_dir)
            print("🗑️  vector_store/ を削除しました")
        if confirmed_mappings_file.exists():
            confirmed_mappings_file.unlink()
            print("🗑️  data/confirmed_mappings.json を削除しました")
        print()
    
    # 事前処理実行
    preprocessor = PreprocessingService(llm_provider=args.provider)
    
    if args.integration_only:
        # 統合分析のみ実行
        print("=== 統合分析のみ実行 ===")
        start_time = time.time()
        try:
            reports = preprocessor.load_all_processed_reports()
            context_result = preprocessor.run_context_analysis(reports)
            end_time = time.time()
            
            print("統合分析結果:")
            print(f"  総案件数: {context_result['total_projects']}")
            print(f"  更新案件数: {context_result['updated_projects']}")
            print(f"  処理時間: {end_time - start_time:.1f}秒")
            if context_result['updated_project_ids']:
                print(f"  更新案件ID: {', '.join(context_result['updated_project_ids'])}")
            
            return 0
        except Exception as e:
            print(f"❌ 統合分析でエラーが発生しました: {e}")
            return 1
    elif args.file:
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
        
        # 🆕 統合分析実行（全ファイル処理の場合のみ）
        if result.get('successful', 0) > 0:
            print(f"\n=== 統合分析実行 ===")
            try:
                # 処理済みレポートを読み込み
                reports = preprocessor.load_all_processed_reports()
                context_result = preprocessor.run_context_analysis(reports)
                
                print(f"統合分析結果:")
                print(f"  総案件数: {context_result['total_projects']}")
                print(f"  更新案件数: {context_result['updated_projects']}")
                if context_result['updated_project_ids']:
                    print(f"  更新案件ID: {', '.join(context_result['updated_project_ids'])}")
                
                result['context_analysis'] = context_result
                
            except Exception as e:
                print(f"⚠️ 統合分析でエラーが発生しました: {e}")
                result['context_analysis_error'] = str(e)
    
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