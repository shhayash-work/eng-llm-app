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

常に建設業界の文脈を理解し、正確で実用的な分析を提供してください。"""

# 統合文書分析プロンプト（レポートタイプ判定 + メイン分析 + 分類困難検知）
DOCUMENT_ANALYSIS_PROMPT = """以下の建設関連文書を包括的に分析し、重要な情報を抽出してください：

文書内容:
{document_content}

## 分析観点
1. **レポートタイプ判定**: 文書の種類を特定
2. **プロジェクト情報**: 工事番号、場所、担当者の抽出
3. **現在の状況**: 工程の進捗状況
4. **問題・トラブル**: 発生している課題
5. **リスクレベル**: 緊急度・重要度の判定
6. **状態・カテゴリ分類**: 適切なフラグの割り当て
7. **分析困難度**: LLMによる分類の確実性評価
8. **要約**: 管理者向けの短い要約

## レポートタイプの定義
- **TROUBLE_REPORT**: 緊急事態、重大トラブル、予期しない問題の報告
- **PROGRESS_UPDATE**: 定期的な進捗状況、状況変化の報告
- **CONSTRUCTION_REPORT**: 作業実績、技術的な工程状況の報告
- **CONSTRUCTION_ESTIMATE**: 工事見積書、パッケージ化見積書
- **NEGOTIATION_PROGRESS**: 交渉経緯報告書、置局物件交渉経緯報告書
- **STRUCTURAL_DESIGN**: 強度計算結果報告書、構造設計関連文書
- **OTHER**: 上記に該当しない文書

## 状態フラグ（現時点の客観的状況、必須選択）
- **停止**: 停止・中断している状態
- **重大な遅延**: 重大な遅延（数か月・数年規模）が発生している状態
- **軽微な遅延**: 軽微な遅延（数日・数週間規模）が発生している状態
- **順調**: 正常な進捗・問題なし


## 遅延理由体系（delay_reasons）
文書内で遅延が言及されている場合、以下の体系で分類してください：

### 工程ミス
- **前工程からの情報連絡ミス**: 前工程からの情報連絡に不備があった
- **前工程の情報不備**: 前工程で提供される情報に不備があった  
- **前工程の遅れ**: 前工程の完了が遅れた
- **自工程のオーバーフロー**: 自工程で処理能力を超過した
- **自工程の対応漏れ**: 自工程で必要な対応が漏れた

### 要件漏れ
- **要件変更**: 要件が変更された
- **MO発行漏れ**: MO（業務指示書）の発行が漏れた
- **連絡不備**: 必要な連絡に不備があった

### 無線機不具合
- **エリア検討書_KDDI発改版の発生**: エリア検討書でKDDI発改版が発生した
- **無線機設定と回線設定の食違い発生**: 無線機設定と回線設定に食い違いが発生した

### 物件不具合  
- **候補物件が見つからない**: 適切な候補物件が見つからない
- **候補物件が基準を満たさない**: 候補物件が必要な基準を満たさない

### 設計不足
- **物品不足（物品発注不足）**: 必要な物品の発注が不足した
- **物品不足（納品遅れ）**: 物品の納品が遅れた

### 電源遅延
- **受電遅延**: 電源の受電が遅延した

### 回線不具合
- **回線が提供不可であることが判明**: 回線サービスが提供不可であることが判明した
- **回線業者からの追加情報提供依頼発生（図面等）**: 回線業者から追加の情報提供を求められた
- **回線業者による納期変更**: 回線業者が納期を変更した
- **回線開通の遅れ**: 回線の開通作業が遅れた

### 免許不具合
- **衛星干渉協議との局名矛盾**: 衛星干渉協議で局名に矛盾が発生した
- **免許依頼のみで基本図到着遅れ**: 免許申請後の基本図到着が遅れた

### 法規制
- **法規制対応**: 各種法規制への対応

### 産廃発生
- **現地で予定外の産廃が追加発生（オーナー物品）**: 現地でオーナー物品の産廃が予定外に発生した
- **現地で予定外の産廃が追加発生（以前工事での置忘れ設備）**: 以前の工事で置き忘れられた設備の産廃が発生した

### オーナー交渉難航
- **基本同意に難航（オーナー説明が行えない）**: オーナーへの説明ができずに基本同意が困難
- **基本同意に難航（口頭同意）**: 口頭での同意のみで正式同意が困難
- **基本同意に難航（現地立入許可頭）**: 現地立入許可で基本同意が困難
- **契約条件交渉に難航**: 契約条件の交渉が難航している

### 近隣交渉難航
- **２H対応に難航（近隣説明が行えない）**: 近隣への説明ができずに２H対応が困難
- **２H対応に難航（近隣の反対）**: 近隣の反対により２H対応が困難

### 他事業者交渉難航
- **設備共用に難航/不許可**: 他事業者との設備共用が困難または不許可
- **設備干渉に難航/不許可**: 設備干渉の調整が困難または不許可  
- **電波干渉に難航/不許可**: 電波干渉の調整が困難または不許可
- **衛星干渉に難航/不許可**: 衛星干渉の調整が困難または不許可

### 親局不具合
- **C-RANで親局がSinせず**: C-RANで親局が同期しない

### イレギュラ発生
- **施工中に問題発生（湧水、想定以上に軟弱地盤など）**: 施工中に予期しない地盤や環境の問題が発生（自然災害は除く）
- **施工後に障害発生**: 施工完了後に設備や機能の障害が発生
- **施工後に干渉発生（700M）**: 施工後に700MHz帯で干渉が発生

