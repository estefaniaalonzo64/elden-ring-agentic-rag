import inspect

from backend.agent.agent import build_agent


def _tool_by_name(agent, name):
    return next(tool for tool in agent.tools if tool.__name__ == name)


def test_tools_registered_with_exact_contract_names(fake_player_profiles_db, fake_rag_backend):
    agent = build_agent("user-a", sources_sink=[])
    names = {tool.__name__ for tool in agent.tools}
    assert names == {
        "search_elden_ring_knowledge",
        "get_player_profile",
        "update_player_memory",
        "forget_player_memory",
    }


def test_tools_never_expose_user_id_as_a_parameter(fake_player_profiles_db, fake_rag_backend):
    agent = build_agent("user-a", sources_sink=[])
    for tool in agent.tools:
        assert "user_id" not in inspect.signature(tool).parameters


def test_get_player_profile_tool_is_bound_to_the_right_user(fake_player_profiles_db, fake_rag_backend):
    fake_player_profiles_db["user-a"] = {"preferences": {"playstyle": "aggressive"}, "stats": {}}
    fake_player_profiles_db["user-b"] = {"preferences": {"playstyle": "defensive"}, "stats": {}}

    agent_a = build_agent("user-a", sources_sink=[])
    tool_a = _tool_by_name(agent_a, "get_player_profile")

    assert tool_a() == {"preferences": {"playstyle": "aggressive"}, "stats": {}}


def test_update_player_memory_tool_writes_through_to_the_right_user(
    fake_player_profiles_db, fake_rag_backend
):
    agent = build_agent("user-a", sources_sink=[])
    tool = _tool_by_name(agent, "update_player_memory")

    tool(preferences_patch={"playstyle": "aggressive"})

    assert fake_player_profiles_db["user-a"]["preferences"]["playstyle"] == "aggressive"
    assert "user-b" not in fake_player_profiles_db


def test_search_tool_returns_plain_dicts_and_fills_sources_sink(
    fake_player_profiles_db, fake_rag_backend
):
    sources_sink: list[dict] = []
    agent = build_agent("user-a", sources_sink)
    tool = _tool_by_name(agent, "search_elden_ring_knowledge")

    results = tool("fast katana for an aggressive dexterity playstyle")

    assert results
    assert all(isinstance(r, dict) for r in results)
    assert sources_sink == results
