"""
LLM機能の自動評価サービス
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

from app.models.report import DocumentReport, FlagType, RiskLevel
from app.config.settings import DATA_DIR

logger = logging.getLogger(__name__)

@dataclass
class EvaluationMetrics:
    """評価指標"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: Dict[str, int]

@dataclass
class EvaluationResult:
    """統合分析評価結果"""
    report_type_classification: EvaluationMetrics
    status_classification: EvaluationMetrics
    category_classification: EvaluationMetrics
    risk_level_assessment: EvaluationMetrics
    human_review_detection: EvaluationMetrics
    project_mapping: EvaluationMetrics
    overall_score: float

class EvaluationService:
    """LLM機能評価サービス"""
    
    def __init__(self):
        self.ground_truth_path = Path(DATA_DIR) / "evaluation" / "ground_truth.json"
        self.ground_truth = self._load_ground_truth()
    
    def _load_ground_truth(self) -> Dict[str, Any]:
        """正解データを読み込み"""
        try:
            with open(self.ground_truth_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Ground truth file not found: {self.ground_truth_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ground truth: {e}")
            return {}
    
    def evaluate_reports(self, reports: List[DocumentReport]) -> EvaluationResult:
        """統合分析結果を評価"""
        if not self.ground_truth:
            raise ValueError("Ground truth data not available")
        
        evaluation_data = self.ground_truth.get("evaluation_data", {})
        
        # 🎯 統合分析機能の評価
        report_type_metrics = self._evaluate_report_type_classification(reports, evaluation_data)
        status_metrics = self._evaluate_status_classification(reports, evaluation_data)
        category_metrics = self._evaluate_category_classification(reports, evaluation_data)
        risk_metrics = self._evaluate_risk_level_assessment(reports, evaluation_data)
        human_review_metrics = self._evaluate_human_review_detection(reports, evaluation_data)
        project_mapping_metrics = self._evaluate_project_mapping(reports, evaluation_data)
        
        # 総合スコア計算（重み付き平均）
        overall_score = (
            report_type_metrics.f1_score * 0.15 +
            status_metrics.f1_score * 0.25 +
            category_metrics.f1_score * 0.20 +
            risk_metrics.f1_score * 0.20 +
            human_review_metrics.f1_score * 0.10 +
            project_mapping_metrics.f1_score * 0.10
        )
        
        return EvaluationResult(
            report_type_classification=report_type_metrics,
            status_classification=status_metrics,
            category_classification=category_metrics,
            risk_level_assessment=risk_metrics,
            human_review_detection=human_review_metrics,
            project_mapping=project_mapping_metrics,
            overall_score=overall_score
        )
    
    def _evaluate_report_type_classification(self, reports: List[DocumentReport], 
                                           ground_truth: Dict[str, Any]) -> EvaluationMetrics:
        """レポートタイプ分類の評価"""
        predictions = []
        actuals = []
        
        for report in reports:
            filename = Path(report.file_path).name
            if filename in ground_truth:
                expected = ground_truth[filename]["expected_report_type"]
                predicted = report.report_type.value if report.report_type else "OTHER"
                
                predictions.append(predicted)
                actuals.append(expected)
        
        return self._calculate_metrics(predictions, actuals, "report_type_classification")
    
    def _evaluate_status_classification(self, reports: List[DocumentReport], 
                                      ground_truth: Dict[str, Any]) -> EvaluationMetrics:
        """状態分類の評価（統合分析版）"""
        predictions = []
        actuals = []
        
        for report in reports:
            filename = Path(report.file_path).name
            if filename in ground_truth:
                expected = ground_truth[filename]["expected_status"]
                predicted = report.status_flag.value if report.status_flag else "unknown"
                
                predictions.append(predicted)
                actuals.append(expected)
        
        return self._calculate_metrics(predictions, actuals, "status_classification")
    
    def _evaluate_human_review_detection(self, reports: List[DocumentReport], 
                                       ground_truth: Dict[str, Any]) -> EvaluationMetrics:
        """分析困難検知の評価"""
        predictions = []
        actuals = []
        
        for report in reports:
            filename = Path(report.file_path).name
            if filename in ground_truth:
                expected = ground_truth[filename]["expected_requires_human_review"]
                predicted = getattr(report, 'requires_human_review', False)
                
                predictions.append(predicted)
                actuals.append(expected)
        
        return self._calculate_metrics(predictions, actuals, "human_review_detection")
    
    def _evaluate_category_classification(self, reports: List[DocumentReport],
                                        ground_truth: Dict[str, Any]) -> EvaluationMetrics:
        """カテゴリ分類の評価（統合分析版）"""
        predictions = []
        actuals = []
        
        for report in reports:
            filename = Path(report.file_path).name
            if filename in ground_truth:
                expected = set(ground_truth[filename]["expected_categories"])
                predicted = set([cat.value for cat in report.category_labels]) if report.category_labels else set()
                
                predictions.append(predicted)
                actuals.append(expected)
        
        return self._calculate_set_metrics(predictions, actuals, "category_classification")
    
    def _evaluate_risk_level_assessment(self, reports: List[DocumentReport],
                                      ground_truth: Dict[str, Any]) -> EvaluationMetrics:
        """リスクレベル評価の評価（統合分析版）"""
        predictions = []
        actuals = []
        
        for report in reports:
            filename = Path(report.file_path).name
            if filename in ground_truth:
                expected = ground_truth[filename]["expected_risk_level"]
                predicted = report.risk_level.value if report.risk_level else "不明"
                
                predictions.append(predicted)
                actuals.append(expected)
        
        return self._calculate_metrics(predictions, actuals, "risk_level_assessment")
    
    def _evaluate_project_mapping(self, reports: List[DocumentReport],
                                ground_truth: Dict[str, Any]) -> EvaluationMetrics:
        """プロジェクトマッピングの評価"""
        predictions = []
        actuals = []
        
        for report in reports:
            filename = Path(report.file_path).name
            if filename in ground_truth:
                expected = ground_truth[filename]["expected_project_id"]
                predicted = getattr(report, 'project_id', None) or "不明"
                
                predictions.append(predicted)
                actuals.append(expected)
        
        return self._calculate_metrics(predictions, actuals, "project_mapping")
    
    def _calculate_metrics(self, predictions: List[str], actuals: List[str], 
                          metric_name: str) -> EvaluationMetrics:
        """分類メトリクスを計算"""
        if not predictions or not actuals:
            return EvaluationMetrics(0.0, 0.0, 0.0, 0.0, {})
        
        # 正確性
        correct = sum(1 for p, a in zip(predictions, actuals) if p == a)
        accuracy = correct / len(predictions)
        
        # 各クラスごとのメトリクス計算
        unique_labels = set(predictions + actuals)
        
        precision_scores = []
        recall_scores = []
        
        confusion_matrix = {}
        
        for label in unique_labels:
            # True Positive, False Positive, False Negative
            tp = sum(1 for p, a in zip(predictions, actuals) if p == label and a == label)
            fp = sum(1 for p, a in zip(predictions, actuals) if p == label and a != label)
            fn = sum(1 for p, a in zip(predictions, actuals) if p != label and a == label)
            
            confusion_matrix[f"{label}_tp"] = tp
            confusion_matrix[f"{label}_fp"] = fp
            confusion_matrix[f"{label}_fn"] = fn
            
            # Precision and Recall
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            
            precision_scores.append(precision)
            recall_scores.append(recall)
        
        # マクロ平均
        avg_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0
        avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0
        
        # F1スコア
        f1_score = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall) \
                   if (avg_precision + avg_recall) > 0 else 0
        
        return EvaluationMetrics(
            accuracy=accuracy,
            precision=avg_precision,
            recall=avg_recall,
            f1_score=f1_score,
            confusion_matrix=confusion_matrix
        )
    
    def _calculate_set_metrics(self, predictions: List[set], actuals: List[set],
                              metric_name: str) -> EvaluationMetrics:
        """セット分類メトリクスを計算（マルチラベル分類用）"""
        if not predictions or not actuals:
            return EvaluationMetrics(0.0, 0.0, 0.0, 0.0, {})
        
        accuracies = []
        precisions = []
        recalls = []
        
        for pred_set, actual_set in zip(predictions, actuals):
            if not actual_set and not pred_set:
                # 両方空の場合は完全一致
                accuracies.append(1.0)
                precisions.append(1.0)
                recalls.append(1.0)
            elif not actual_set:
                # 正解が空だが予測がある場合
                accuracies.append(0.0)
                precisions.append(0.0)
                recalls.append(1.0)  # 何も予測すべきでないので recall は 1
            elif not pred_set:
                # 予測が空だが正解がある場合
                accuracies.append(0.0)
                precisions.append(1.0)  # 何も予測していないので precision は 1
                recalls.append(0.0)
            else:
                # 両方に要素がある場合
                intersection = pred_set & actual_set
                union = pred_set | actual_set
                
                accuracy = len(intersection) / len(union) if union else 0
                precision = len(intersection) / len(pred_set) if pred_set else 0
                recall = len(intersection) / len(actual_set) if actual_set else 0
                
                accuracies.append(accuracy)
                precisions.append(precision)
                recalls.append(recall)
        
        avg_accuracy = sum(accuracies) / len(accuracies)
        avg_precision = sum(precisions) / len(precisions)
        avg_recall = sum(recalls) / len(recalls)
        
        f1_score = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall) \
                   if (avg_precision + avg_recall) > 0 else 0
        
        return EvaluationMetrics(
            accuracy=avg_accuracy,
            precision=avg_precision,
            recall=avg_recall,
            f1_score=f1_score,
            confusion_matrix={"set_comparison": len(predictions)}
        )
    
    def _calculate_binary_metrics(self, predictions: List[bool], actuals: List[bool],
                                 metric_name: str) -> EvaluationMetrics:
        """バイナリ分類メトリクスを計算"""
        if not predictions or not actuals:
            return EvaluationMetrics(0.0, 0.0, 0.0, 0.0, {})
        
        tp = sum(1 for p, a in zip(predictions, actuals) if p and a)
        fp = sum(1 for p, a in zip(predictions, actuals) if p and not a)
        fn = sum(1 for p, a in zip(predictions, actuals) if not p and a)
        tn = sum(1 for p, a in zip(predictions, actuals) if not p and not a)
        
        accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        confusion_matrix = {
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "true_negative": tn
        }
        
        return EvaluationMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            confusion_matrix=confusion_matrix
        )
    
    def evaluate_project_mapping(self, reports: List[DocumentReport]) -> EvaluationMetrics:
        """プロジェクトマッピング精度を評価"""
        predictions = []
        actuals = []
        mapping_methods = []
        confidence_scores = []
        
        for report in reports:
            file_name = report.file_name
            if file_name in self.ground_truth["evaluation_data"]:
                expected_data = self.ground_truth["evaluation_data"][file_name]
                
                # 実際の値
                actual_project_id = expected_data.get("expected_project_id")
                actual_method = expected_data.get("expected_mapping_method")
                
                # 予測値
                predicted_project_id = getattr(report, 'project_id', None)
                mapping_info = getattr(report, 'project_mapping_info', {})
                predicted_method = mapping_info.get('matching_method', 'unknown')
                confidence = mapping_info.get('confidence_score', 0.0)
                
                if actual_project_id:  # 正解データが存在する場合のみ評価
                    predictions.append(predicted_project_id)
                    actuals.append(actual_project_id)
                    mapping_methods.append(predicted_method)
                    confidence_scores.append(confidence)
        
        if not predictions:
            return EvaluationMetrics(0.0, 0.0, 0.0, 0.0, {})
        
        # プロジェクトID一致率
        correct_mappings = sum(1 for p, a in zip(predictions, actuals) if p == a)
        mapping_accuracy = correct_mappings / len(predictions)
        
        # 平均信頼度
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # メソッド別統計
        method_stats = {}
        for method in set(mapping_methods):
            method_predictions = [p for p, m in zip(predictions, mapping_methods) if m == method]
            method_actuals = [a for a, m in zip(actuals, mapping_methods) if m == method]
            method_confidence = [c for c, m in zip(confidence_scores, mapping_methods) if m == method]
            
            if method_predictions:
                method_correct = sum(1 for p, a in zip(method_predictions, method_actuals) if p == a)
                method_accuracy = method_correct / len(method_predictions)
                method_avg_confidence = sum(method_confidence) / len(method_confidence)
                
                method_stats[method] = {
                    'accuracy': method_accuracy,
                    'count': len(method_predictions),
                    'avg_confidence': method_avg_confidence
                }
        
        return EvaluationMetrics(
            accuracy=mapping_accuracy,
            precision=avg_confidence,  # 信頼度をprecisionとして使用
            recall=0.0,  # プロジェクトマッピングでは使用しない
            f1_score=0.0,  # プロジェクトマッピングでは使用しない
            confusion_matrix=method_stats
        )