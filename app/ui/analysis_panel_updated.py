"""
効率的なRAG処理を実装した分析パネルUI
"""
import streamlit as st
import json
from typing import List, Dict, Any
from pathlib import Path

from app.models.report import DocumentReport
from app.services.llm_service import get_llm_service
from app.services.vector_store import VectorStoreService

def load_all_processed_reports() -> Dict[str, List[DocumentReport]]:
    """処理済み報告書を案件ID別に読み込み"""
    reports_by_project = {}
    processed_dir = Path("data/processed_reports")
    
    if not processed_dir.exists():
        return {}
    
    for report_file in processed_dir.glob("*.json"):
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            project_id = report_data.get('project_id')
            if project_id:
                if project_id not in reports_by_project:
                    reports_by_project[project_id] = []
                
                # DocumentReportオブジェクトに変換（簡易版）
                report = type('Report', (), {
                    'file_name': report_data.get('file_name', ''),
                    'project_id': project_id,
                    'content': report_data.get('content_preview', ''),
                    'analysis_result': type('Analysis', (), {
                        'summary': report_data.get('analysis_result', {}).get('summary', ''),
                        'issues': report_data.get('analysis_result', {}).get('issues', []),
                        'key_points': report_data.get('analysis_result', {}).get('key_points', [])
                    })(),
                    'risk_level': report_data.get('risk_level', '不明'),
                    'status_flag': report_data.get('status_flag', '不明')
                })()
                
                reports_by_project[project_id].append(report)
                
        except Exception as e:
            st.warning(f"報告書読み込みエラー: {report_file.name} - {e}")
    
    return reports_by_project

def process_qa_question_efficient(question: str, reports: List[DocumentReport]) -> str:
    """効率的なRAG処理による質問応答"""
    try:
        vector_store = VectorStoreService()
        
        # 🔍 Step 1: 統合分析結果から関連案件を検索
        context_results = vector_store.search_similar_documents(
            query=question,
            n_results=5,
            filter_metadata={'type': 'context_analysis'}  # 統合分析結果のみ検索
        )
        
        if not context_results:
            # フォールバック: 通常の報告書検索
            return _fallback_search(question, reports, vector_store)
        
        # 🎯 Step 2: 関連案件IDを特定
        related_project_ids = []
        context_parts = []
        
        for result in context_results:
            similarity_score = 1 - result.get('distance', 0.0)
            if similarity_score > 0.3:  # 類似度閾値
                metadata = result.get('metadata', {})
                project_id = metadata.get('project_id')
                
                if project_id and project_id not in related_project_ids:
                    related_project_ids.append(project_id)
                
                # 統合分析結果をコンテキストに追加
                context_parts.append(
                    f"=== 案件統合分析結果 ({project_id}) ===\\n"
                    f"類似度: {similarity_score:.3f}\\n"
                    f"総合ステータス: {metadata.get('overall_status', '不明')}\\n"
                    f"総合リスク: {metadata.get('overall_risk', '不明')}\\n"
                    f"現在工程: {metadata.get('current_phase', '不明')}\\n"
                    f"進捗傾向: {metadata.get('progress_trend', '不明')}\\n"
                    f"内容: {result.get('content', '')[:300]}...\\n"
                )
        
        # 📄 Step 3: 関連案件の全報告書を取得
        reports_by_project = load_all_processed_reports()
        
        for project_id in related_project_ids[:3]:  # 上位3案件
            if project_id in reports_by_project:
                project_reports = reports_by_project[project_id]
                context_parts.append(f"\\n=== 案件 {project_id} の関連報告書 ===")
                
                for i, report in enumerate(project_reports[:3]):  # 案件あたり上位3件
                    context_parts.append(
                        f"報告書{i+1}: {report.file_name}\\n"
                        f"要約: {report.analysis_result.summary}\\n"
                        f"リスクレベル: {report.risk_level}\\n"
                        f"問題: {', '.join(report.analysis_result.issues)}\\n"
                    )
        
        # 🤖 Step 4: LLMに質問
        context = "\\n".join(context_parts)
        llm_service = get_llm_service()
        answer = llm_service.answer_question(question, context)
        
        return answer
        
    except Exception as e:
        return f"申し訳ございませんが、回答の生成中にエラーが発生しました: {str(e)}"

def _fallback_search(question: str, reports: List[DocumentReport], vector_store: VectorStoreService) -> str:
    """フォールバック: 通常の報告書検索"""
    try:
        # 通常の報告書検索
        search_results = vector_store.search_similar_documents(
            query=question,
            n_results=8,
            filter_metadata={'type': {'$ne': 'context_analysis'}}  # 統合分析結果以外
        )
        
        context_parts = []
        for i, result in enumerate(search_results):
            similarity_score = 1 - result.get('distance', 0.0)
            if similarity_score > 0.3:
                metadata = result.get('metadata', {})
                content = result.get('content', '')
                
                context_parts.append(
                    f"関連文書{i+1} (類似度: {similarity_score:.3f}):\\n"
                    f"ファイル名: {metadata.get('file_name', '不明')}\\n"
                    f"レポート種別: {metadata.get('report_type', '不明')}\\n"
                    f"リスクレベル: {metadata.get('risk_level', '不明')}\\n"
                    f"内容: {content[:300]}...\\n"
                )
        
        context = "\\n".join(context_parts)
        llm_service = get_llm_service()
        return llm_service.answer_question(question, context)
        
    except Exception as e:
        return f"フォールバック検索でもエラーが発生しました: {str(e)}"

def render_efficient_qa_interface(reports: List[DocumentReport], use_streaming: bool = True):
    """効率的なRAG処理を使用した質問応答インターフェース"""
    st.markdown("<div class='custom-header'>建設工程について質問する（効率的RAG）</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>統合分析結果→関連案件の報告書を効率的に検索してAIが回答</p>", unsafe_allow_html=True)
    
    # 質問入力
    question = st.text_area(
        "質問を入力してください:",
        placeholder="例: MO0005の進捗状況はどうですか？\n例: 遅延が発生している案件はありますか？\n例: オーナー交渉で問題が起きている案件を教えて",
        height=100
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔍 質問する", type="primary", use_container_width=True):
            if question.strip():
                with st.spinner("効率的RAG処理で回答を生成中..."):
                    answer = process_qa_question_efficient(question, reports)
                
                st.markdown("### 💡 回答")
                st.info(answer)
                st.success("✅ 効率的RAGシステムによる回答が完了しました")
            else:
                st.warning("質問を入力してください。")
    
    with col2:
        st.markdown("**💡 効率的RAG処理の流れ:**")
        st.markdown("""
        1. 🔍 統合分析結果から関連案件を検索
        2. 🎯 関連案件IDを特定
        3. 📄 関連案件の全報告書を取得
        4. 🤖 統合分析結果＋関連報告書でLLM回答
        """)