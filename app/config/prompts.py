"""
LLM用プロンプトテンプレート
"""

# システムプロンプト（建設業界特化）
SYSTEM_PROMPT = """あなたは建設工程管理のエキスパートです。以下の専門知識を持っています：

## 建設業界用語の理解
- 「工事開始」= プロジェクトの正式開始
- 「設置交渉」= 建設地での住民・関係者との交渉
- 「内諾」= 建設許可の事前同意
- 「免許申請」= 無線局免許申請
- 「理事会NG」= 集合住宅での建設反対
- 「auRora」= 建設管理システム
- 「Synapse」= 統合管理プラットフォーム

## あなたの役割
1. 建設工程レポートから重要な情報を抽出
2. トラブルや異常事象を適切に分類
3. リスクレベルの判定
4. 関係者への報告内容の要約

## 新しいフラグ体系

### 状態フラグ（現在の状況）
- 🔴 stopped: 停止 - 緊急停止、住民反対等
- 🟠 delay_risk_high: 遅延リスク高 - 重大な遅延懸念
- 🟡 delay_risk_low: 遅延リスク低 - 軽微な遅延懸念
- 🟢 normal: 順調 - 正常な進捗

### 原因カテゴリ（建設業界包括分類）
- 🔧 technical: 技術課題 - 設計変更、工法問題、機器故障、地盤改良
- 📋 administrative: 行政手続き - 免許申請、許可待ち、承認遅延
- 🏘️ stakeholder: 関係者調整 - 住民反対、理事会NG、近隣問題
- 💰 financial: 予算・契約 - 予算超過、契約変更、コスト問題
- 🌤️ environmental: 環境・外的 - 天候、地盤条件、アクセス、災害
- ⚖️ legal: 法的問題 - 契約紛争、法令変更、責任分担
- ❓ requires_review: 要人間確認 - 内容不明、分類困難
- ⚠️ other: その他明確原因 - 上記以外の特定可能問題

### リスクレベル
- 🔴 高: 緊急対応必要
- 🟡 中: 注意が必要
- 🟢 低: 軽微な課題

常に建設業界の文脈を理解し、正確で実用的な分析を提供してください。"""

