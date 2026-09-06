from backend.tools import memory


def test_guardar_preferencia(fake_player_profiles_db):
    profile = memory.update_player_memory(
        "user-a", preferences_patch={"preferred_weapon_types": ["katana"]}
    )
    assert profile["preferences"]["preferred_weapon_types"] == ["katana"]


def test_guardar_stats(fake_player_profiles_db):
    profile = memory.update_player_memory("user-a", stats_patch={"level": 85, "vigor": 40})
    assert profile["stats"] == {"level": 85, "vigor": 40}


def test_actualizar_preferencia_corrige_no_acumula(fake_player_profiles_db):
    memory.update_player_memory("user-a", preferences_patch={"preferred_combat_style": "arcane"})
    profile = memory.update_player_memory("user-a", preferences_patch={"preferred_combat_style": "melee"})
    assert profile["preferences"]["preferred_combat_style"] == "melee"


def test_olvidar_preferencia_borra_solo_el_campo_pedido(fake_player_profiles_db):
    memory.update_player_memory(
        "user-a",
        preferences_patch={"preferred_weapon_types": ["katana"], "playstyle": "aggressive"},
    )
    profile = memory.forget_player_memory("user-a", ["preferences.preferred_weapon_types"])
    assert "preferred_weapon_types" not in profile["preferences"]
    assert profile["preferences"]["playstyle"] == "aggressive"


def test_perfil_vacio_es_valido_sin_onboarding(fake_player_profiles_db):
    assert memory.get_player_profile("user-nuevo") == {"preferences": {}, "stats": {}}


def test_aislamiento_usuario_a_no_ve_memoria_de_b(fake_player_profiles_db):
    memory.update_player_memory("user-a", preferences_patch={"playstyle": "aggressive"})
    assert memory.get_player_profile("user-b") == {"preferences": {}, "stats": {}}