**上記の体系に該当しない遅延理由（例. 地震、洪水等の自然災害や火災などの人的災害など）の場合は「重大問題（要人的確認）」として分類してください。**

## 緊急度スコア（urgency_score）
遅延理由や報告書内容を踏まえ、将来の遅延可能性を1-10で評価してください：
- **9-10**: 引き続きまたは今後停止・中断の引き続きの可能性あり
- **7-8**: 引き続きまたは今後数か月・数年規模の遅延の可能性あり
- **4-6**: 引き続きまたは今後数日・数週間規模の遅延の可能性あり
- **1-3**: 引き続きまたは今後も順調・問題なし

以下のJSON形式で**必ず**全項目を回答してください：
```json
{{{{
  "analysis_metadata": {{{{
    "overall_confidence": "0.0-1.0の数値",
    "analysis_summary": "分析全体の要約説明",
    "difficult_items": ["判定困難な項目のリスト"],
    "high_confidence_items": ["高信頼度項目のリスト"],
    "extraction_method": "direct_extraction/inference_based/vector_search_required"
  }}}},
  "report_type": "TROUBLE_REPORT/PROGRESS_UPDATE/CONSTRUCTION_REPORT/CONSTRUCTION_ESTIMATE/NEGOTIATION_PROGRESS/STRUCTURAL_DESIGN/OTHER",
  "report_type_confidence": "0.0-1.0の数値",
  "report_type_evidence": "判定根拠の説明",
  "project_info": {{{{
    "project_id": "MOIDまたはMO-IDまたはauRoraMO-ID、不明な場合は\"不明\"）",
    "project_id_confidence": "0.0-1.0の数値",
    "project_id_evidence": "判定根拠の説明（文書内のどの部分から抽出したかを具体的に記載）",
    "extracted_keywords": ["抽出されたキーワードのリスト"],
    "station_name": "局名（文書から抽出、不明な場合は\"不明\"）",
    "station_name_confidence": "0.0-1.0の数値",
    "station_name_evidence": "判定根拠の説明",
    "station_number": "局番（文書から抽出、TKNE-001のような形式、不明な場合は\"不明\"）",
    "station_number_confidence": "0.0-1.0の数値",
    "station_number_evidence": "判定根拠の説明",
    "aurora_plan": "auRoraプラン名またはプラン名（文書から抽出、不明な場合は\"不明\"）",
    "aurora_plan_confidence": "0.0-1.0の数値",
    "aurora_plan_evidence": "判定根拠の説明",
    "location": "場所（文書から抽出、不明な場合は\"不明\"）",
    "location_confidence": "0.0-1.0の数値",
    "location_evidence": "判定根拠の説明",
    "responsible_person": "担当者（文書から抽出、不明な場合は\"不明\"）",
    "responsible_person_confidence": "0.0-1.0の数値",
    "responsible_person_evidence": "判定根拠の説明"
  }}}},
  "summary": "現在の状況説明と管理者向け要約を統合した文章",
  "issues": ["問題1", "問題2"],
  "status_flag": "停止/重大な遅延/軽微な遅延/順調（現時点の客観的状況）",
  "status_flag_confidence": "0.0-1.0の数値",
  "status_flag_evidence": "判定根拠の説明",
  "report_type_phase_mapping": {{{{
    "expected_primary_phase": "報告書タイプから推定される主要工程",
    "possible_phases": ["可能性のある工程のリスト"],
    "mapping_confidence": "0.0-1.0の数値",
    "mapping_description": "マッピング理由の説明",
    "phase_consistency_note": "報告書タイプと内容の整合性確認用"
  }}}},
  "delay_reasons": [{{{{
    "category": "工程ミス/要件漏れ/無線機不具合/物件不具合/設計不足/電源遅延/回線不具合/免許不具合/法規制/産廃発生/オーナー交渉難航/近隣交渉難航/他事業者交渉難航/親局不具合/イレギュラ発生/重大問題（要人的確認）",
    "subcategory": "具体的な遅延理由サブカテゴリ",
    "description": "遅延の詳細説明",
    "confidence": "0.0-1.0の数値",
    "evidence": "判定根拠の説明"
  }}}}],
  "requires_human_review": false,
  "analysis_confidence": "0.0-1.0の数値",
  "urgency_score": "1-10の数値",
  "urgency_score_confidence": "0.0-1.0の数値",
  "urgency_score_evidence": "判定根拠の説明",
  "key_points": ["重要ポイント1", "重要ポイント2"]
}}}}
```