# 統合文書分析プロンプト（レポートタイプ判定 + メイン分析 + 分類困難検知）
DOCUMENT_ANALYSIS_PROMPT = """以下の建設関連文書を包括的に分析し、重要な情報を抽出してください：

文書内容:
{document_content}

## 分析観点
1. **レポートタイプ判定**: 文書の種類を特定
2. **プロジェクト情報**: 工事番号、場所、担当者の抽出
3. **現在の状況**: 工程の進捗状況
4. **建設工程**: 現在のフェーズと各工程の進捗状況
5. **問題・トラブル**: 発生している課題
6. **リスクレベル**: 緊急度・重要度の判定
7. **状態・カテゴリ分類**: 適切なフラグの割り当て
8. **分析困難度**: LLMによる分類の確実性評価
9. **要約**: 管理者向けの短い要約

## レポートタイプの定義
- **TROUBLE_REPORT**: 緊急事態、重大トラブル、予期しない問題の報告
- **PROGRESS_UPDATE**: 定期的な進捗状況、状況変化の報告
- **CONSTRUCTION_REPORT**: 作業実績、技術的な工程状況の報告
- **OTHER**: 上記に該当しない文書

## 状態フラグ（必須選択）
- **stopped**: 停止 - 緊急停止、住民反対等で工事が完全に停止
- **delay_risk_high**: 遅延リスク高 - 重大な遅延懸念、大きな問題発生
- **delay_risk_low**: 遅延リスク低 - 軽微な遅延懸念、小さな問題
- **normal**: 順調 - 正常な進捗、問題なし

## 原因カテゴリ（複数選択可）
- **technical**: 技術課題 - 設計変更、工法問題、機器故障、地盤改良
- **administrative**: 行政手続き - 免許申請、許可待ち、承認遅延
- **stakeholder**: 関係者調整 - 住民反対、理事会NG、近隣問題
- **financial**: 予算・契約 - 予算超過、契約変更、コスト問題
- **environmental**: 環境・外的 - 天候、地盤条件、アクセス、災害
- **legal**: 法的問題 - 契約紛争、法令変更、責任分担
- **requires_review**: 要人間確認 - 内容不明、分類困難（**LLMが判断困難な場合のみ使用**）
- **other**: その他明確原因 - 上記以外の特定可能問題

以下のJSON形式で**必ず**全項目を回答してください：
```json
{{{{
  "report_type": "TROUBLE_REPORT/PROGRESS_UPDATE/CONSTRUCTION_REPORT/OTHER",
  "project_info": {{{{
    "project_id": "プロジェクトID（文書から抽出、不明な場合は\"不明\"）",
    "location": "場所（文書から抽出、不明な場合は\"不明\"）",
    "responsible_person": "担当者（文書から抽出、不明な場合は\"不明\"）"
  }}}},
  "status": "現在の状況の説明文",
  "issues": ["問題1", "問題2"],
  "risk_level": "低/中/高",
  "status_flag": "stopped/delay_risk_high/delay_risk_low/normal",
  "category_labels": ["technical", "administrative", "stakeholder", "financial", "environmental", "legal", "requires_review", "other"],
  "current_construction_phase": "工事開始/設置交渉/内諾/免許申請/工事実施/完了（文書から推定される現在の建設工程フェーズ）",
  "construction_progress": {{{{
    "工事開始": "完了/進行中/未着手",
    "設置交渉": "完了/進行中/未着手", 
    "内諾": "完了/進行中/未着手",
    "免許申請": "完了/進行中/未着手",
    "工事実施": "完了/進行中/未着手"
  }}}},
  "requires_human_review": false,
  "analysis_confidence": 0.85,
  "analysis_notes": "LLMによる分析の備考・留意点",
  "summary": "管理者向け要約",
  "urgency_score": 5,
  "key_points": ["重要ポイント1", "重要ポイント2"]
}}}}
```

## 重要な指針
1. **report_type**, **status_flag**, **category_labels** は必須項目です
2. **requires_human_review** は、LLMが分類に確信を持てない場合のみ true にしてください
3. **analysis_confidence** は 0.0-1.0 の範囲で分析の確実性を示してください
4. 不明な項目は "不明" と明記し、推測は避けてください
5. **category_labels** で "requires_review" を選択した場合は、必ず **requires_human_review** を true にしてください"""

# Few-shot例文
FEW_SHOT_EXAMPLES = """
## 分析例1:
入力: "マンション理事会から強い反対意見が出され、工事開始が延期となりました"
出力: 
```json
{
  "recommended_flags": ["emergency_stop"],
  "risk_level": "高",
  "urgency_score": 8,
  "summary": "住民反対による工事停止、早急な対応が必要"
}
```

## 分析例2:
入力: "地下で想定外の岩盤層を発見、特殊機械が必要で3週間延長"
出力:
```json
{
  "recommended_flags": ["technical_issue", "delay_risk"],
  "risk_level": "中",
  "urgency_score": 6,
  "summary": "地盤条件変更による工期延長、追加コスト発生"
}
```

## 分析例3:
入力: "設備から異音と煙が発生、消防署に通報、火災には至らず"
出力:
```json
{
  "recommended_flags": ["emergency_stop"],
      "risk_level": "高", 
  "urgency_score": 10,
  "summary": "設備重大不具合、安全上の緊急事態"
}
```
"""

# 質問応答プロンプト
QA_PROMPT = """建設工程に関する質問に対して、提供された文書情報を基に回答してください。

質問: {question}

関連文書:
{context}

以下の形式で回答してください：
1. **回答**: 質問への直接的な回答
2. **根拠**: 回答の根拠となる文書情報
3. **追加情報**: 関連する重要な補足情報
4. **推奨対応**: 必要に応じた推奨対応策

建設業界の専門知識を活用し、実用的で具体的な回答を提供してください。"""