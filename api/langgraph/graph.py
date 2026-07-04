"""
LangGraph 翻译工作流 — 有向图定义

工作流拓扑：
    
    extract_images
         │
         ▼
    translate_text ──→ translate_images
         │
         ▼
    check_risk ──→ calculate_finance ──→ generate_tags
         │                                    │
         └─────────── (manual) ────────────────┘
         │
         ▼
    (completed)
"""

from typing import Literal
from langgraph.graph import StateGraph, END

from api.langgraph.nodes import (
    node_extract_images,
    node_translate_text,
    node_translate_images,
    node_check_risk,
    node_calculate_finance,
    node_generate_tags,
    WorkflowState,
)

# ==================== 图定义 ====================

workflow = StateGraph(WorkflowState)

# 添加节点
workflow.add_node("extract_images", node_extract_images)
workflow.add_node("translate_text", node_translate_text)
workflow.add_node("translate_images", node_translate_images)
workflow.add_node("check_risk", node_check_risk)
workflow.add_node("calculate_finance", node_calculate_finance)
workflow.add_node("generate_tags", node_generate_tags)

# 设置入口点
workflow.set_entry_point("extract_images")

# 定义边
workflow.add_edge("extract_images", "translate_text")
workflow.add_edge("translate_text", "translate_images")
workflow.add_edge("translate_images", "check_risk")
workflow.add_edge("check_risk", "calculate_finance")
workflow.add_edge("calculate_finance", "generate_tags")
workflow.add_edge("generate_tags", END)

# 条件路由（风控结果）
def route_after_check_risk(state: WorkflowState) -> Literal["calculate_finance", "translate_text"]:
    """根据风控结果决定下一步"""
    if state.get("risk_status") == "manual":
        # 有风险 → 返回翻译节点重新处理
        return "translate_text"
    return "calculate_finance"

workflow.add_conditional_edges(
    "check_risk",
    route_after_check_risk,
    {"calculate_finance": "calculate_finance", "translate_text": "translate_text"},
)

# 编译工作流
translate_workflow = workflow.compile()


def run_translation_workflow(product_id: int, **kwargs) -> WorkflowState:
    """
    运行翻译工作流
    
    Args:
        product_id: 商品 ID
        **kwargs: 额外参数（title_zh, desc_zh, images 等）
        
    Returns:
        WorkflowState: 工作流输出状态
    """
    initial_state: WorkflowState = {
        "product_id": product_id,
        **kwargs,
        "title_th": None,
        "desc_th": None,
        "images": None,
        "risk_status": "pending",
        "risk_detail": None,
        "profit_thb": None,
        "profit_margin": None,
        "seo_tags": None,
        "translate_status": "processing",
        "error_message": None,
        "updated_at": None,
    }

    try:
        result = translate_workflow.invoke(initial_state)
        return result
    except Exception as e:
        return {
            **initial_state,
            "translate_status": "failed",
            "error_message": str(e),
        }


# ==================== 批量翻译 ====================

async def run_batch_translation(product_ids: list[int]) -> dict:
    """
    批量翻译工作流
    
    Args:
        product_ids: 商品 ID 列表
        
    Returns:
        dict: 批量翻译结果
    """
    results = {
        "total": len(product_ids),
        "success": 0,
        "failed": 0,
        "details": [],
    }

    for product_id in product_ids:
        try:
            result = run_translation_workflow(product_id=product_id)
            results["success"] += 1
            results["details"].append({
                "product_id": product_id,
                "status": "success",
                "risk_status": result.get("risk_status"),
                "profit_margin": result.get("profit_margin"),
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "product_id": product_id,
                "status": "failed",
                "error": str(e),
            })

    return results