## 重要な指針
1. **必須項目**: analysis_metadata, report_type, project_info, status_flag, report_type_phase_mapping, delay_reasons, urgency_score
2. **JSON構造**: 上記Few-shot例と同じ完全な構造で出力してください
3. **信頼度・根拠**: 全ての分析項目に confidence (0.0-1.0) と evidence (根拠説明) を必ず付与
4. **requires_human_review**: 遅延理由が「重大問題（要人的確認）」またはLLMが分類に確信を持てない場合 true
5. **analysis_metadata**: 分析全体の信頼度、サマリ、困難項目、高信頼度項目を必ず記載
6. **不明項目**: "不明"と明記、推測は避ける。confidence は低く設定し evidence で理由を説明
7. **遅延理由**: 15カテゴリ体系に該当しない場合 「重大問題（要人的確認）」とする
8. **report_type_phase_mapping**: 報告書タイプから推定される建設工程関連性を記載（統合分析の重要なインプット）
9. **status_flag判定の最重要指針**: 文書タイプに関わらず文書内容を最優先で判定。現時点の状況として「中断」「停止」という旨の記載がある場合は、必ず「停止」とする。
10. **urgency_score**: 将来の遅延可能性を1-10で評価、confidence と evidence も必須
11. **キーワード混乱回避**: 担当者名、局名、住所などの類似した名称を他のプロジェクトと混同しないよう注意。文書内容に明記されていないプロジェクトIDは推測せず「不明」とする
12. **project_id抽出の重要指針**: 文書内で「auRoraMO-ID | MO0001」「MOID: MO0001」「MO-ID: MO0001」のような形式を見つけた場合、必ずMO0001部分を抽出してください。表形式データでも見落とさないよう注意深く確認してください"""

# Few-shot例文（最新のJSON構造）
FEW_SHOT_EXAMPLES = """
## 分析例1: 建設見積書レポート
入力: "札幌センター南基地局建設の建設図面見積書です。auRoraMO-ID | MO1234、auRoraプラン: 容量対策_700M新設_B11追加。現在は基本図承認段階で、順調に進行中です。"
出力:
```json
{
  "analysis_metadata": {
    "overall_confidence": 0.85,
    "analysis_summary": "明確なプロジェクトIDと進行状況が記載された建設見積書",
    "difficult_items": ["担当者情報", "詳細な場所情報"],
    "high_confidence_items": ["プロジェクトID", "報告書種別", "現在フェーズ"]
  },
  "report_type": "CONSTRUCTION_ESTIMATE",
  "report_type_confidence": 0.95,
  "report_type_evidence": "建設図面見積書との明記",
  "project_info": {
    "project_id": "MO1234",
    "project_id_confidence": 0.95,
    "project_id_evidence": "auRoraMO-ID | MO1234と明記",
    "station_name": "札幌センター南",
    "station_name_confidence": 0.90,
    "station_name_evidence": "札幌センター南基地局建設と明記",
    "station_number": "不明",
    "station_number_confidence": 0.0,
    "station_number_evidence": "文書に記載なし",
    "aurora_plan": "容量対策_700M新設_B11追加",
    "aurora_plan_confidence": 0.95,
    "aurora_plan_evidence": "auRoraプラン: 容量対策_700M新設_B11追加と明記",
    "location": "不明",
    "location_confidence": 0.0,
    "location_evidence": "詳細な住所の記載なし",
    "responsible_person": "不明",
    "responsible_person_confidence": 0.0,
    "responsible_person_evidence": "担当者名の記載なし"
  },
  "summary": "札幌センター南基地局の工事見積書、基本図承認段階で順調進行",
  "summary_confidence": 0.90,
  "summary_evidence": "基本図承認段階で順調進行との記載",
  "issues": [],
  "issues_confidence": 0.80,
  "issues_evidence": "問題の記載なし、順調進行と明記",
  "status_flag": "順調",
  "status_flag_confidence": 0.90,
  "status_flag_evidence": "順調に進行中との記載",
  "report_type_phase_mapping": {
    "expected_phase": "基本図承認",
    "phase_consistency": "一致",
    "confidence": 0.90,
    "evidence": "建設見積書は基本図承認段階で作成される"
  },
  "delay_reasons": [],
  "delay_reasons_confidence": 0.85,
  "delay_reasons_evidence": "遅延の記載なし、順調進行",
  "requires_human_review": false,
  "requires_human_review_confidence": 0.90,
  "requires_human_review_evidence": "明確な情報で分類可能",
  "analysis_confidence": 0.85,
  "urgency_score": 3,
  "urgency_score_confidence": 0.80,
  "urgency_score_evidence": "順調進行だが基本図承認段階のため中程度",
  "key_points": ["基本図承認段階", "順調進行", "工事見積書作成完了"]
}
```

## 分析例2: 交渉進捗レポート（遅延あり）
入力: "新宿センター西基地局の交渉進捗レポートです。住所は東京都新宿区。オーナーとの交渉が難航し、基本同意取得に時間を要しています。近隣住民からの反対意見もあり、リスクが高まっています。予定を2024/02/10から2024/07/10に延期します。"
出力:
```json
{
  "analysis_metadata": {
    "overall_confidence": 0.75,
    "analysis_summary": "プロジェクトID不明だが遅延問題が明確な交渉進捗レポート",
    "difficult_items": ["プロジェクトID", "担当者情報", "具体的な遅延期間"],
    "high_confidence_items": ["報告書種別", "遅延理由", "リスクレベル"]
  },
  "report_type": "NEGOTIATION_PROGRESS",
  "report_type_confidence": 0.90,
  "report_type_evidence": "交渉進捗レポートとの明記",
  "project_info": {
    "project_id": "不明",
    "project_id_confidence": 0.0,
    "project_id_evidence": "プロジェクトIDの記載なし",
    "station_name": "新宿センター西",
    "station_name_confidence": 0.95,
    "station_name_evidence": "新宿センター西基地局と明記",
    "station_number": "不明",
    "station_number_confidence": 0.0,
    "station_number_evidence": "局番の記載なし",
    "aurora_plan": "不明",
    "aurora_plan_confidence": 0.0,
    "aurora_plan_evidence": "auRoraプランの記載なし",
    "location": "東京都新宿区",
    "location_confidence": 0.90,
    "location_evidence": "住所は東京都新宿区と明記",
    "responsible_person": "不明",
    "responsible_person_confidence": 0.0,
    "responsible_person_evidence": "担当者名の記載なし"
  },
  "summary": "新宿センター西基地局の交渉進捗、オーナー交渉難航で軽微な遅延、近隣住民反対によりリスク高",
  "summary_confidence": 0.85,
  "summary_evidence": "オーナー交渉難航と近隣住民反対の明記",
  "issues": ["オーナー交渉難航", "近隣住民反対"],
  "issues_confidence": 0.90,
  "issues_evidence": "オーナーとの交渉が難航、近隣住民からの反対意見と明記",
  "status_flag": "重大な遅延",
  "status_flag_confidence": 0.80,
  "status_flag_evidence": "予定を2024/02/10から2024/07/10に延期していると記載",
  "report_type_phase_mapping": {
    "expected_phase": "基本同意",
    "phase_consistency": "一致",
    "confidence": 0.85,
    "evidence": "交渉進捗レポートは基本同意段階で作成される"
  },
  "delay_reasons": [{
    "category": "オーナー交渉難航",
    "subcategory": "基本同意に難航（口頭同意）",
    "description": "オーナーとの交渉に難航しており、基本同意が困難",
    "confidence": 0.90,
    "evidence": "オーナーとの交渉が難航し、基本同意取得に時間を要していると明記"
  },
  {
    "category": "近隣住民反対",
    "subcategory": "近隣住民反対",
    "description": "近隣住民からの反対意見もあり、リスクが高まっています。",
    "confidence": 0.90,
    "evidence": "近隣住民からの反対意見もあり、リスクが高まっていると明記"
  }],
  "delay_reasons_confidence": 0.90,
  "delay_reasons_evidence": "オーナー交渉難航が明確に記載",
  "requires_human_review": false,
  "requires_human_review_confidence": 0.85,
  "requires_human_review_evidence": "15カテゴリ体系で分類可能",
  "analysis_confidence": 0.75,
  "urgency_score": 7,
  "urgency_score_confidence": 0.85,
  "urgency_score_evidence": "遅延発生中かつ近隣住民反対でリスク高",
  "key_points": ["オーナー交渉難航", "近隣住民反対", "遅延リスク", "基本同意段階"]
}
```

