"""
ダミーデータ設定
0を指定すると実際の数値が使用される
"""

# 報告書監査用ダミー数値
REPORT_AUDIT_DUMMY = {
    # 基本数値
    "total_reports_in_folder": 1752,  # フォルダ内の全報告書数
    "analyzed_reports": 1732,         # 分析済み
    
    # 確認必須・推奨は実際の数値を使用（0のまま）
    "required_review": 0,             # 確認必須（実際の数値を使用）
    "recommended_review": 0,          # 確認推奨（実際の数値を使用）
    
    # 問題なしは自動計算される（analyzed_reports - required_review - recommended_review）
}

# 案件監査用ダミー数値
PROJECT_AUDIT_DUMMY = {
    # 基本数値
    "total_projects": 387,            # 全案件数
    "active_projects": 312,           # 進行中案件数（完了は除く）
    "completed_projects": 75,         # 完了案件数
    
    # ステータス別（0に設定すると実際の値を使用）
    "normal_projects": 0,             # 順調案件数（自動計算）
    "minor_delay_projects": 0,        # 軽微遅延案件数（実際の値を使用）
    "major_delay_projects": 0,        # 重大遅延案件数（実際の値を使用）
    "stopped_projects": 0,            # 停止案件数（実際の値を使用）
    "unknown_projects": 0,            # 不明案件数（実際の値を使用）
    
    # リスク別
    "high_risk_projects": 23,         # 高リスク案件数
    "medium_risk_projects": 89,       # 中リスク案件数
    "low_risk_projects": 200,         # 低リスク案件数
    
    # 緊急対応
    "urgent_projects": 12,            # 要緊急対応案件数
}

def get_dummy_value(category: str, key: str, actual_value: int) -> int:
    """
    ダミー値を取得する
    
    Args:
        category: "report" または "project"
        key: 設定キー
        actual_value: 実際の値
    
    Returns:
        ダミー値（0の場合は実際の値）
    """
    if category == "report":
        dummy_config = REPORT_AUDIT_DUMMY
    elif category == "project":
        dummy_config = PROJECT_AUDIT_DUMMY
    else:
        return actual_value
    
    dummy_value = dummy_config.get(key, 0)
    
    # 0の場合は実際の値を返す
    if dummy_value == 0:
        return actual_value
    else:
        return dummy_value

def calculate_no_issues_reports(analyzed_reports: int, required_review: int, recommended_review: int) -> int:
    """
    問題なし報告書数を計算する
    重複を考慮して計算
    """
    # 確認必須と確認推奨の重複を除いた合計を計算
    total_issues = required_review + recommended_review
    
    # 問題なし = 分析済み - 問題あり
    no_issues = max(0, analyzed_reports - total_issues)
    
    return no_issues

def get_report_audit_metrics(actual_metrics: dict) -> dict:
    """
    報告書監査用のメトリクスを取得（ダミー値適用）
    
    Args:
        actual_metrics: 実際のメトリクス辞書
    
    Returns:
        ダミー値が適用されたメトリクス辞書
    """
    # 基本数値の取得
    total_in_folder = get_dummy_value("report", "total_reports_in_folder", actual_metrics.get("total_in_folder", 0))
    analyzed = get_dummy_value("report", "analyzed_reports", actual_metrics.get("analyzed_reports", 0))
    
    # 確認必須・推奨は実際の値を使用
    required = get_dummy_value("report", "required_review", actual_metrics.get("required_review", 0))
    recommended = get_dummy_value("report", "recommended_review", actual_metrics.get("recommended_review", 0))
    
    # 問題なしを計算
    no_issues = calculate_no_issues_reports(analyzed, required, recommended)
    
    return {
        "total_in_folder": total_in_folder,
        "analyzed_reports": analyzed,
        "required_review": required,
        "recommended_review": recommended,
        "no_issues": no_issues
    }

def get_project_audit_metrics(actual_metrics: dict) -> dict:
    """
    案件監査用のメトリクスを取得（ダミー値適用）
    
    Args:
        actual_metrics: 実際のメトリクス辞書
    
    Returns:
        ダミー値が適用されたメトリクス辞書
    """
    # 基本数値（ダミー値適用）
    total_projects = get_dummy_value("project", "total_projects", actual_metrics.get("total_projects", 0))
    active_projects = get_dummy_value("project", "active_projects", actual_metrics.get("active_projects", 0))
    
    # ステータス別（実際の値を使用）
    stopped_projects = get_dummy_value("project", "stopped_projects", actual_metrics.get("stopped_count", 0))
    major_delay_projects = get_dummy_value("project", "major_delay_projects", actual_metrics.get("major_delay_count", 0))
    minor_delay_projects = get_dummy_value("project", "minor_delay_projects", actual_metrics.get("minor_delay_count", 0))
    unknown_projects = get_dummy_value("project", "unknown_projects", actual_metrics.get("unknown_count", 0))
    
    # 順調工程数は自動計算（active_projects - 停止 - 重大遅延 - 軽微遅延 - 不明）
    normal_projects = max(0, active_projects - stopped_projects - major_delay_projects - minor_delay_projects - unknown_projects)
    
    return {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "completed_projects": get_dummy_value("project", "completed_projects", actual_metrics.get("completed_projects", 0)),
        "normal_projects": normal_projects,  # 自動計算
        "minor_delay_projects": minor_delay_projects,
        "major_delay_projects": major_delay_projects,
        "stopped_projects": stopped_projects,
        "unknown_projects": unknown_projects,
        "high_risk_projects": get_dummy_value("project", "high_risk_projects", actual_metrics.get("high_risk_projects", 0)),
        "medium_risk_projects": get_dummy_value("project", "medium_risk_projects", actual_metrics.get("medium_risk_projects", 0)),
        "low_risk_projects": get_dummy_value("project", "low_risk_projects", actual_metrics.get("low_risk_projects", 0)),
        "urgent_projects": get_dummy_value("project", "urgent_projects", actual_metrics.get("urgent_projects", 0)),
    }
