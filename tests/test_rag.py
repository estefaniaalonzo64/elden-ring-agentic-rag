import pytest

from backend.tools.rag import search_elden_ring_knowledge


def test_query_vacia_devuelve_lista_vacia_sin_llamar_bigquery(fake_rag_backend):
    assert search_elden_ring_knowledge("") == []
    assert search_elden_ring_knowledge("   ") == []
    assert "query_text" not in fake_rag_backend


def test_query_normal_devuelve_resultados_con_rank_y_score(fake_rag_backend):
    results = search_elden_ring_knowledge("fast katana for an aggressive dexterity playstyle")

    assert [r.rank for r in results] == [1, 2]
    assert results[0].entity_type == "weapon"
    assert results[0].name == "Moonveil"
    assert results[0].score == pytest.approx(0.9)
    assert fake_rag_backend["query_text"] == "fast katana for an aggressive dexterity playstyle"


def test_top_k_se_propaga_al_vector_search(fake_rag_backend):
    search_elden_ring_knowledge("algo", top_k=1)
    assert fake_rag_backend["top_k"] == 1


def test_top_k_por_defecto_usa_rag_top_k_de_settings(fake_rag_backend):
    from backend.config import get_settings

    search_elden_ring_knowledge("algo")
    assert fake_rag_backend["top_k"] == get_settings().rag_top_k


def test_entity_type_filter_se_propaga_y_filtra(fake_rag_backend):
    results = search_elden_ring_knowledge("algo", entity_types=["ash"])
    assert fake_rag_backend["entity_types"] == ["ash"]
    assert all(r.entity_type == "ash" for r in results)


def test_resultados_incluyen_nombre_id_texto(fake_rag_backend):
    results = search_elden_ring_knowledge("algo")
    for r in results:
        assert r.entity_id
        assert r.name
        assert r.searchable_text