## 分析例3: 工事停止レポート（アスベスト検出）
入力: "横浜港北基地局建設の工事進捗報告書です。auRoraMO-ID | MO9876、局名: 横浜港北センター、住所: 神奈川県横浜市港北区。工事開始後、屋上貯水槽の解体作業中にアスベスト含有材料を検出しました。安全確保のため工事を緊急停止し、専門業者による詳細調査と除去作業が必要となります。工期は調査結果により大幅に変更予定です。"
出力:
```json
{
  "analysis_metadata": {
    "overall_confidence": 0.90,
    "analysis_summary": "アスベスト検出により工事緊急停止、専門調査が必要な重大事案",
    "difficult_items": ["復旧時期の予測", "除去作業期間"],
    "high_confidence_items": ["プロジェクトID", "停止理由", "ステータス"],
    "extraction_method": "direct_extraction"
  },
  "report_type": "CONSTRUCTION_REPORT",
  "report_type_confidence": 0.95,
  "report_type_evidence": "工事進捗報告書との明記",
  "project_info": {
    "project_id": "MO9876",
    "project_id_confidence": 0.95,
    "project_id_evidence": "auRoraMO-ID | MO9876と明記",
    "station_name": "横浜港北センター",
    "station_name_confidence": 0.95,
    "station_name_evidence": "局名: 横浜港北センターと明記",
    "station_number": "不明",
    "station_number_confidence": 0.0,
    "station_number_evidence": "局番の記載なし",
    "aurora_plan": "不明",
    "aurora_plan_confidence": 0.0,
    "aurora_plan_evidence": "auRoraプランの記載なし",
    "location": "神奈川県横浜市港北区",
    "location_confidence": 0.95,
    "location_evidence": "住所: 神奈川県横浜市港北区と明記",
    "responsible_person": "不明",
    "responsible_person_confidence": 0.0,
    "responsible_person_evidence": "担当者名の記載なし"
  },
  "summary": "横浜港北基地局建設でアスベスト検出により工事緊急停止、専門調査と除去作業が必要",
  "issues": ["アスベスト検出", "工事緊急停止", "専門調査必要"],
  "status_flag": "停止",
  "status_flag_confidence": 0.95,
  "status_flag_evidence": "安全確保のため工事を緊急停止と明記",
  "report_type_phase_mapping": {
    "expected_primary_phase": "附帯着工",
    "possible_phases": ["工事開始", "施工"],
    "mapping_confidence": 0.85,
    "mapping_description": "工事進捗報告書は附帯着工段階で作成される",
    "phase_consistency_note": "工事開始後の進捗報告"
  },
  "delay_reasons": [{
    "category": "重大問題（要人的確認）",
    "subcategory": "アスベスト含有材料検出",
    "description": "屋上貯水槽解体作業中にアスベスト含有材料を検出、専門調査と除去作業が必要",
    "confidence": 0.95,
    "evidence": "屋上貯水槽の解体作業中にアスベスト含有材料を検出と明記"
  }],
  "delay_reasons_confidence": 0.95,
  "delay_reasons_evidence": "アスベスト検出による工事停止が明確に記載",
  "requires_human_review": true,
  "requires_human_review_confidence": 0.95,
  "requires_human_review_evidence": "アスベスト問題は重大問題（要人的確認）に該当",
  "analysis_confidence": 0.90,
  "urgency_score": 10,
  "urgency_score_confidence": 0.95,
  "urgency_score_evidence": "工事緊急停止かつ専門調査が必要で最高緊急度",
  "key_points": ["アスベスト検出", "工事緊急停止", "専門調査必要", "除去作業待ち"]
}
```
"""

# 質問応答プロンプト
QA_PROMPT = """あなたは建設工程管理のエキスパートです。RAGシステムによって検索された関連文書を基に、質問に対して正確で実用的な回答を提供してください。

