from app.tools.factory import create_tool_registry


def test_tool_definition_exposes_argument_schema():
    registry = create_tool_registry()

    definition = registry.get("knowledge.search")

    assert definition.argument_schema["type"] == "object"
    assert "query" in definition.argument_schema["properties"]
    assert "top_k" in definition.argument_schema["properties"]


def test_tool_registry_builds_llm_catalog():
    registry = create_tool_registry()

    catalog = registry.build_llm_catalog()

    assert len(catalog) == 4

    tool_names = {
        tool["name"]
        for tool in catalog
    }

    assert tool_names == {
        "knowledge.search",
        "sql.read",
        "python.analysis",
        "service.restart",
    }


def test_llm_catalog_contains_tool_contract():
    registry = create_tool_registry()

    catalog = registry.build_llm_catalog()

    restart_tool = next(
        tool
        for tool in catalog
        if tool["name"] == "service.restart"
    )

    assert restart_tool["risk_level"] == "high"
    assert restart_tool["required_permission"] == (
        "operations.restart"
    )

    assert restart_tool["parameters"]["type"] == "object"
    assert "service" in (
        restart_tool["parameters"]["properties"]
    )