# 事前処理スクリプト

## 概要

建設管理システムの事前処理を実行するスクリプト群です。SharePointに保存された各種レポートを分析し、LLMによる自動分類・リスク評価・ベクター化を行います。

## 現在の実装

### `preprocess_documents.py`

```bash
# 基本実行
python scripts/preprocess_documents.py

# オプション
python scripts/preprocess_documents.py --provider ollama --force --verbose
python scripts/preprocess_documents.py --file report_001.txt
```

**主な機能:**
- SharePointドキュメントの読み込み・解析
- LLMによる自動分類（ステータス・カテゴリ・リスクレベル）
- 異常検知・品質監視
- ChromaDBベクター化
- ファイル単位の増分処理

## 将来の実装TODO

### 🎯 フェーズ1: ルールベースプロジェクトマッピング

**目標:** ファイル名・内容解析による自動プロジェクト推論

**実装項目:**
- [ ] ファイル名パターン認識エンジン
  ```python
  def extract_project_id_from_filename(filename: str) -> Optional[str]:
      # report_001_xxx → TKY-2024-001 の推論
      # 命名規則パターンマッチング
  ```

- [ ] 内容からプロジェクト情報抽出
  ```python
  def extract_project_info_from_content(content: str) -> ProjectInfo:
      # 工事番号・場所・担当者の自動抽出
      # 既存プロジェクトマスターとのマッチング
  ```

- [ ] 信頼度スコア算出
  ```python
  def calculate_mapping_confidence(report: DocumentReport, project_id: str) -> float:
      # 複数要素での信頼度計算
      # 閾値による自動/手動判定
  ```

### 🤖 フェーズ2: LLM強化マッピング

**目標:** 高精度なプロジェクト推論システム

**実装項目:**
- [ ] LLMプロジェクト推論プロンプト
  ```python
  PROJECT_INFERENCE_PROMPT = """
  以下のレポートがどの建設プロジェクトに属するか推論してください：
  - ファイル名: {filename}
  - 内容抜粋: {content_preview}
  - 利用可能プロジェクト: {available_projects}
  
  信頼度と共に回答してください。
  """
  ```

- [ ] マルチ候補推論システム
  ```python
  def llm_infer_project_candidates(report: DocumentReport) -> List[ProjectCandidate]:
      # 複数候補 + 信頼度スコア
      # 不確実性の明示
  ```

- [ ] 推論結果の品質評価
  ```python
  def evaluate_mapping_quality(predictions: List, ground_truth: List) -> QualityMetrics:
      # 精度・再現率・F1スコア
      # 継続的な品質向上
  ```

### 🔄 フェーズ3: 動的マッピング更新システム

**目標:** 実運用での自動マッピング管理

**実装項目:**
- [ ] 建設マスター連携
  ```python
  def sync_with_master_projects() -> List[Project]:
      # 外部DBとの同期
      # 新規プロジェクト自動検知
  ```

- [ ] 動的マッピングデータ更新
  ```python
  def update_project_mapping(report: DocumentReport, mapping_result: MappingResult):
      # project_reports_mapping.json の動的更新
      # 履歴管理・バージョン管理
  ```

- [ ] 人間確認ワークフロー
  ```python
  def handle_low_confidence_mapping(report: DocumentReport, candidates: List):
      # 確認待ちキュー管理
      # フィードバック学習システム
  ```

### 📊 フェーズ4: 継続学習・最適化

**目標:** 運用データによる継続的改善

**実装項目:**
- [ ] フィードバック学習システム
  ```python
  def learn_from_human_feedback(corrections: List[MappingCorrection]):
      # 人間修正データの学習
      # パターン認識精度向上
  ```

- [ ] A/Bテスト・性能比較
  ```python
  def compare_mapping_strategies(strategy_a: MappingStrategy, strategy_b: MappingStrategy):
      # ルールベース vs LLM比較
      # 最適戦略の自動選択
  ```

- [ ] リアルタイム更新対応
  ```python
  def real_time_processing_pipeline():
      # SharePoint変更検知
      # 即座の事前処理・マッピング更新
  ```

## データ構造設計

### 現在のマッピングファイル

```json
// data/sample_construction_data/project_reports_mapping.json
{
  "project_id": "TKY-2024-001",
  "project_name": "東京都品川区アンテナ基地局建設",
  "reports": [
    {
      "file_name": "report_001.txt",
      "report_date": "2024-12-15",
      "is_latest": true
    }
  ]
}
```

### 将来のマッピングファイル

```json
// 信頼度・メタデータ付き
{
  "project_id": "TKY-2024-001",
  "reports": [
    {
      "file_name": "report_001.txt",
      "confidence_score": 0.95,
      "mapping_method": "llm_inference",
      "mapped_at": "2024-12-20T10:30:00",
      "verified_by_human": false,
      "inference_details": {
        "primary_evidence": ["工事番号TKY-2024-001", "品川区"],
        "alternative_candidates": []
      }
    }
  ],
  "pending_review": [
    {
      "file_name": "report_unclear.txt",
      "candidates": [
        {"project_id": "TKY-2024-001", "confidence": 0.4},
        {"project_id": "TKY-2024-002", "confidence": 0.3}
      ],
      "needs_human_review": true,
      "review_priority": "medium"
    }
  ]
}
```

## 実装優先度

| フェーズ | 優先度 | 期間目安 | 主な目的 |
|---------|--------|----------|----------|
| フェーズ1 | 高 | 2-3週間 | 基本的な自動推論 |
| フェーズ2 | 中 | 4-6週間 | 高精度化・LLM活用 |
| フェーズ3 | 中 | 2-3ヶ月 | 実運用対応 |
| フェーズ4 | 低 | 継続的 | 継続改善 |

## 関連ファイル

- `app/services/project_aggregator.py` - プロジェクト集約ロジック
- `data/sample_construction_data/project_reports_mapping.json` - マッピングデータ
- `app/ui/project_dashboard.py` - プロジェクト中心ダッシュボード

## 注意事項

- 現在は理想的なマッピングファイルを使用（デモ・説明用）
- 実運用では自動推論システムが必要
- 段階的実装により徐々に自動化率を向上
- 人間確認フローの確保が重要