質問: {question}

検索された関連文書:
{context}

【回答指針】
- 検索された文書の内容を最優先に活用してください
- 類似度の高い文書ほど信頼性が高いです
- 文書に記載されていない内容は推測せず、「文書に記載なし」と明記してください
- 建設業界の専門用語を正確に使用してください
- 回答は簡潔で読みやすい形式で提供してください

【回答形式】
以下の形式で回答してください（記号は使用せず、シンプルなテキストで）：

回答: [質問への直接的な回答]

根拠: [回答の根拠となる具体的な文書情報（ファイル名と内容を明記）]

関連情報: [検索された文書から得られる関連する重要な補足情報]

推奨対応: [必要に応じた具体的な推奨対応策]


建設業界の専門知識とRAGシステムで検索された最新情報を組み合わせ、実用的で具体的な回答を提供してください。"""

# ========================================
# 統合分析プロンプト（案件レベル分析）
# ========================================

# 統合分析システムプロンプト
INTEGRATION_SYSTEM_PROMPT = """あなたは建設工程管理の統合分析エキスパートです。複数の報告書を時系列で分析し、案件全体の状況を包括的に判定する専門知識を持っています：

## 専門知識
1. **時系列分析**: 報告書の時間的変化から進捗トレンドを把握
2. **継続性評価**: 問題の継続性と解決状況の判定
3. **工程管理**: 7ステップ建設工程の詳細な進捗管理
4. **リスク統合判定**: 複数報告書からの総合的リスク評価
5. **遅延理由管理**: 複数の遅延要因の統合的な管理と追跡

## あなたの役割
1. 案件の全報告書を時系列で分析
2. 工程進捗の総合的な判定
3. 問題の継続性と解決状況の評価
4. 統合的なリスクレベルの判定
5. 具体的な推奨対応策の提案

常に時系列での変化を重視し、単発の情報ではなく文脈を考慮した総合判定を行ってください。"""

# 統合分析メインプロンプト
INTEGRATION_ANALYSIS_PROMPT = """以下の案件について、全報告書を時系列で分析し、統合的な案件状況を判定してください：

案件ID: {project_id}
報告書数: {report_count}件

{reports_data}

## 分析観点
1. **時系列統合分析**: 複数報告書の時間的変化から進捗トレンドを把握
2. **案件全体状況**: 統合的なステータスとリスクレベルの判定
3. **建設工程7ステップ詳細**: 各工程の進捗状況と現在フェーズの特定
4. **問題継続性評価**: 問題の新規発生・継続・解決状況の分析
5. **遅延理由統合管理**: 複数の遅延要因の統合的な管理と追跡
6. **報告頻度分析**: 報告書提出パターンの評価
7. **推奨対応策**: 即時・監視・長期対策の具体的提案

## レポートタイプの定義
- **TROUBLE_REPORT**: 緊急事態、重大トラブル、予期しない問題の報告
- **PROGRESS_UPDATE**: 定期的な進捗状況、状況変化の報告
- **CONSTRUCTION_REPORT**: 作業実績、技術的な工程状況の報告
- **CONSTRUCTION_ESTIMATE**: 工事見積書、パッケージ化見積書
- **NEGOTIATION_PROGRESS**: 交渉経緯報告書、置局物件交渉経緯報告書
- **STRUCTURAL_DESIGN**: 強度計算結果報告書、構造設計関連文書
- **OTHER**: 上記に該当しない文書

## 統合ステータスフラグ（案件全体の客観的状況、必須選択）
- **停止**: 案件が停止・中断している状態
- **重大な遅延**: 重大な遅延（数か月・数年規模）が発生し継続している状態
- **軽微な遅延**: 軽微な遅延（数日・数週間規模）が発生している状態
- **順調**: 正常な進捗・問題なし（時系列で改善傾向）

## 建設工程7ステップ詳細ガイド

### 各工程で作成される報告書種別
- **置局発注**: 工事見積書
- **基本同意**: 交渉経緯報告書
- **基本図承認**: ビル基地局構造設計書
- **内諾**: 建設工事許可申請書、承認書
- **附帯着工**: 工事開始報告書、工事進捗報告書
- **電波発射**: 電波発射許可申請書、電波発射結果報告書
- **工事検収**: 工事検収報告書

### 各工程のステータス判定基準
- **完了**: 該当工程の必要書類がすべて承認・完了している状態
- **実施中**: 該当工程の作業が進行中で、報告書が継続的に作成されている状態
- **一時停止**: 該当工程で問題が発生し、作業が中断している状態
- **再見積もり中**: 該当工程で設計変更や条件変更により、再検討が必要な状態
- **未着手**: 該当工程にまだ着手していない状態

### current_phase判定指針
最新の報告書種別と工程進捗を総合的に判断し、現在最も活発に活動している工程を特定してください。

## 遅延理由体系（delay_reasons_management）
統合分析では、複数報告書から得られた遅延理由を以下の体系で統合管理してください：

### 工程ミス
- **前工程からの情報連絡ミス**: 前工程からの情報連絡に不備があった
- **前工程の情報不備**: 前工程で提供される情報に不備があった  
- **前工程の遅れ**: 前工程の完了が遅れた
- **自工程のオーバーフロー**: 自工程で処理能力を超過した
- **自工程の対応漏れ**: 自工程で必要な対応が漏れた

### 要件漏れ
- **要件変更**: 要件が変更された
- **MO発行漏れ**: MO（業務指示書）の発行が漏れた
- **連絡不備**: 必要な連絡に不備があった

