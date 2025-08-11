# 🚀 Git リポジトリセットアップガイド

## 📋 概要
既存の作業ディレクトリを Git リポジトリとして初期化し、GitHub などにプッシュする手順です。

## ✅ 前提条件
- Git がインストールされていること
- GitHub アカウント（またはGitLab、Bitbucket等）
- SSH鍵の設定またはHTTPS認証の準備

## 🔧 セットアップ手順

### 1. Gitリポジトリの初期化
```bash
# プロジェクトディレクトリで実行
cd /home/share/eng-llm-app

# Gitリポジトリを初期化
git init

# ユーザー情報設定（初回のみ）
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### 2. 初回コミット
```bash
# 全ファイルをステージング
git add .

# 初回コミット
git commit -m "🎉 Initial commit: 建設管理LLMアプリケーション

✨ Features:
- プロジェクト中心ダッシュボード
- 統合LLM分析システム
- マルチ戦略プロジェクトマッピング
- AI対話分析パネル
- 定量的評価システム

🔧 Tech Stack:
- Streamlit + Ollama/OpenAI/Anthropic
- ChromaDB + カスタムベクターストア
- 事前処理 + リアルタイム分離設計"
```

### 3. リモートリポジトリの追加
```bash
# GitHubでリポジトリを作成後、URLを追加
git remote add origin https://github.com/yourusername/eng-llm-app.git

# または SSH の場合
git remote add origin git@github.com:yourusername/eng-llm-app.git
```

### 4. プッシュ
```bash
# メインブランチにプッシュ
git branch -M main
git push -u origin main
```

## 🗂️ 除外されるファイル
`.gitignore` により以下が自動除外されます：

### 🚫 除外対象
- `venv/` - 仮想環境
- `data/processed_reports/` - 事前処理結果
- `vector_store/` - ベクターストア
- `*.cache`, `*.pkl` - キャッシュファイル
- `test_*.py` - 一時テストファイル
- `.env` - 環境変数

### ✅ 含まれるファイル
- `app/` - メインアプリケーション
- `scripts/` - 事前処理スクリプト
- `data/sharepoint_docs/` - サンプルドキュメント
- `data/evaluation/` - 評価データ
- `requirements.txt` - 依存関係
- `README.md` - ドキュメント

## 🔄 継続的な開発ワークフロー

### 日常的な作業
```bash
# 変更をステージング
git add .

# コミット
git commit -m "✨ Add: 新機能の追加"

# プッシュ
git push origin main
```

### ブランチを使った開発
```bash
# 新機能用ブランチ作成
git checkout -b feature/new-dashboard

# 開発・コミット
git add .
git commit -m "🚧 WIP: 新ダッシュボード実装中"

# プッシュ
git push origin feature/new-dashboard

# メインブランチにマージ（Pull Request推奨）
git checkout main
git merge feature/new-dashboard
git push origin main
```

## 💡 推奨コミットメッセージ形式

```bash
# 機能追加
git commit -m "✨ Add: プロジェクト詳細画面を追加"

# バグ修正
git commit -m "🐛 Fix: スクロール位置の問題を修正"

# 改善
git commit -m "⚡ Improve: LLM処理の高速化"

# ドキュメント
git commit -m "📝 Update: README.mdを更新"

# リファクタリング
git commit -m "♻️ Refactor: コード構造を整理"

# スタイル
git commit -m "💄 Style: UIデザインを改善"
```

## 🚨 注意事項

1. **機密情報**: `.env` ファイルに API キーを保存し、Git には含めない
2. **大容量ファイル**: モデルファイルやキャッシュは除外する
3. **仮想環境**: `venv/` ディレクトリは含めない（`requirements.txt` で管理）

## 🎯 結論

**既存のディレクトリからでも完全にGitリポジトリ化可能です！**

作業内容を失うことなく、すべてのコードをバージョン管理下に置くことができます。