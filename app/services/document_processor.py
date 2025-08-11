"""
文書処理サービス
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from docx import Document
try:
    import PyPDF2
except ImportError:
    try:
        import pypdf as PyPDF2
    except ImportError:
        PyPDF2 = None

from openpyxl import load_workbook

from app.models.report import DocumentReport, ReportType, AnalysisResult, AnomalyDetection
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService
from app.config.settings import SHAREPOINT_DOCS_DIR

logger = logging.getLogger(__name__)

if PyPDF2 is None:
    logger.warning("PyPDF2/pypdf not available. PDF reading will be disabled.")

class DocumentProcessor:
    """文書処理クラス"""
    
    def __init__(self, llm_provider: Optional[str] = None, create_vector_store: bool = False):
        self.llm_service = LLMService(provider=llm_provider)
        self.vector_store = VectorStoreService(create_mode=create_vector_store)
        
    def process_directory(self, directory_path: Path) -> List[DocumentReport]:
        """ディレクトリ内の全文書を処理"""
        reports = []
        
        # サポートされているファイル拡張子
        supported_extensions = {'.txt', '.pdf', '.docx', '.xlsx'}
        
        for file_path in directory_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    report = self.process_single_document(file_path)
                    if report:
                        reports.append(report)
                        logger.info(f"Processed: {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
        
        return reports
    
    def process_single_document(self, file_path: Path) -> Optional[DocumentReport]:
        """単一文書を処理（統合分析1回のみ）"""
        try:
            # ファイル内容を読み込み
            content = self._read_file_content(file_path)
            if not content:
                return None
            
            # 🤖 統合LLM分析を実行（レポートタイプ判定 + メイン分析 + 分類困難検知を1回で）
            llm_result = self.llm_service.analyze_document(content)
            if not llm_result:
                logger.error(f"統合LLM分析が失敗しました（フォールバック処理なし）: {file_path.name}")
                return None
            
            # DocumentReportオブジェクトを作成（統合分析結果を使用）
            report = self._create_report_from_unified_analysis(file_path, content, llm_result)
            
            # ベクターストアに追加
            self._add_to_vector_store(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return None
    
    def _read_file_content(self, file_path: Path) -> str:
        """ファイル内容を読み込み"""
        extension = file_path.suffix.lower()
        
        try:
            if extension == '.txt':
                return self._read_text_file(file_path)
            elif extension == '.pdf':
                return self._read_pdf_file(file_path)
            elif extension == '.docx':
                return self._read_docx_file(file_path)
            elif extension == '.xlsx':
                return self._read_xlsx_file(file_path)
            else:
                logger.warning(f"Unsupported file type: {extension}")
                return ""
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return ""
    
    def _read_text_file(self, file_path: Path) -> str:
        """テキストファイルを読み込み"""
        encodings = ['utf-8', 'shift_jis', 'euc-jp', 'iso-2022-jp']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # すべてのエンコーディングで失敗した場合
        logger.warning(f"Could not decode text file: {file_path}")
        return ""
    
    def _read_pdf_file(self, file_path: Path) -> str:
        """PDFファイルを読み込み"""
        if PyPDF2 is None:
            logger.warning(f"PDF reading not available for {file_path}")
            return "PDF読み込み機能が利用できません。PyPDF2またはpypdfをインストールしてください。"
        
        text = ""
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\\n"
        except Exception as e:
            logger.error(f"PDF reading failed: {e}")
        return text
    
    def _read_docx_file(self, file_path: Path) -> str:
        """Wordファイルを読み込み"""
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\\n"
        except Exception as e:
            logger.error(f"DOCX reading failed: {e}")
        return text
    
    def _read_xlsx_file(self, file_path: Path) -> str:
        """Excelファイルを読み込み"""
        text = ""
        try:
            workbook = load_workbook(file_path, data_only=True)
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                text += f"シート: {sheet_name}\\n"
                
                for row in sheet.iter_rows(values_only=True):
                    row_text = "\\t".join([str(cell) if cell is not None else "" for cell in row])
                    if row_text.strip():
                        text += row_text + "\\n"
        except Exception as e:
            logger.error(f"XLSX reading failed: {e}")
        return text
    
    def _create_report_from_unified_analysis(self, file_path: Path, content: str, llm_result: Dict[str, Any]) -> DocumentReport:
        """統合LLM分析結果からDocumentReportを作成"""
        from app.models.report import StatusFlag, CategoryLabel, RiskLevel
        from app.services.project_mapper import ProjectMapper
        
        # レポートタイプの設定
        report_type_str = llm_result.get('report_type', 'OTHER')
        try:
            report_type = ReportType(report_type_str)
        except ValueError:
            logger.warning(f"無効なレポートタイプ: {report_type_str}、OTHERに設定")
            report_type = ReportType.OTHER
        
        # DocumentReportオブジェクトを作成
        report = DocumentReport(
            file_path=str(file_path),
            file_name=file_path.name,
            report_type=report_type,
            content=content,
            created_at=datetime.fromtimestamp(file_path.stat().st_mtime)
        )
        
        # 🤖 統合分析結果を設定
        report.requires_human_review = llm_result.get('requires_human_review', False)
        report.analysis_confidence = llm_result.get('analysis_confidence', 0.0)
        report.analysis_notes = llm_result.get('analysis_notes', '')
        
        # 🎯 プロジェクトマッピング（直接ID + ベクター検索）
        self._apply_project_mapping(report, llm_result)
        
        # 🏷️ 新フラグ体系の適用
        self._apply_unified_flag_system(report, llm_result)
        
        # 🔍 建設工程情報の設定
        report.current_construction_phase = llm_result.get('current_construction_phase', '不明')
        report.construction_progress = llm_result.get('construction_progress', {})
        
        # 📋 後方互換性のためのAnalysisResult作成
        report.analysis_result = AnalysisResult(
            project_info=llm_result.get('project_info', {}),
            status=llm_result.get('status', '不明'),
            issues=llm_result.get('issues', []),
            risk_level=llm_result.get('risk_level', '低'),
            recommended_flags=llm_result.get('category_labels', []),  # 後方互換性
            summary=llm_result.get('summary', '分析結果なし'),
            urgency_score=llm_result.get('urgency_score', 1),
            key_points=llm_result.get('key_points', []),
            confidence=report.analysis_confidence
        )
        
        # 🚨 異常検知の統合（分析困難度として扱う）
        report.anomaly_detection = AnomalyDetection(
            is_anomaly=report.requires_human_review,
            anomaly_description=f"LLMによる分析困難度: {'要確認' if report.requires_human_review else '正常'}",
            confidence=report.analysis_confidence,
            suggested_action="手動確認を推奨" if report.requires_human_review else "自動分析完了",
            requires_human_review=report.requires_human_review,
            similar_cases=[]
        )
        
        return report
    
    def _add_to_vector_store(self, report: DocumentReport) -> bool:
        """ベクターストアに文書を追加"""
        metadata = {
            'file_name': report.file_name,
            'file_path': report.file_path,
            'report_type': report.report_type.value,
            'created_at': report.created_at.isoformat(),
            'risk_level': report.analysis_result.risk_level if report.analysis_result else '低',
            'urgency_score': report.analysis_result.urgency_score if report.analysis_result else 1
        }
        
        return self.vector_store.add_document(report.content, metadata)
    
    def _apply_project_mapping(self, report: DocumentReport, llm_result: Dict[str, Any]):
        """プロジェクトマッピングを適用（直接ID + ベクター検索）"""
        try:
            from app.services.project_mapper import ProjectMapper
            
            # 🎯 マルチ戦略プロジェクトマッピング
            project_mapper = ProjectMapper()
            mapping_result = project_mapper.map_project(report.content, llm_result)
            
            if mapping_result.project_id:
                report.project_id = mapping_result.project_id
                logger.info(f"Mapped project_id: {mapping_result.project_id} "
                          f"(confidence: {mapping_result.confidence_score:.2f}, "
                          f"method: {mapping_result.matching_method}) for {report.file_name}")
                
                # マッピング詳細情報を保存
                report.project_mapping_info = {
                    'confidence_score': mapping_result.confidence_score,
                    'matching_method': mapping_result.matching_method,
                    'alternative_candidates': mapping_result.alternative_candidates,
                    'extracted_info': mapping_result.extracted_info
                }
                
                # 低信頼度の場合は検証が必要としてマーク
                if mapping_result.confidence_score < 0.7:
                    report.has_unexpected_values = True
                    report.validation_issues.append(f"低信頼度プロジェクトマッピング: {mapping_result.confidence_score:.2f}")
                    
            else:
                report.project_id = None
                logger.warning(f"Failed to map project for {report.file_name}")
                report.has_unexpected_values = True
                report.validation_issues.append("プロジェクトマッピング失敗")
                
        except Exception as e:
            logger.error(f"プロジェクトマッピング失敗: {e}")
            report.project_id = None
            report.has_unexpected_values = True
            report.validation_issues.append(f"プロジェクトマッピングエラー: {str(e)}")
    
    def _apply_unified_flag_system(self, report: DocumentReport, llm_result: Dict[str, Any]):
        """統合分析結果から新フラグ体系を適用"""
        try:
            from app.models.report import StatusFlag, CategoryLabel, RiskLevel
            
            # 🚨 想定外値フラグを初期化
            report.has_unexpected_values = False
            report.validation_issues = []
            
            # StatusFlag設定
            llm_status_flag = llm_result.get('status_flag')
            if llm_status_flag and llm_status_flag in [e.value for e in StatusFlag]:
                report.status_flag = StatusFlag(llm_status_flag)
            else:
                report.status_flag = None
                report.has_unexpected_values = True
                if llm_status_flag:
                    report.validation_issues.append(f"StatusFlag: 無効値 '{llm_status_flag}'")
                else:
                    report.validation_issues.append("StatusFlag: LLM出力なし")
            
            # CategoryLabel設定
            llm_category_labels = llm_result.get('category_labels', [])
            categories = []
            if llm_category_labels and isinstance(llm_category_labels, list):
                valid_category_values = [e.value for e in CategoryLabel]
                for cat in llm_category_labels:
                    if cat in valid_category_values:
                        categories.append(CategoryLabel(cat))
                    else:
                        report.has_unexpected_values = True
                        report.validation_issues.append(f"CategoryLabel: 無効値 '{cat}'")
            else:
                report.has_unexpected_values = True
                report.validation_issues.append("CategoryLabel: LLM出力なし")
            
            report.category_labels = categories if categories else None
            
            # RiskLevel設定
            risk_level_str = llm_result.get('risk_level')
            if risk_level_str:
                if risk_level_str in ['高', 'HIGH']:
                    report.risk_level = RiskLevel.HIGH
                elif risk_level_str in ['中', 'MEDIUM']:
                    report.risk_level = RiskLevel.MEDIUM
                elif risk_level_str in ['低', 'LOW']:
                    report.risk_level = RiskLevel.LOW
                else:
                    report.risk_level = None
                    report.has_unexpected_values = True
                    report.validation_issues.append(f"RiskLevel: 無効値 '{risk_level_str}'")
            else:
                report.risk_level = None
                report.has_unexpected_values = True
                report.validation_issues.append("RiskLevel: LLM出力なし")
            
            # 🔍 想定外値の検出ログ
            if report.has_unexpected_values:
                logger.warning(f"🚨 想定外値検出: {report.file_name}")
                for issue in report.validation_issues:
                    logger.warning(f"  - {issue}")
            
            # 正常処理の場合のログ
            status_log = report.status_flag.value if report.status_flag else "None"
            categories_log = [c.value for c in report.category_labels] if report.category_labels else "None"
            risk_log = report.risk_level.value if report.risk_level else "None"
            logger.info(f"🎯 Applied flags: status={status_log}, categories={categories_log}, risk={risk_log}")
            
        except Exception as e:
            logger.error(f"統合フラグ体系適用失敗: {e}")
            # 🚨 エラー時も想定外として記録
            from app.models.report import StatusFlag, CategoryLabel, RiskLevel
            report.status_flag = None
            report.category_labels = None
            report.risk_level = None
            report.has_unexpected_values = True
            report.validation_issues = [f"フラグ体系適用エラー: {str(e)}"]