### 無線機不具合
- **エリア検討書_KDDI発改版の発生**: エリア検討書でKDDI発改版が発生した
- **無線機設定と回線設定の食違い発生**: 無線機設定と回線設定に食い違いが発生した

### 物件不具合  
- **候補物件が見つからない**: 適切な候補物件が見つからない
- **候補物件が基準を満たさない**: 候補物件が必要な基準を満たさない

### 設計不足
- **物品不足（物品発注不足）**: 必要な物品の発注が不足した
- **物品不足（納品遅れ）**: 物品の納品が遅れた

### 電源遅延
- **受電遅延**: 電源の受電が遅延した

### 回線不具合
- **回線が提供不可であることが判明**: 回線サービスが提供不可であることが判明した
- **回線業者からの追加情報提供依頼発生（図面等）**: 回線業者から追加の情報提供を求められた
- **回線業者による納期変更**: 回線業者が納期を変更した
- **回線開通の遅れ**: 回線の開通作業が遅れた

### 免許不具合
- **衛星干渉協議との局名矛盾**: 衛星干渉協議で局名に矛盾が発生した
- **免許依頼のみで基本図到着遅れ**: 免許申請後の基本図到着が遅れた

### 法規制
- **法規制対応**: 各種法規制への対応

### 産廃発生
- **現地で予定外の産廃が追加発生（オーナー物品）**: 現地でオーナー物品の産廃が予定外に発生した
- **現地で予定外の産廃が追加発生（以前工事での置忘れ設備）**: 以前の工事で置き忘れられた設備の産廃が発生した

### オーナー交渉難航
- **基本同意に難航（オーナー説明が行えない）**: オーナーへの説明ができずに基本同意が困難
- **基本同意に難航（口頭同意）**: 口頭での同意のみで正式同意が困難
- **基本同意に難航（現地立入許可頭）**: 現地立入許可で基本同意が困難
- **契約条件交渉に難航**: 契約条件の交渉が難航している

### 近隣交渉難航
- **２H対応に難航（近隣説明が行えない）**: 近隣への説明ができずに２H対応が困難
- **２H対応に難航（近隣の反対）**: 近隣の反対により２H対応が困難

### 他事業者交渉難航
- **設備共用に難航/不許可**: 他事業者との設備共用が困難または不許可
- **設備干渉に難航/不許可**: 設備干渉の調整が困難または不許可  
- **電波干渉に難航/不許可**: 電波干渉の調整が困難または不許可
- **衛星干渉に難航/不許可**: 衛星干渉の調整が困難または不許可

### 親局不具合
- **C-RANで親局がSinせず**: C-RANで親局が同期しない

### イレギュラ発生
- **施工中に問題発生（湧水、想定以上に軟弱地盤など）**: 施工中に予期しない地盤や環境の問題が発生（自然災害は除く）
- **施工後に障害発生**: 施工完了後に設備や機能の障害が発生
- **施工後に干渉発生（700M）**: 施工後に700MHz帯で干渉が発生

### 重大問題（要人的確認）
- **上記カテゴリに該当しない重大な問題**: 15カテゴリ体系に該当しない場合

## 統合分析要求（全項目網羅）

以下のJSON形式で**必ず**全項目を回答してください：

```json
{{
  "analysis_metadata": {{
    "overall_confidence": 0.00-1.00,
    "analysis_summary": "時系列での変化を踏まえた総合的な案件状況の説明",
    "difficult_items": ["判定困難な項目"],
    "high_confidence_items": ["高信頼度項目"]
  }},
  
  "overall_status": "停止/重大な遅延/軽微な遅延/順調",
  "overall_status_confidence": 0.00-1.00,
  "overall_status_evidence": "時系列での状況変化から判定した根拠",
  
  "overall_risk": "高/中/低",
  "overall_risk_confidence": 0.00-1.00,
  "overall_risk_evidence": "継続的な問題や影響範囲を考慮した根拠",
  
  "current_phase": "置局発注/基本同意/基本図承認/内諾/附帯着工/電波発射/工事検収",
  "current_phase_confidence": 0.00-1.00,
  "current_phase_evidence": "最新報告書と過去の進捗から判定した根拠",
  
  "construction_phases": {{
    "置局発注": {{
      "status": "完了/実施中/一時停止/再見積もり中/未着手",
      "confidence": 0.00-1.00,
      "evidence": "判定根拠"
    }},
    "基本同意": {{
      "status": "完了/実施中/一時停止/再見積もり中/未着手",
      "confidence": 0.00-1.00,
      "evidence": "判定根拠"
    }},
    "基本図承認": {{
      "status": "完了/実施中/一時停止/再見積もり中/未着手",
      "confidence": 0.00-1.00,
      "evidence": "判定根拠"
    }},
    "内諾": {{
      "status": "完了/実施中/一時停止/再見積もり中/未着手",
      "confidence": 0.00-1.00,
      "evidence": "判定根拠"
    }},
    "附帯着工": {{
      "status": "完了/実施中/一時停止/再見積もり中/未着手",
      "confidence": 0.00-1.00,
      "evidence": "判定根拠"
    }},
    "電波発射": {{
      "status": "完了/実施中/一時停止/再見積もり中/未着手",
      "confidence": 0.00-1.00,
      "evidence": "判定根拠"
    }},
    "工事検収": {{
      "status": "完了/実施中/一時停止/再見積もり中/未着手",
      "confidence": 0.00-1.00,
      "evidence": "判定根拠"
    }}
  }},
  
  "progress_trend": "改善/悪化/停滞",
  "progress_trend_confidence": 0.00-1.00,
  "progress_trend_evidence": "時系列での進捗変化の分析根拠",
  
  "issue_continuity": "新規/継続/解決済み",
  "issue_continuity_confidence": 0.00-1.00,
  "issue_continuity_evidence": "問題の継続性に関する分析根拠",
  
  "report_frequency": "正常/減少/停止",
  "report_frequency_confidence": 0.00-1.00,
  "report_frequency_evidence": "報告頻度の分析根拠",
  
  "delay_reasons_management": [
    {{
      "delay_category": "15カテゴリ遅延理由体系のいずれか（工程ミス/要件漏れ/無線機不具合/物件不具合/設計不足/電源遅延/回線不具合/免許不具合/法規制/産廃発生/オーナー交渉難航/近隣交渉難航/他事業者交渉難航/親局不具合/イレギュラ発生）または重大問題（要人的確認）",
      "delay_subcategory": "具体的なサブカテゴリ（例：基本同意に難航、図面提供遅延など）",
      "description": "遅延理由の詳細説明",
      "status": "継続中/解決済み/新規発生のいずれか",
      "current_response": "現在実施中の対応策",
      "confidence": "0.00-1.00の数値",
      "evidence": "判定根拠の説明",
      "first_reported": "YYYY-MM-DD形式の初回報告日",
      "last_updated": "YYYY-MM-DD形式の最終更新日"
    }}
  ],
  
  "recommended_actions": [
    "即時対応が必要な項目",
    "監視継続が必要な項目", 
    "長期対策が必要な項目"
  ]
}}
```

