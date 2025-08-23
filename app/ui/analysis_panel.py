"""
分析パネルUI
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime, timedelta

from app.models.report import DocumentReport, FlagType
from app.services.llm_service import get_llm_service
from app.services.vector_store import VectorStoreService

def render_analysis_panel(reports: List[DocumentReport]):
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
    render_qa_interface(reports, use_streaming, show_thinking)

def render_qa_interface(reports: List[DocumentReport], use_streaming: bool = True, show_thinking: bool = False):
    """質問応答インターフェースを表示"""
    st.markdown("<div class='custom-header'>建設工程について質問する</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>自然言語で建設工程や案件状況について質問し、関連報告書を検索してAIが回答</p>", unsafe_allow_html=True)
    
    # サンプル質問
    st.write("**サンプル質問:**")
    sample_questions = [
        "現在進行中のトラブル案件はありますか？",
        "最も緊急度の高い案件は何ですか？",
        "住民反対が発生している現場はありますか？",
        "工期遅延のリスクがある案件を教えてください",
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
            st.write("**🤖 RAGシステムによるAI回答:**")
            
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
                    relevant_docs = [r for r in search_results if (1 - r.get('distance', 0.0)) > 0.3]
                    if relevant_docs:
                        st.success(f"✅ {len(relevant_docs)}件の関連文書を発見")
                        
                        # 検索結果の詳細表示（オプション）
                        if show_thinking:
                            with st.expander("🔍 検索された関連文書"):
                                for i, result in enumerate(relevant_docs[:3]):
                                    similarity = 1 - result.get('distance', 0.0)
                                    metadata = result.get('metadata', {})
                                    st.write(f"**{i+1}. {metadata.get('file_name', '不明')}** (類似度: {similarity:.3f})")
                                    st.write(f"レポート種別: {metadata.get('report_type', '不明')}")
                                    st.write(f"内容抜粋: {result.get('content', '')[:150]}...")
                                    st.divider()
                    else:
                        st.warning("⚠️ 関連度の高い文書が見つからないため、最新レポートを使用")
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
                        answer = process_qa_question(question, reports)
                else:
                    with st.spinner("🤖 AIが回答を生成中..."):
                        answer = process_qa_question(question, reports)
                
                # 元のシンプルなinfo表示
                with response_placeholder.container():
                    st.info(answer)
                
                # 完了メッセージ
                st.success("✅ RAGシステムによる回答が完了しました")
        else:
            st.warning("質問を入力してください。")

def process_qa_question(question: str, reports: List[DocumentReport]) -> str:
    """質問応答を処理（RAGシステム）"""
    try:
        # 🔍 RAGシステム: 質問内容に基づいて関連文書を動的検索
        vector_store = VectorStoreService()
        search_results = vector_store.search_similar_documents(
            query=question, 
            n_results=8  # より多くの関連文書を検索
        )
        
        # 検索結果から高品質なコンテキストを構築
        context_parts = []
        
        if search_results:
            for i, result in enumerate(search_results):
                similarity_score = 1 - result.get('distance', 0.0)
                if similarity_score > 0.3:  # 類似度閾値でフィルタリング
                    metadata = result.get('metadata', {})
                    content = result.get('content', '')
                    
                    context_parts.append(
                        f"関連文書{i+1} (類似度: {similarity_score:.3f}):\\n"
                        f"ファイル名: {metadata.get('file_name', '不明')}\\n"
                        f"レポート種別: {metadata.get('report_type', '不明')}\\n"
                        f"リスクレベル: {metadata.get('risk_level', '不明')}\\n"
                        f"内容: {content[:300]}...\\n"
                    )
        
        # フォールバック: ベクター検索で結果が少ない場合は最新レポートも追加
        if len(context_parts) < 3:
            for i, report in enumerate(reports[:5]):
                if report.analysis_result:
                    context_parts.append(
                        f"最新レポート{i+1}: {report.file_name}\\n"
                        f"要約: {report.analysis_result.summary}\\n"
                        f"リスクレベル: {getattr(report, 'risk_level', '不明')}\\n"
                        f"問題: {', '.join(report.analysis_result.issues)}\\n"
                    )
        
        context = "\\n".join(context_parts)
        
        # LLMに質問（シングルトンインスタンス使用）
        llm_service = get_llm_service()
        answer = llm_service.answer_question(question, context)
        
        return answer
        
    except Exception as e:
        return f"申し訳ございませんが、回答の生成中にエラーが発生しました: {str(e)}"

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
        
        if search_results:
            for i, result in enumerate(search_results):
                similarity_score = 1 - result.get('distance', 0.0)
                if similarity_score > 0.3:  # 類似度閾値でフィルタリング
                    metadata = result.get('metadata', {})
                    content = result.get('content', '')
                    
                    context_parts.append(
                        f"関連文書{i+1} (類似度: {similarity_score:.3f}):\\n"
                        f"ファイル名: {metadata.get('file_name', '不明')}\\n"
                        f"レポート種別: {metadata.get('report_type', '不明')}\\n"
                        f"リスクレベル: {metadata.get('risk_level', '不明')}\\n"
                        f"内容: {content[:300]}...\\n"
                    )
        
        # フォールバック: ベクター検索で結果が少ない場合は最新レポートも追加
        if len(context_parts) < 3:
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
                        with st.expander(f"{i}. {result['metadata'].get('file_name', '不明')} (類似度: {1-result['distance']:.3f})"):
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