from app.tools.factory import create_tool_registry


def test_registry_contains_approved_tools():
    registry = create_tool_registry()

    assert registry.list_tools() == [
        "knowledge.search",
        "python.analysis",
        "service.restart",
        "sql.read",
    ]


def test_registry_contains_tool_metadata():
    registry = create_tool_registry()

    knowledge = registry.get("knowledge.search")
    sql = registry.get("sql.read")
    python = registry.get("python.analysis")
    restart = registry.get("service.restart")

    assert knowledge.description
    assert knowledge.risk_level == "low"
    assert knowledge.required_permission == "knowledge.read"

    assert sql.description
    assert sql.risk_level == "low"
    assert sql.required_permission == "data.read"

    assert python.description
    assert python.risk_level == "medium"
    assert python.required_permission == "analytics.execute"

    assert restart.description
    assert restart.risk_level == "high"
    assert restart.required_permission == "operations.restart"


def test_registry_definitions_are_sorted_by_name():
    registry = create_tool_registry()

    definitions = registry.list_definitions()

    assert [definition.name for definition in definitions] == [
        "knowledge.search",
        "python.analysis",
        "service.restart",
        "sql.read",
    ]