## 重要な指針
1. **時系列分析**: 報告書の時間的変化を重視して判定
2. **継続性評価**: 単発問題か継続問題かを区別
3. **文脈考慮**: 過去の経緯を踏まえた現在の状況判定
4. **信頼度評価**: 各判定の確実性を0.0-1.0で評価
5. **根拠明示**: 判定理由を具体的に説明
6. **複数遅延理由対応**: 一つの案件で複数の遅延理由（問題・課題）が同時に発生している場合は、それぞれを個別の項目として delay_reasons_management に含める
7. **遅延理由の統合**: 同じカテゴリ・サブカテゴリの問題が複数の報告書で報告されている場合は、時系列での変化を考慮して統合する
8. **工程判定**: 報告書種別と内容から各工程のステータスを論理的に推定し、矛盾がないよう注意する"""

# 統合分析Few-shot例
INTEGRATION_FEW_SHOT_EXAMPLES = """## 統合分析Few-shot例

### 例1: 順調進行案件（MO1001）
**入力**: 
```
案件ID: MO1001
報告書数: 2件

==================================================
報告書1: estimate_MO1001_新宿センター東_v1.0.xlsx
作成日時: 2024-01-15 09:30:00
レポートタイプ: ReportType.CONSTRUCTION_ESTIMATE
ステータス: StatusFlag.NORMAL
リスクレベル: RiskLevel.LOW
要約: 新宿センター東基地局の建設見積書、基本図承認段階で順調進行
問題: 問題なし
遅延理由: []
緊急度スコア: 3

==================================================
報告書2: negotiation_MO1001_新宿センター東_v1.1.docx
作成日時: 2024-01-20 14:15:00
レポートタイプ: ReportType.NEGOTIATION_PROGRESS
ステータス: StatusFlag.NORMAL
リスクレベル: RiskLevel.LOW
要約: オーナーとの基本同意取得が完了、次工程への準備中
問題: 問題なし
遅延理由: []
緊急度スコア: 2

==================================================
```

**出力例**:
```json
{{
  "analysis_metadata": {{
    "overall_confidence": 0.85,
    "analysis_summary": "基本同意取得完了後、基本図承認段階で順調に進行中",
    "difficult_items": ["将来の遅延リスク予測"],
    "high_confidence_items": ["現在工程", "進捗状況", "ステータス判定"]
  }},
  "overall_status": "順調",
  "overall_status_confidence": 0.90,
  "overall_status_evidence": "両報告書で順調進行が確認され、工程が適切に進んでいる",
  "overall_risk": "低",
  "overall_risk_confidence": 0.85,
  "overall_risk_evidence": "問題の報告がなく、順調に進行している",
  "current_phase": "基本図承認",
  "current_phase_confidence": 0.90,
  "current_phase_evidence": "最新の建設見積書で基本図承認段階と明記",
  "construction_phases": {{
    "置局発注": {{
      "status": "完了",
      "confidence": 0.80,
      "evidence": "基本同意段階に進んでいることから推定"
    }},
    "基本同意": {{
      "status": "完了",
      "confidence": 0.95,
      "evidence": "交渉進捗レポートで取得完了と明記"
    }},
    "基本図承認": {{
      "status": "実施中",
      "confidence": 0.95,
      "evidence": "建設見積書で基本図承認段階と明記"
    }},
    "内諾": {{
      "status": "未着手",
      "confidence": 0.90,
      "evidence": "まだ基本図承認段階のため"
    }},
    "附帯着工": {{
      "status": "未着手",
      "confidence": 0.90,
      "evidence": "まだ基本図承認段階のため"
    }},
    "電波発射": {{
      "status": "未着手",
      "confidence": 0.90,
      "evidence": "まだ基本図承認段階のため"
    }},
    "工事検収": {{
      "status": "未着手",
      "confidence": 0.90,
      "evidence": "まだ基本図承認段階のため"
    }}
  }},
  "progress_trend": "改善",
  "progress_trend_confidence": 0.85,
  "progress_trend_evidence": "基本同意取得完了から基本図承認へ順調に進行",
  "issue_continuity": "解決済み",
  "issue_continuity_confidence": 0.90,
  "issue_continuity_evidence": "両報告書で問題の報告なし",
  "report_frequency": "正常",
  "report_frequency_confidence": 0.90,
  "report_frequency_evidence": "適切な間隔で報告書が提出されている",
  "delay_reasons_management": [],
  "recommended_actions": [
    "基本図承認の完了に向けた継続的な監視",
    "次工程（内諾）の準備開始",
    "順調な進行状況の維持"
  ]
}}
```

