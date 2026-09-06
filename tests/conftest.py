import pytest


@pytest.fixture
def fake_users_db(monkeypatch):
    import backend.auth.service as auth_service

    users: dict[str, dict] = {}

    def fake_get_user_by_username(username):
        return users.get(username.strip().lower())

    def fake_create_user(username, password_hash, password_salt):
        user_id = f"user-{len(users) + 1}"
        users[username.strip().lower()] = {
            "user_id": user_id,
            "username": username,
            "password_hash": password_hash,
            "password_salt": password_salt,
        }
        return user_id

    monkeypatch.setattr(auth_service, "get_user_by_username", fake_get_user_by_username)
    monkeypatch.setattr(auth_service, "create_user", fake_create_user)

    return users


@pytest.fixture
def fake_player_profiles_db(monkeypatch):
    import backend.tools.memory as memory_tools

    profiles: dict[str, dict] = {}

    def _profile(user_id):
        return profiles.setdefault(user_id, {"preferences": {}, "stats": {}})

    def fake_get_player_profile(user_id):
        profile = _profile(user_id)
        return {"preferences": dict(profile["preferences"]), "stats": dict(profile["stats"])}

    def fake_update_player_profile(user_id, preferences_patch, stats_patch):
        profile = _profile(user_id)
        profile["preferences"].update(preferences_patch)
        profile["stats"].update(stats_patch)

    def fake_forget_player_fields(user_id, fields):
        profile = _profile(user_id)
        for field in fields:
            section, _, key = field.partition(".")
            profile.get(section, {}).pop(key, None)

    monkeypatch.setattr(memory_tools, "_get_player_profile", fake_get_player_profile)
    monkeypatch.setattr(memory_tools, "_update_player_profile", fake_update_player_profile)
    monkeypatch.setattr(memory_tools, "_forget_player_fields", fake_forget_player_fields)

    return profiles


@pytest.fixture
def fake_rag_backend(monkeypatch):
    import backend.tools.rag as rag_tools

    calls: dict = {}
    catalog = [
        {
            "entity_type": "weapon",
            "entity_id": "moonveil",
            "name": "Moonveil",
            "searchable_text": "A katana that unleashes a wave of light.",
            "distance": 0.1,
        },
        {
            "entity_type": "ash",
            "entity_id": "unsheathe",
            "name": "Unsheathe",
            "searchable_text": "An ash of war for katanas.",
            "distance": 0.3,
        },
    ]

    def fake_generate_query_embedding(query_text):
        calls["query_text"] = query_text
        return [0.1, 0.2, 0.3]

    def fake_vector_search(query_embedding, top_k, entity_types=None):
        calls["query_embedding"] = query_embedding
        calls["top_k"] = top_k
        calls["entity_types"] = entity_types
        rows = catalog
        if entity_types:
            rows = [row for row in rows if row["entity_type"] in entity_types]
        return rows[:top_k]

    monkeypatch.setattr(rag_tools, "generate_query_embedding", fake_generate_query_embedding)
    monkeypatch.setattr(rag_tools, "vector_search", fake_vector_search)

    return calls
