"""
バイナリキャッシュ読み込みユーティリティ
"""
import pickle
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from app.models.report import DocumentReport

logger = logging.getLogger(__name__)

class CacheLoader:
    """バイナリキャッシュ読み込み管理クラス"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
    
    def load_reports_parallel(self, processed_reports_dir: Path) -> List[DocumentReport]:
        """
        並列でバイナリキャッシュからレポートを読み込み
        
        Args:
            processed_reports_dir: 処理済みレポートディレクトリ
            
        Returns:
            List[DocumentReport]: 読み込まれたレポートリスト
        """
        start_time = time.time()
        
        # インデックスファイルから処理済みファイル一覧を取得
        index_file = processed_reports_dir / "index.json"
        if not index_file.exists():
            logger.warning(f"Index file not found: {index_file}")
            return []
        
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        successful_files = {k: v for k, v in index_data.get("processed_files", {}).items() 
                          if v.get("status") == "success"}
        
        logger.info(f"🔍 Found {len(successful_files)} processed files")
        
        # 並列読み込みの準備
        cache_files = []
        fallback_files = []
        
        for file_path, file_info in successful_files.items():
            cache_file_path = file_info.get("cache_file")
            json_file_path = file_info.get("result_file")
            
            if cache_file_path:
                cache_file = Path(cache_file_path)
                json_file = Path(json_file_path) if json_file_path else None
                
                if cache_file.exists():
                    # キャッシュファイルの新しさをチェック
                    if json_file and json_file.exists():
                        cache_mtime = cache_file.stat().st_mtime
                        json_mtime = json_file.stat().st_mtime
                        
                        if cache_mtime >= json_mtime:
                            cache_files.append(cache_file)
                        else:
                            # JSONの方が新しい場合はフォールバック
                            fallback_files.append((json_file, cache_file))
                            logger.debug(f"Cache outdated, using JSON: {json_file.name}")
                    else:
                        cache_files.append(cache_file)
                else:
                    # キャッシュファイルが存在しない場合はJSONから読み込み
                    if json_file and json_file.exists():
                        fallback_files.append((json_file, cache_file if cache_file_path else None))
                        logger.debug(f"Cache missing, using JSON: {json_file.name}")
        
        reports = []
        
        # 🚀 並列でバイナリキャッシュを読み込み
        if cache_files:
            cache_reports = self._load_cache_files_parallel(cache_files)
            reports.extend(cache_reports)
            logger.info(f"⚡ Loaded {len(cache_reports)} reports from binary cache")
        
        # 📄 フォールバック: JSONファイルから読み込み（必要に応じてキャッシュ生成）
        if fallback_files:
            fallback_reports = self._load_json_files_with_cache_generation(fallback_files)
            reports.extend(fallback_reports)
            logger.info(f"📄 Loaded {len(fallback_reports)} reports from JSON (with cache generation)")
        
        load_time = time.time() - start_time
        logger.info(f"🏁 Total load time: {load_time:.3f}秒 ({len(reports)} reports)")
        
        return reports
    
    def _load_cache_files_parallel(self, cache_files: List[Path]) -> List[DocumentReport]:
        """並列でバイナリキャッシュファイルを読み込み"""
        reports = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 全てのキャッシュファイルを並列で読み込み
            future_to_file = {
                executor.submit(self._load_single_cache_file, cache_file): cache_file
                for cache_file in cache_files
            }
            
            for future in as_completed(future_to_file):
                cache_file = future_to_file[future]
                try:
                    report = future.result()
                    if report:
                        reports.append(report)
                        logger.debug(f"✅ Cache loaded: {cache_file.name}")
                except Exception as e:
                    logger.error(f"❌ Failed to load cache {cache_file}: {e}")
        
        return reports
    
    def _load_single_cache_file(self, cache_file: Path) -> Optional[DocumentReport]:
        """単一のバイナリキャッシュファイルを読み込み（JSONフォールバック付き）"""
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Cache file corrupted: {cache_file.name}. Attempting JSON fallback...")
            
            # 破損したキャッシュファイルを削除
            try:
                cache_file.unlink(missing_ok=True)
                logger.debug(f"🗑️ Removed corrupted cache: {cache_file.name}")
            except Exception:
                pass
            
            # JSONファイルからフォールバック読み込み
            json_file = cache_file.with_suffix('.json')
            if json_file.exists():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    
                    report = self._deserialize_report(report_data)
                    if report:
                        # 新しいキャッシュを生成
                        try:
                            with open(cache_file, 'wb') as f:
                                pickle.dump(report, f)
                            logger.info(f"🔄 Regenerated cache from JSON: {cache_file.name}")
                        except Exception as cache_e:
                            logger.warning(f"Failed to regenerate cache {cache_file}: {cache_e}")
                        return report
                except Exception as json_e:
                    logger.error(f"❌ JSON fallback also failed for {json_file}: {json_e}")
            
            logger.error(f"❌ Complete failure to load {cache_file.name}")
            return None
    
    def _load_json_files_with_cache_generation(self, fallback_files: List[tuple]) -> List[DocumentReport]:
        """JSONファイルから読み込み、同時にキャッシュを生成"""
        reports = []
        
        for json_file, cache_file in fallback_files:
            try:
                # JSONファイルから読み込み
                with open(json_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                
                # DocumentReportオブジェクトに変換
                report = self._deserialize_report(report_data)
                if report:
                    reports.append(report)
                    
                    # バイナリキャッシュを生成（次回用）
                    if cache_file:
                        try:
                            cache_file.parent.mkdir(parents=True, exist_ok=True)
                            with open(cache_file, 'wb') as f:
                                pickle.dump(report, f)
                            logger.debug(f"💾 Generated cache: {cache_file.name}")
                        except Exception as e:
                            logger.warning(f"Failed to generate cache {cache_file}: {e}")
                
            except Exception as e:
                logger.error(f"Failed to load JSON file {json_file}: {e}")
        
        return reports
    
    def load_report_smart(self, json_path: Path) -> Optional[DocumentReport]:
        """JSONまたはバイナリキャッシュからレポートを読み込み、必要に応じてキャッシュを更新"""
        cache_path = json_path.with_suffix('.cache')
        
        # キャッシュが存在し、JSONより新しい場合、またはJSONが存在しない場合
        if cache_path.exists() and (not json_path.exists() or cache_path.stat().st_mtime >= json_path.stat().st_mtime):
            try:
                with open(cache_path, 'rb') as f:
                    report = pickle.load(f)
                logger.debug(f"⚡ Loaded from binary cache: {json_path.name}")
                return report
            except Exception as e:
                logger.warning(f"Failed to load from cache {cache_path}: {e}. Falling back to JSON.")
                # キャッシュが壊れている場合は削除してJSONから再生成
                cache_path.unlink(missing_ok=True)
        
        # JSONファイルから読み込み、キャッシュを生成
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                report = self._deserialize_report(data)
                
                if report:
                    try:
                        with open(cache_path, 'wb') as f:
                            pickle.dump(report, f)
                        logger.debug(f"💾 Generated new binary cache for: {json_path.name}")
                    except Exception as e:
                        logger.warning(f"Failed to save binary cache {cache_path}: {e}")
                return report
            except Exception as e:
                logger.error(f"Failed to load from JSON {json_path}: {e}")
        
        return None
    
    def _deserialize_report(self, data: Dict[str, Any]) -> Optional[DocumentReport]:
        """JSONデータからDocumentReportオブジェクトを復元"""
        try:
            from app.models.report import StatusFlag, RiskLevel, ConstructionStatus, AnalysisResult, AnomalyDetection, ReportType
            from datetime import datetime
            
            report = DocumentReport(
                file_path=data["file_path"],
                file_name=data["file_name"],
                report_type=ReportType(data["report_type"]) if data.get("report_type") else ReportType.PROGRESS_UPDATE,
                content=data.get("content", data.get("content_preview", "")),
                created_at=datetime.fromisoformat(data.get("processed_at", datetime.now().isoformat())),
                project_id=data.get("project_id")  # プロジェクトID復元
            )
            
            # AnalysisResult復元
            if data.get("analysis_result"):
                analysis = data["analysis_result"]
                report.analysis_result = AnalysisResult(
                    summary=analysis.get("summary", ""),
                    issues=analysis.get("issues", []),
                    key_points=analysis.get("key_points", "").split(",") if analysis.get("key_points") else [],
                    confidence=float(analysis.get("confidence", 0.0))
                )
            
            # AnomalyDetection復元（新構造）
            if data.get("anomaly_detection"):
                anomaly = data["anomaly_detection"]
                report.anomaly_detection = AnomalyDetection(
                    is_anomaly=bool(anomaly.get("is_anomaly", anomaly.get("has_anomaly", False))),  # 後方互換性
                    anomaly_description=anomaly.get("anomaly_description", anomaly.get("explanation", "")),  # 後方互換性
                    confidence=float(anomaly.get("confidence", 0.0)),
                    suggested_action=anomaly.get("suggested_action", ""),
                    requires_human_review=bool(anomaly.get("requires_human_review", False)),
                    similar_cases=anomaly.get("similar_cases", [])
                )
            
            # 新しいフラグ体系復元
            if data.get("status_flag"):
                report.status_flag = StatusFlag(data["status_flag"])
            # category_labels削除: 15カテゴリ遅延理由体系に統一
            if data.get("risk_level"):
                report.risk_level = RiskLevel(data["risk_level"])
            if data.get("construction_status"):
                report.construction_status = ConstructionStatus(data["construction_status"])
            
            # 🚨 データ品質監視フィールド復元
            report.has_unexpected_values = data.get("has_unexpected_values", False)
            report.validation_issues = data.get("validation_issues", [])
            
            # 🤖 統合分析結果フィールド復元
            report.requires_human_review = data.get("requires_human_review", False)
            report.analysis_confidence = data.get("analysis_confidence", 0.0)
            # analysis_notes削除: summaryに統合
            
            # 🔍 建設工程情報復元
            report.current_construction_phase = data.get("current_construction_phase")
            report.construction_progress = data.get("construction_progress")
            
            # 📋 プロジェクトマッピング詳細情報復元
            report.project_mapping_info = data.get("project_mapping_info")
            
            # 🚧 遅延理由情報復元（15カテゴリ体系）
            report.delay_reasons = data.get("delay_reasons", [])
            
            # 🎯 緊急度スコア復元
            report.urgency_score = data.get("urgency_score", 1)
            
            # current_status削除: status_flagで統一
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to deserialize report: {e}")
            return None