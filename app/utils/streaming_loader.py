import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.utils.cache_loader import CacheLoader
from app.models.report import DocumentReport

logger = logging.getLogger(__name__)

class StreamingLoader:
    """ストリーミング読み込みローダー（プログレス表示対応）"""
    
    def __init__(self, max_workers: int = 3, batch_size: int = 5):
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.cache_loader = CacheLoader(max_workers=max_workers)
    
    def load_reports_streaming(self, processed_reports_dir: Path) -> Iterator[Tuple[int, int, List[DocumentReport]]]:
        """
        ストリーミング形式でレポートを読み込み
        
        Yields:
            Tuple[current_count, total_count, batch_reports]
            - current_count: 現在読み込み済み件数
            - total_count: 総件数
            - batch_reports: 今回のバッチで読み込まれたレポート
        """
        index_file = processed_reports_dir / "index.json"
        if not index_file.exists():
            logger.warning(f"Index file not found: {index_file}")
            yield (0, 0, [])
            return
        
        # インデックスファイル読み込み
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        # 成功した処理済みファイルのリストを取得
        successful_files = []
        for file_key, file_info in index_data.get("processed_files", {}).items():
            if file_info.get("status") == "success":
                json_path = Path(file_info["result_file"])
                cache_path = Path(file_info.get("cache_file", "")) if file_info.get("cache_file") else json_path.with_suffix('.cache')
                if json_path.exists():
                    successful_files.append((json_path, cache_path))
        
        total_count = len(successful_files)
        current_count = 0
        
        if total_count == 0:
            logger.info("No successful processed reports to load.")
            yield (0, 0, [])
            return
        
        # バッチ単位で並列読み込み
        for i in range(0, total_count, self.batch_size):
            batch_files = successful_files[i:i + self.batch_size]
            batch_reports = []
            
            # バッチ内で並列読み込み
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(batch_files))) as executor:
                futures = {
                    executor.submit(self._load_single_report, json_path, cache_path): (json_path, cache_path)
                    for json_path, cache_path in batch_files
                }
                
                for future in as_completed(futures):
                    json_path, cache_path = futures[future]
                    try:
                        report = future.result()
                        if report:
                            batch_reports.append(report)
                            current_count += 1
                        else:
                            current_count += 1  # 失敗もカウント
                    except Exception as e:
                        logger.error(f"Error loading report {json_path.name}: {e}")
                        current_count += 1  # 失敗もカウント
            
            # 進捗を返す（小さな遅延でプログレス表示を見やすくする）
            time.sleep(0.1)  # 100ms遅延でユーザーがプログレスを確認できる
            yield (current_count, total_count, batch_reports)
    
    def _load_single_report(self, json_path: Path, cache_path: Path) -> Optional[DocumentReport]:
        """単一レポートを読み込み（キャッシュ優先、JSONフォールバック）"""
        return self.cache_loader.load_report_smart(json_path)