from app.tools.knowledge import knowledge_search
from app.tools.operations import service_restart
from app.tools.python_analysis import python_analysis
from app.tools.registry import ToolRegistry
from app.tools.schemas import (
    KnowledgeSearchArguments,
    PythonAnalysisArguments,
    ServiceRestartArguments,
    SqlReadArguments,
)
from app.tools.sql import sql_read


def create_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        "knowledge.search",
        knowledge_search,
        argument_model=KnowledgeSearchArguments,
        description=(
            "Search enterprise knowledge and troubleshooting "
            "documentation."
        ),
        risk_level="low",
        required_permission="knowledge.read",
    )

    registry.register(
        "sql.read",
        sql_read,
        argument_model=SqlReadArguments,
        description=(
            "Execute validated read-only SQL queries against "
            "enterprise operational data."
        ),
        risk_level="low",
        required_permission="data.read",
    )

    registry.register(
        "python.analysis",
        python_analysis,
        argument_model=PythonAnalysisArguments,
        description=(
            "Run controlled numerical analytics on structured data."
        ),
        risk_level="medium",
        required_permission="analytics.execute",
    )

    registry.register(
        "service.restart",
        service_restart,
        argument_model=ServiceRestartArguments,
        description=(
            "Restart an operational service. This is a high-risk "
            "action and requires approval."
        ),
        risk_level="high",
        required_permission="operations.restart",
    )

    return registry