### 例2: 遅延発生案件（MO2002）
**入力**:
```
案件ID: MO2002
報告書数: 2件

==================================================
報告書1: negotiation_MO2002_渋谷ビル西_v1.0.docx
作成日時: 2024-01-10 11:00:00
レポートタイプ: ReportType.NEGOTIATION_PROGRESS
ステータス: StatusFlag.MINOR_DELAY
リスクレベル: RiskLevel.MEDIUM
要約: オーナーとの交渉が難航、基本同意取得に遅延発生
問題: ['オーナー交渉難航']
遅延理由: [{{'category': 'オーナー交渉難航', 'subcategory': '基本同意に難航', 'description': 'オーナーとの面談機会が確保できない'}}]
緊急度スコア: 6

==================================================
報告書2: negotiation_MO2002_渋谷ビル西_v1.1.docx
作成日時: 2024-01-18 16:30:00
レポートタイプ: ReportType.NEGOTIATION_PROGRESS
ステータス: StatusFlag.MINOR_DELAY
リスクレベル: RiskLevel.HIGH
要約: オーナー交渉継続難航、加えて近隣住民からの反対意見も発生
問題: ['オーナー交渉難航', '近隣住民反対']
遅延理由: [{{'category': 'オーナー交渉難航', 'subcategory': '基本同意に難航', 'description': 'オーナーとの面談機会が確保できない'}}, {{'category': '近隣交渉難航', 'subcategory': '近隣住民反対', 'description': '近隣住民からの反対意見が発生'}}]
緊急度スコア: 7

==================================================
```

**出力例**:
```json
{{
  "analysis_metadata": {{
    "overall_confidence": 0.80,
    "analysis_summary": "オーナー交渉が継続的に難航し、新たに近隣住民反対も発生、リスクレベルが上昇",
    "difficult_items": ["解決時期の予測", "近隣住民対応の効果"],
    "high_confidence_items": ["遅延理由", "問題の継続性", "リスク上昇"]
  }},
  "overall_status": "軽微な遅延",
  "overall_status_confidence": 0.85,
  "overall_status_evidence": "複数の報告書で交渉難航が継続し、新たな問題も発生",
  "overall_risk": "高",
  "overall_risk_confidence": 0.90,
  "overall_risk_evidence": "オーナー交渉難航に加え近隣住民反対も発生、リスクが上昇",
  "current_phase": "基本同意",
  "current_phase_confidence": 0.95,
  "current_phase_evidence": "両報告書で基本同意段階での交渉難航が報告",
  "construction_phases": {{
    "置局発注": {{
      "status": "完了",
      "confidence": 0.80,
      "evidence": "基本同意段階に進んでいることから推定"
    }},
    "基本同意": {{
      "status": "実施中",
      "confidence": 0.90,
      "evidence": "交渉難航により基本同意取得が停滞"
    }},
    "基本図承認": {{
      "status": "未着手",
      "confidence": 0.95,
      "evidence": "基本同意が完了していないため"
    }},
    "内諾": {{
      "status": "未着手",
      "confidence": 0.95,
      "evidence": "基本同意が完了していないため"
    }},
    "附帯着工": {{
      "status": "未着手",
      "confidence": 0.95,
      "evidence": "基本同意が完了していないため"
    }},
    "電波発射": {{
      "status": "未着手",
      "confidence": 0.95,
      "evidence": "基本同意が完了していないため"
    }},
    "工事検収": {{
      "status": "未着手",
      "confidence": 0.95,
      "evidence": "基本同意が完了していないため"
    }}
  }},
  "progress_trend": "悪化",
  "progress_trend_confidence": 0.85,
  "progress_trend_evidence": "オーナー交渉難航が継続し、新たに近隣住民反対も発生",
  "issue_continuity": "継続",
  "issue_continuity_confidence": 0.90,
  "issue_continuity_evidence": "オーナー交渉難航が複数報告書で継続報告",
  "report_frequency": "正常",
  "report_frequency_confidence": 0.85,
  "report_frequency_evidence": "適切な間隔で報告書が提出されている",
  "delay_reasons_management": [
    {{
      "delay_category": "オーナー交渉難航",
      "delay_subcategory": "基本同意に難航",
      "description": "オーナーとの面談機会が確保できない",
      "status": "継続中",
      "current_response": "管理会社経由での調整継続",
      "confidence": 0.90,
      "evidence": "複数の報告書で同様の問題が継続報告",
      "first_reported": "2024-01-10",
      "last_updated": "2024-01-18"
    }},
    {{
      "delay_category": "近隣交渉難航",
      "delay_subcategory": "近隣住民反対",
      "description": "近隣住民からの反対意見が発生",
      "status": "新規発生",
      "current_response": "住民説明会の開催検討",
      "confidence": 0.85,
      "evidence": "最新報告書で新たに報告された問題",
      "first_reported": "2024-01-18",
      "last_updated": "2024-01-18"
    }}
  ],
  "recommended_actions": [
    "オーナーとの面談機会確保を最優先で実施",
    "近隣住民への説明会開催と合意形成",
    "管理会社との連携強化による交渉支援"
  ]
}}
```"""