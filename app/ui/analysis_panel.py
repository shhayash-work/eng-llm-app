"""
分析パネルUI
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime, timedelta
import logging

from app.models.report import DocumentReport
from app.services.llm_service import get_llm_service
from app.services.vector_store import VectorStoreService
import json
from pathlib import Path

logger = logging.getLogger(__name__)

def load_context_analysis() -> Dict[str, Any]:
    """統合分析結果を読み込み"""
    context_file = Path("data/context_analysis/context_analysis.json")
    if context_file.exists():
        try:
            with open(context_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"📊 統合分析結果読み込み: {len(data)}工程の分析結果")
                return data
        except Exception as e:
            st.warning(f"統合分析結果の読み込みに失敗しました: {e}")
            logger.error(f"統合分析結果読み込みエラー: {e}")
    return {}

def render_analysis_panel(reports: List[DocumentReport], audit_type: str = "工程"):
    """分析パネルを表示"""
    st.markdown("<div class='custom-header'>AI対話分析</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>RAG技術による報告書検索とLLMによる自然言語での質問応答システム</p>", unsafe_allow_html=True)
    
    # 表示設定（セクション上部に左寄せ配置）
    st.markdown("**表示設定**")
    col_s1, col_s2, col_spacer = st.columns([2, 2, 6])
    with col_s1:
        use_streaming = st.checkbox("ストリーミング表示", value=True, help="回答をリアルタイムで表示")
    with col_s2:
        show_thinking = st.checkbox("思考過程表示", value=False, help="AIの思考過程を表示")
    
    st.divider()
    
    # 質問応答インターフェース
    render_qa_interface(reports, use_streaming, show_thinking, audit_type)

def render_qa_interface(reports: List[DocumentReport], use_streaming: bool = True, show_thinking: bool = False, audit_type: str = "工程"):
    """質問応答インターフェースを表示"""
    if audit_type == "報告書":
        st.markdown("<div class='custom-header'>報告書について質問する</div>", unsafe_allow_html=True)
        st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>報告書の内容や品質に関する質問にAIが回答（報告書特化RAG処理）</p>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='custom-header'>建設工程について質問する</div>", unsafe_allow_html=True)
        st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>統合分析結果→関連工程の報告書を効率的に検索してAIが回答（効率的RAG処理）</p>", unsafe_allow_html=True)
    
    # サンプル質問（チェック内容に応じて変更）
    st.write("**サンプル質問:**")
    if audit_type == "報告書":
        sample_questions = [
            "報告書の記載内容に不備があるものはありますか？",
            "必須項目が不足している報告書を教えてください",
            "遅延理由の分類が困難な報告書はありますか？",
            "LLMの分析信頼度が低い報告書はどれですか？",
            "報告書の品質に問題があるものを特定してください"
        ]
    else:
        sample_questions = [
            "現在進行中のトラブル工程はありますか？",
            "最も緊急度の高い工程は何ですか？",
            "住民反対が発生している現場はありますか？",
            "工期遅延のリスクがある工程を教えてください",
            "設備不具合が報告されている現場はどこですか？"
        ]
    
    selected_question = st.selectbox(
        "サンプル質問を選択（または下に独自の質問を入力）",
        ["質問を選択..."] + sample_questions
    )
    
    # 質問入力
    if selected_question != "質問を選択...":
        question = st.text_input("質問内容:", value=selected_question)
    else:
        question = st.text_input("質問内容:")
    
    # シンプルなAI質問ボタン（設定なし）
    ask_button = st.button("AIに質問する", type="primary", use_container_width=True)
    
    if ask_button:
        if question:
            st.write("**RAGシステムによるAI回答:**")
            
            # RAGシステムの動作可視化
            with st.spinner("🔍 関連文書を検索中..."):
                # ベクター検索の実行と結果表示
                vector_store = VectorStoreService()
                search_results = vector_store.search_similar_documents(
                    query=question, 
                    n_results=8
                )
                
                # 検索結果の可視化
                if search_results:
                    # 正規化された類似度で関連文書を判定
                    relevant_docs = []
                    for r in search_results:
                        distance = r.get('distance', 0.0)
                        similarity_score = 1.0 / (1.0 + distance / 100.0)
                        if similarity_score > 0.1:
                            relevant_docs.append((r, similarity_score))
                    
                    # 閾値以上のものがない場合は上位3件を使用
                    if not relevant_docs:
                        for r in search_results[:3]:
                            distance = r.get('distance', 0.0)
                            similarity_score = 1.0 / (1.0 + distance / 100.0)
                            relevant_docs.append((r, similarity_score))
                    
                    if relevant_docs:
                        st.success(f"✅ {len(relevant_docs)}件の関連文書を発見")
                        
                        # 検索結果の詳細表示（オプション）
                        if show_thinking:
                            with st.expander("🔍 検索された関連文書"):
                                for i, (result, similarity) in enumerate(relevant_docs[:3]):
                                    metadata = result.get('metadata', {})
                                    st.write(f"**{i+1}. {metadata.get('file_name', '不明')}** (類似度: {similarity:.3f})")
                                    st.write(f"レポート種別: {metadata.get('report_type', '不明')}")
                                    st.write(f"内容抜粋: {result.get('content', '')[:150]}...")
                                    st.divider()
                    else:
                        st.success("✅ 関連文書を検索しました（上位結果を使用）")
                else:
                    st.warning("⚠️ ベクター検索でエラーが発生、最新レポートを使用")
            
            # 思考過程表示
            if show_thinking:
                with st.spinner("🧠 AIが文書を分析中..."):
                    import time
                    time.sleep(1)  # 思考演出
                st.success("💡 回答を生成します")
            
            # 統一された回答表示コンテナ（元のスタイル）
            response_placeholder = st.empty()
            
            if use_streaming:
                # ストリーミング表示（元のinfo風スタイル内で）
                full_response = ""
                chunk_count = 0
                
                for chunk in process_qa_question_stream(question, reports):
                    full_response += chunk
                    chunk_count += 1
                    
                    # 3文字ごとに更新（元のinfo風デザイン）
                    if chunk_count % 3 == 0:
                        with response_placeholder.container():
                            st.info(f"{full_response}▌")  # タイピングカーソル付き
                
                # 最終表示（カーソル削除）
                with response_placeholder.container():
                    st.info(full_response)
                
                # 完了メッセージ
                st.success("✅ RAGシステムによる回答が完了しました")
                
            else:
                # 従来の一括表示（元のスタイル維持）
                if show_thinking:
                    with st.spinner("🤖 AIが回答を生成中..."):
                        answer = process_qa_question(question, reports, audit_type)
                else:
                    with st.spinner("🤖 AIが回答を生成中..."):
                        answer = process_qa_question(question, reports, audit_type)
                
                # 元のシンプルなinfo表示
                with response_placeholder.container():
                    st.info(answer)
                
                # 完了メッセージ
                st.success("✅ RAGシステムによる回答が完了しました")
        else:
            st.warning("質問を入力してください。")

def process_qa_question(question: str, reports: List[DocumentReport], audit_type: str = "工程") -> str:
    """効率的なRAG処理による質問応答（チェック内容に応じて検索方法を変更）"""
    try:
        vector_store = VectorStoreService()
        
        if audit_type == "報告書":
            # 報告書チェック：報告書要約の出力結果をベクトル検索
            return _process_report_audit_question(question, vector_store)
        else:
            # 工程チェック：統合分析結果をベクトル検索
            return _process_project_audit_question(question, reports, vector_store)
        
    except Exception as e:
        return f"申し訳ございませんが、回答の生成中にエラーが発生しました: {str(e)}"

def _process_report_audit_question(question: str, vector_store: VectorStoreService) -> str:
    """報告書チェック用の質問処理：報告書要約をベクトル検索して上位5件を取得"""
    try:
        # 報告書要約の出力結果を検索（統合分析結果を除外）
        search_results = vector_store.search_similar_documents(
            query=question,
            n_results=10  # 多めに取得してフィルタリング
        )
        
        # 統合分析結果を除外し、報告書要約のみを対象とする
        filtered_results = [
            result for result in search_results 
            if result.get('metadata', {}).get('type') != 'context_analysis'
        ]
        
        # 上位5件を取得（類似度閾値は使わない）
        top_5_results = filtered_results[:5]
        
        context_parts = []
        for i, result in enumerate(top_5_results):
            distance = result.get('distance', 0.0)
            similarity_score = 1.0 / (1.0 + distance / 100.0)
            metadata = result.get('metadata', {})
            content = result.get('content', '')
            
            context_parts.append(
                f"=== 報告書要約{i+1} (類似度: {similarity_score:.3f}) ===\\n"
                f"ファイル名: {metadata.get('file_name', '不明')}\\n"
                f"レポート種別: {metadata.get('report_type', '不明')}\\n"
                f"リスクレベル: {metadata.get('risk_level', '不明')}\\n"
                f"ステータス: {metadata.get('status_flag', '不明')}\\n"
                f"要約内容: {content[:400]}...\\n"
            )
        
        if not context_parts:
            return "関連する報告書要約が見つかりませんでした。質問を変更してお試しください。"
        
        # LLMに質問
        context = "\\n".join(context_parts)
        llm_service = get_llm_service()
        answer = llm_service.answer_question(question, context)
        
        logger.info(f"📋 報告書チェック質問処理: {len(top_5_results)}件の報告書要約を使用")
        return answer
        
    except Exception as e:
        return f"報告書チェックの質問処理でエラーが発生しました: {str(e)}"

def _process_project_audit_question(question: str, reports: List[DocumentReport], vector_store: VectorStoreService) -> str:
    """工程チェック用の質問処理：統合分析結果をベクトル検索して上位5件を取得"""
    try:
        # 🔍 Step 1: 統合分析結果から関連工程を検索（上位5件）
        context_results = vector_store.search_similar_documents(
            query=question,
            n_results=5,
            filter_metadata={'type': 'context_analysis'}  # 統合分析結果のみ検索
        )
        
        if not context_results:
            # フォールバック: 通常の報告書検索
            return _fallback_search(question, reports, vector_store)
        
        # 🎯 Step 2: 関連工程IDを特定（上位5件すべて使用）
        related_project_ids = []
        context_parts = []
        
        # 統合分析結果のサマリを追加
        context_analysis = load_context_analysis()
        if context_analysis:
            context_parts.append("=== 全工程統合分析サマリ ===")
            for project_id, analysis in list(context_analysis.items())[:3]:  # 上位3工程のサマリ
                context_parts.append(
                    f"工程ID: {project_id}\\n"
                    f"総合ステータス: {analysis.get('overall_status', '不明')}\\n"
                    f"総合リスク: {analysis.get('overall_risk', '不明')}\\n"
                    f"現在工程: {analysis.get('current_phase', '不明')}\\n"
                    f"進捗傾向: {analysis.get('progress_trend', '不明')}\\n"
                    f"分析サマリ: {analysis.get('analysis_summary', '')}\\n"
                )
            context_parts.append("")
        
        # ベクトル検索結果から関連工程を特定
        for i, result in enumerate(context_results):
            distance = result.get('distance', 0.0)
            similarity_score = 1.0 / (1.0 + distance / 100.0)
            metadata = result.get('metadata', {})
            project_id = metadata.get('project_id')
            
            if project_id and project_id not in related_project_ids:
                related_project_ids.append(project_id)
                
                # 統合分析結果をコンテキストに追加
                context_parts.append(
                    f"=== 関連工程統合分析結果{i+1} ({project_id}) ===\\n"
                    f"類似度: {similarity_score:.3f}\\n"
                    f"総合ステータス: {metadata.get('overall_status', '不明')}\\n"
                    f"総合リスク: {metadata.get('overall_risk', '不明')}\\n"
                    f"現在工程: {metadata.get('current_phase', '不明')}\\n"
                    f"進捗傾向: {metadata.get('progress_trend', '不明')}\\n"
                    f"内容: {result.get('content', '')[:300]}...\\n"
                )
        
        # 📄 Step 3: 関連工程の報告書要約をすべて取得
        if related_project_ids:
            reports_by_project = _load_specific_reports_by_project_ids(related_project_ids)
            
            for project_id in related_project_ids:
                if project_id in reports_by_project:
                    project_reports = reports_by_project[project_id]
                    context_parts.append(f"\\n=== 工程 {project_id} の関連報告書要約 ===")
                    
                    for i, report in enumerate(project_reports):  # 工程の全報告書
                        context_parts.append(
                            f"報告書{i+1}: {report.get('file_name', '不明')}\\n"
                            f"要約: {report.get('analysis_result', {}).get('summary', '')}\\n"
                            f"リスクレベル: {report.get('risk_level', '不明')}\\n"
                            f"ステータス: {report.get('status_flag', '不明')}\\n"
                            f"問題: {', '.join(report.get('analysis_result', {}).get('issues', []))}\\n"
                        )
        
        # 🤖 Step 4: LLMに質問
        context = "\\n".join(context_parts)
        llm_service = get_llm_service()
        answer = llm_service.answer_question(question, context)
        
        logger.info(f"🏗️ 工程チェック質問処理: {len(related_project_ids)}工程、{sum(len(reports_by_project.get(pid, [])) for pid in related_project_ids)}件の報告書要約を使用")
        return answer
        
    except Exception as e:
        return f"工程チェックの質問処理でエラーが発生しました: {str(e)}"

def _load_specific_reports_by_project_ids(project_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """指定された工程IDの報告書のみを読み込み"""
    reports_by_project = {}
    processed_dir = Path("data/processed_reports")
    
    if not processed_dir.exists():
        return {}
    
    # インデックスファイルから処理済みファイル一覧を取得
    index_file = processed_dir / "index.json"
    if index_file.exists():
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # 成功した処理済みファイルのみを対象とする
            successful_files = {k: v for k, v in index_data.get("processed_files", {}).items() 
                              if v.get("status") == "success"}
            
            for file_key, file_info in successful_files.items():
                json_file_path = file_info.get("result_file")
                if json_file_path:
                    json_file = Path(json_file_path)
                    if json_file.exists():
                        try:
                            with open(json_file, 'r', encoding='utf-8') as f:
                                report_data = json.load(f)
                            
                            project_id = report_data.get('project_id')
                            # 指定された工程IDの報告書のみを読み込み
                            if project_id and project_id in project_ids:
                                if project_id not in reports_by_project:
                                    reports_by_project[project_id] = []
                                reports_by_project[project_id].append(report_data)
                                
                        except Exception as e:
                            logger.warning(f"報告書読み込みエラー: {json_file.name} - {e}")
            
        except Exception as e:
            logger.error(f"インデックスファイル読み込みエラー: {e}")
    
    logger.info(f"📊 指定工程の報告書読み込み: {len(reports_by_project)}工程、{sum(len(reports) for reports in reports_by_project.values())}件の報告書")
    return reports_by_project

def _fallback_search(question: str, reports: List[DocumentReport], vector_store: VectorStoreService) -> str:
    """フォールバック: 通常の報告書検索"""
    try:
        # 通常の報告書検索（統合分析結果以外）
        search_results = vector_store.search_similar_documents(
            query=question,
            n_results=8
        )
        
        # 統合分析結果を除外
        filtered_results = [
            result for result in search_results 
            if result.get('metadata', {}).get('type') != 'context_analysis'
        ]
        
        # 上位5件を取得（類似度閾値は使わない）
        top_5_results = filtered_results[:5]
        
        context_parts = []
        for i, result in enumerate(top_5_results):
            distance = result.get('distance', 0.0)
            similarity_score = 1.0 / (1.0 + distance / 100.0)
            metadata = result.get('metadata', {})
            content = result.get('content', '')
            
            context_parts.append(
                f"関連文書{i+1} (類似度: {similarity_score:.3f}):\\n"
                f"ファイル名: {metadata.get('file_name', '不明')}\\n"
                f"レポート種別: {metadata.get('report_type', '不明')}\\n"
                f"リスクレベル: {metadata.get('risk_level', '不明')}\\n"
                f"内容: {content[:300]}...\\n"
            )
        
        # 統合分析結果も追加（JSONファイルから）
        context_analysis = load_context_analysis()
        if context_analysis:
            context_parts.append("\\n=== 案件統合分析結果 ===")
            for project_id, analysis in list(context_analysis.items())[:3]:  # 上位3件
                context_parts.append(
                    f"案件ID: {project_id}\\n"
                    f"総合ステータス: {analysis.get('overall_status', '不明')}\\n"
                    f"総合リスク: {analysis.get('overall_risk', '不明')}\\n"
                    f"分析サマリ: {analysis.get('analysis_summary', '')}\\n"
                )
        
        if not context_parts:
            return "関連する文書が見つかりませんでした。質問を変更してお試しください。"
        
        context = "\\n".join(context_parts)
        llm_service = get_llm_service()
        answer = llm_service.answer_question(question, context)
        
        logger.info(f"🔄 フォールバック検索: {len(top_5_results)}件の文書を使用")
        return answer
        
    except Exception as e:
        return f"フォールバック検索でもエラーが発生しました: {str(e)}"

def process_qa_question_stream(question: str, reports: List[DocumentReport]):
    """質問応答を処理（ストリーミング対応・RAGシステム）"""
    try:
        # 🔍 RAGシステム: 質問内容に基づいて関連文書を動的検索
        vector_store = VectorStoreService()
        search_results = vector_store.search_similar_documents(
            query=question, 
            n_results=8  # より多くの関連文書を検索
        )
        
        # 検索結果から高品質なコンテキストを構築
        context_parts = []
        
        # 上位5件を取得（類似度閾値は使わない）
        top_5_results = search_results[:5] if search_results else []
        
        for i, result in enumerate(top_5_results):
            distance = result.get('distance', 0.0)
            similarity_score = 1.0 / (1.0 + distance / 100.0)
            metadata = result.get('metadata', {})
            content = result.get('content', '')
            
            context_parts.append(
                f"関連文書{i+1} (類似度: {similarity_score:.3f}):\\n"
                f"ファイル名: {metadata.get('file_name', '不明')}\\n"
                f"レポート種別: {metadata.get('report_type', '不明')}\\n"
                f"リスクレベル: {metadata.get('risk_level', '不明')}\\n"
                f"内容: {content[:300]}...\\n"
            )
        
        # 🆕 統合分析結果を追加
        context_analysis = load_context_analysis()
        if context_analysis:
            context_parts.append("\\n=== 案件統合分析結果 ===")
            for project_id, analysis in context_analysis.items():
                context_parts.append(
                    f"案件ID: {project_id}\\n"
                    f"総合ステータス: {analysis.get('overall_status', '不明')}\\n"
                    f"総合リスク: {analysis.get('overall_risk', '不明')}\\n"
                    f"現在工程: {analysis.get('current_phase', '不明')}\\n"
                    f"進捗傾向: {analysis.get('progress_trend', '不明')}\\n"
                    f"問題継続性: {analysis.get('issue_continuity', '不明')}\\n"
                    f"分析サマリ: {analysis.get('analysis_summary', '')}\\n"
                )
                
                # 遅延理由管理情報
                delay_reasons = analysis.get('delay_reasons_management', [])
                if delay_reasons:
                    context_parts.append(f"現在の遅延理由・問題:")
                    for reason in delay_reasons[:3]:  # 上位3件
                        context_parts.append(
                            f"  - {reason.get('delay_category', '')}/{reason.get('delay_subcategory', '')}: "
                            f"{reason.get('description', '')} (ステータス: {reason.get('status', '')})"
                        )
                
                # 推奨アクション
                actions = analysis.get('recommended_actions', [])
                if actions:
                    context_parts.append(f"推奨アクション: {', '.join(actions[:3])}")
                
                context_parts.append("---")
        
        # フォールバック: ベクター検索で結果が少ない場合は最新レポートも追加
        if len([p for p in context_parts if not p.startswith("=== 案件統合分析結果")]) < 3:
            for i, report in enumerate(reports[:5]):
                if report.analysis_result:
                    context_parts.append(
                        f"最新レポート{i+1}: {report.file_name}\\n"
                        f"要約: {report.analysis_result.summary}\\n"
                        f"リスクレベル: {getattr(report, 'risk_level', '不明')}\\n"
                        f"問題: {', '.join(report.analysis_result.issues)}\\n"
                    )
        
        context = "\\n".join(context_parts)
        
        # LLMにストリーミング質問（シングルトンインスタンス使用）
        llm_service = get_llm_service()
        yield from llm_service.answer_question_stream(question, context)
        
    except Exception as e:
        yield f"申し訳ございませんが、回答の生成中にエラーが発生しました: {str(e)}"

def render_similarity_search():
    """類似ケース検索を表示"""
    st.markdown("<div class='custom-header'>類似ケース検索</div>", unsafe_allow_html=True)
    
    # 検索クエリ入力
    search_query = st.text_input(
        "検索したい内容を入力してください:",
        placeholder="例: 住民反対による工事停止"
    )
    
    # 検索フィルター
    col1, col2 = st.columns(2)
    with col1:
        max_results = st.slider("最大表示件数", 1, 20, 5)
    with col2:
        similarity_threshold = st.slider("類似度閾値", 0.0, 1.0, 0.5)
    
    if st.button("🔍 検索実行"):
        if search_query:
            with st.spinner("類似ケースを検索中..."):
                results = search_similar_cases(search_query, max_results)
                
                if results:
                    st.write(f"**{len(results)}件の類似ケースが見つかりました:**")
                    
                    for i, result in enumerate(results, 1):
                        distance = result.get('distance', 0.0)
                        similarity_score = 1.0 / (1.0 + distance / 100.0)
                        with st.expander(f"{i}. {result['metadata'].get('file_name', '不明')} (類似度: {similarity_score:.3f})"):
                            st.write("**内容:**")
                            st.text(result['content'][:500] + "..." if len(result['content']) > 500 else result['content'])
                            
                            st.write("**メタデータ:**")
                            metadata = result['metadata']
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"ファイル名: {metadata.get('file_name', '不明')}")
                                st.write(f"レポート種別: {metadata.get('report_type', '不明')}")
                            with col2:
                                st.write(f"リスクレベル: {metadata.get('risk_level', '不明')}")
                                st.write(f"緊急度: {metadata.get('urgency_score', '不明')}")
                else:
                    st.info("類似ケースが見つかりませんでした。")
        else:
            st.warning("検索クエリを入力してください。")

def search_similar_cases(query: str, max_results: int) -> List[Dict[str, Any]]:
    """類似ケースを検索"""
    try:
        vector_store = VectorStoreService()
        results = vector_store.search_similar_documents(query, max_results)
        return results
    except Exception as e:
        st.error(f"検索エラー: {str(e)}")
        return []

def render_trend_analysis(reports: List[DocumentReport]):
    """トレンド分析を表示"""
    st.markdown("<div class='custom-header'>トレンド分析</div>", unsafe_allow_html=True)
    
    if not reports:
        st.info("分析するデータがありません。")
        return
    
    # 期間選択
    analysis_period = st.selectbox(
        "分析期間を選択:",
        ["過去7日間", "過去30日間", "過去90日間", "全期間"]
    )
    
    # 期間に基づくデータフィルタリング
    filtered_reports = filter_reports_by_period(reports, analysis_period)
    
    # トレンドチャート
    col1, col2 = st.columns(2)
    
    with col1:
        render_issue_trend_chart(filtered_reports)
    
    with col2:
        render_urgency_trend_chart(filtered_reports)
    
    # 詳細統計
    render_trend_statistics(filtered_reports)

def filter_reports_by_period(reports: List[DocumentReport], period: str) -> List[DocumentReport]:
    """期間でレポートをフィルタリング"""
    now = datetime.now()
    
    if period == "過去7日間":
        cutoff = now - timedelta(days=7)
    elif period == "過去30日間":
        cutoff = now - timedelta(days=30)
    elif period == "過去90日間":
        cutoff = now - timedelta(days=90)
    else:  # 全期間
        return reports
    
    return [r for r in reports if r.created_at >= cutoff]

def render_issue_trend_chart(reports: List[DocumentReport]):
    """問題発生トレンドチャートを表示"""
    st.write("**問題発生トレンド**")
    
    # 日別の問題数を集計
    daily_issues = {}
    for report in reports:
        date = report.created_at.date()
        if report.analysis_result and report.analysis_result.issues:
            issue_count = len(report.analysis_result.issues)
            daily_issues[date] = daily_issues.get(date, 0) + issue_count
    
    if daily_issues:
        df = pd.DataFrame([
            {"日付": date, "問題数": count}
            for date, count in sorted(daily_issues.items())
        ])
        
        fig = px.line(
            df, 
            x="日付", 
            y="問題数",
            title="日別問題発生数",
            markers=True
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("問題データがありません。")

def render_urgency_trend_chart(reports: List[DocumentReport]):
    """緊急度トレンドチャートを表示"""
    st.write("**緊急度トレンド**")
    
    # 日別の平均緊急度を集計
    daily_urgency = {}
    daily_counts = {}
    
    for report in reports:
        date = report.created_at.date()
        if report.analysis_result:
            urgency = getattr(report, 'urgency_score', 0)
            daily_urgency[date] = daily_urgency.get(date, 0) + urgency
            daily_counts[date] = daily_counts.get(date, 0) + 1
    
    if daily_urgency:
        # 平均緊急度を計算
        avg_urgency = {
            date: daily_urgency[date] / daily_counts[date]
            for date in daily_urgency
        }
        
        df = pd.DataFrame([
            {"日付": date, "平均緊急度": urgency}
            for date, urgency in sorted(avg_urgency.items())
        ])
        
        fig = px.line(
            df,
            x="日付",
            y="平均緊急度",
            title="日別平均緊急度",
            markers=True,
            range_y=[0, 10]
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("緊急度データがありません。")

def render_trend_statistics(reports: List[DocumentReport]):
    """トレンド統計を表示"""
    st.write("**統計サマリー**")
    
    if not reports:
        st.info("統計データがありません。")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_reports = len(reports)
        st.metric("総レポート数", total_reports)
    
    with col2:
        avg_urgency = sum(
            getattr(r, 'urgency_score', 0)
            for r in reports
        ) / len(reports)
        st.metric("平均緊急度", f"{avg_urgency:.1f}")
    
    with col3:
        high_urgency_count = len([
            r for r in reports
            if getattr(r, 'urgency_score', 0) >= 7
        ])
        st.metric("高緊急度案件", high_urgency_count)
    
    with col4:
        emergency_flags = len([
            r for r in reports
            if FlagType.EMERGENCY_STOP in r.flags
        ])
        st.metric("緊急停止案件", emergency_flags)

def render_realtime_analysis():
    """リアルタイム分析を表示"""
    st.markdown("<div class='custom-header'>リアルタイム分析</div>", unsafe_allow_html=True)
    
    st.write("**新しい文書をアップロードして即座に分析**")
    
    # ファイルアップロード
    uploaded_file = st.file_uploader(
        "分析したいファイルをアップロード",
        type=['txt', 'pdf', 'docx'],
        help="テキスト、PDF、Wordファイルをサポートしています"
    )
    
    if uploaded_file is not None:
        with st.spinner("ファイルを分析中..."):
            # ファイル内容を読み込み
            if uploaded_file.type == "text/plain":
                content = str(uploaded_file.read(), "utf-8")
            else:
                content = "ファイル内容の読み込みに対応していません（デモ版）"
            
            # LLM分析を実行（シングルトンインスタンス使用）
            try:
                llm_service = get_llm_service()
                analysis_result = llm_service.analyze_document(content)
                anomaly_result = llm_service.detect_anomaly(content)
                
                # 結果表示
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**分析結果**")
                    st.json(analysis_result)
                
                with col2:
                    st.write("**異常検知結果**")
                    st.json(anomaly_result)
                
                # 文書内容プレビュー
                st.write("**文書内容プレビュー**")
                st.text_area("内容", content[:1000] + "..." if len(content) > 1000 else content, height=200)
                
            except Exception as e:
                st.error(f"分析エラー: {str(e)}")
    
    # 監視設定
    st.write("**リアルタイム監視設定**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        monitor_enabled = st.checkbox("SharePointフォルダ監視を有効化")
        refresh_interval = st.slider("更新間隔（秒）", 10, 300, 60)
    
    with col2:
        alert_threshold = st.slider("アラート緊急度しきい値", 1, 10, 7)
        auto_analysis = st.checkbox("自動分析を有効化")
    
    if monitor_enabled:
        st.info("📡 リアルタイム監視が有効です（デモ版では実際の監視は行われません）")
    
    # 手動更新ボタン
    if st.button("🔄 手動更新"):
        st.success("更新が完了しました！")
        st.rerun()