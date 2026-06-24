"""Tests unitarios para la atribución de buckets QA en time_metrics.

Valida la decisión JPDS WP-07h:
  - "Ready for QA" → cuello del dev (ready_for_qa_biz_hours, dentro de dev_resp)
  - "In QA" / "Testing" → tiempo de QA/Edgar (qa_biz_hours, excluido de dev_resp)
"""



from forge.etl.time_metrics import ACTIVE_QA_STATES, HANDOFF_QA_STATES, extract_time_metrics


def _ts(s: str) -> str:
    """ISO timestamp helper."""
    return s + "+00:00"


def _history(ts: str, from_status: str, to_status: str) -> dict:
    return {
        "created": ts,
        "author": {"displayName": "Tester"},
        "items": [
            {"field": "status", "fromString": from_status, "toString": to_status}
        ],
    }


def _issue(*histories: dict, created: str, resolutiondate: str | None = None) -> dict:
    return {
        "fields": {
            "created": created,
            "resolutiondate": resolutiondate,
        },
        "changelog": {"histories": list(histories)},
    }


class TestQaBucketSplit:
    """La tarjeta pasa Ready for QA (8h) → In QA (40h) → Done."""

    def test_ready_for_qa_goes_to_dev_bucket(self) -> None:
        issue = _issue(
            _history(_ts("2026-01-05T09:00:00"), "Backlog", "In Progress"),
            _history(_ts("2026-01-05T17:00:00"), "In Progress", "Ready for QA"),
            # 1 business day in Ready for QA (Mon→Tue morning)
            _history(_ts("2026-01-06T09:00:00"), "Ready for QA", "In QA"),
            # 1 business day in In QA
            _history(_ts("2026-01-07T09:00:00"), "In QA", "Done"),
            created=_ts("2026-01-05T09:00:00"),
        )
        m = extract_time_metrics(issue)

        assert m["ready_for_qa_biz_hours"] is not None
        assert m["ready_for_qa_biz_hours"] > 0, "Dev should have Ready for QA hours"

        assert m["qa_biz_hours"] is not None
        assert m["qa_biz_hours"] > 0, "QA should have In QA hours"

    def test_dev_resp_excludes_in_qa_time(self) -> None:
        """dev_resp = CT - In QA - Review. In QA no carga al dev."""
        issue = _issue(
            _history(_ts("2026-01-05T09:00:00"), "Backlog", "In Progress"),
            _history(_ts("2026-01-05T17:00:00"), "In Progress", "Ready for QA"),
            _history(_ts("2026-01-06T09:00:00"), "Ready for QA", "In QA"),
            _history(_ts("2026-01-07T09:00:00"), "In QA", "Done"),
            created=_ts("2026-01-05T09:00:00"),
        )
        m = extract_time_metrics(issue)

        ct = m["ct_biz_hours"]
        qa = m["qa_biz_hours"]
        dev_resp = m["dev_resp_biz_hours"]
        rfq = m["ready_for_qa_biz_hours"]

        assert ct is not None and qa is not None and dev_resp is not None

        # dev_resp = CT - In QA - review (Ready for QA permanece en dev_resp)
        expected = max(0, ct - (qa or 0))
        assert abs(dev_resp - expected) < 0.01, (
            f"dev_resp={dev_resp:.2f} debería ser CT({ct:.2f}) - qa({qa:.2f}) = {expected:.2f}"
        )

        # Ready for QA no se resta de dev_resp → dev_resp incluye rfq time
        assert rfq is not None and rfq > 0
        # Si rfq se restara, dev_resp sería CT - qa - rfq (más pequeño)
        dev_resp_if_rfq_subtracted = max(0, ct - (qa or 0) - (rfq or 0))
        assert dev_resp > dev_resp_if_rfq_subtracted - 0.01, (
            "Ready for QA no debería restarse de dev_resp"
        )

    def test_no_qa_at_all(self) -> None:
        """Tarjeta sin ningún estado QA — ambos buckets son None."""
        issue = _issue(
            _history(_ts("2026-01-05T09:00:00"), "Backlog", "In Progress"),
            _history(_ts("2026-01-07T09:00:00"), "In Progress", "Done"),
            created=_ts("2026-01-05T09:00:00"),
        )
        m = extract_time_metrics(issue)

        assert m["qa_biz_hours"] is None
        assert m["ready_for_qa_biz_hours"] is None
        assert m["dev_resp_biz_hours"] is not None  # CT sí existe

    def test_testing_state_goes_to_qa_bucket(self) -> None:
        """'Testing' (flujo PO/Design) cuenta como revisión activa, no como cuello del dev."""
        issue = _issue(
            _history(_ts("2026-01-05T09:00:00"), "Backlog", "In Progress"),
            _history(_ts("2026-01-06T09:00:00"), "In Progress", "Testing"),
            _history(_ts("2026-01-07T09:00:00"), "Testing", "Done"),
            created=_ts("2026-01-05T09:00:00"),
        )
        m = extract_time_metrics(issue)

        assert m["qa_biz_hours"] is not None and m["qa_biz_hours"] > 0
        assert m["ready_for_qa_biz_hours"] is None  # sin Ready for QA

        ct = m["ct_biz_hours"] or 0
        qa = m["qa_biz_hours"] or 0
        dev_resp = m["dev_resp_biz_hours"] or 0
        assert abs(dev_resp - max(0, ct - qa)) < 0.01


class TestYap721Synthetic:
    """Caso sintético de YAP-721: 2 entradas a QA con rebote."""

    def test_two_qa_rounds_both_counted(self) -> None:
        """
        Flujo: In Progress → In Review → Ready for QA (8h) → In QA (3d, rebote) →
               In Progress → In Review → Ready for QA (8d) → In QA (2d) → Done
        Cada periodo debe sumar en su bucket correcto.
        """
        issue = _issue(
            _history(_ts("2026-04-24T02:29:00"), "Backlog", "Ready"),
            _history(_ts("2026-04-24T02:33:46"), "Ready", "In Progress"),
            _history(_ts("2026-04-24T02:33:54"), "In Progress", "In Review"),
            _history(_ts("2026-04-24T02:33:58"), "In Review", "Ready for QA"),
            _history(_ts("2026-04-24T11:07:10"), "Ready for QA", "In QA"),
            _history(_ts("2026-04-27T08:59:19"), "In QA", "In Progress"),    # rebote
            _history(_ts("2026-05-03T09:43:55"), "In Progress", "In Review"),
            _history(_ts("2026-05-03T09:44:59"), "In Review", "Ready for QA"),
            _history(_ts("2026-05-11T15:37:12"), "Ready for QA", "In QA"),
            _history(_ts("2026-05-13T12:26:10"), "In QA", "Done"),
            created=_ts("2026-04-24T02:29:00"),
        )
        m = extract_time_metrics(issue)

        # Ambos periodos de QA deben sumarse
        assert m["qa_biz_hours"] is not None
        assert m["qa_biz_hours"] > 0

        # Ambos periodos de Ready for QA deben sumarse
        assert m["ready_for_qa_biz_hours"] is not None
        assert m["ready_for_qa_biz_hours"] > 0

        # dev_resp = CT - total_in_qa - review (sin Ready for QA)
        ct = m["ct_biz_hours"] or 0
        qa = m["qa_biz_hours"] or 0
        dev_resp = m["dev_resp_biz_hours"] or 0
        assert abs(dev_resp - max(0, ct - qa)) < 0.01

        # El tiempo de In QA no contamina al dev
        assert dev_resp < ct  # dev_resp debe ser menor que CT total

    def test_qa_biz_hours_matches_recomputed_value(self) -> None:
        """
        Los valores del recompute real de YAP-721 deben coincidir con los del script.
        ready_for_qa_biz_hours ≈ 47.74h, qa_biz_hours ≈ 19.7h.
        """
        issue = _issue(
            _history(_ts("2026-04-24T02:29:00"), "Backlog", "Ready"),
            _history(_ts("2026-04-24T02:33:46"), "Ready", "In Progress"),
            _history(_ts("2026-04-24T02:33:54"), "In Progress", "In Review"),
            _history(_ts("2026-04-24T02:33:58"), "In Review", "Ready for QA"),
            _history(_ts("2026-04-24T11:07:10"), "Ready for QA", "In QA"),
            _history(_ts("2026-04-27T08:59:19"), "In QA", "In Progress"),
            _history(_ts("2026-05-03T09:43:55"), "In Progress", "In Review"),
            _history(_ts("2026-05-03T09:44:59"), "In Review", "Ready for QA"),
            _history(_ts("2026-05-11T15:37:12"), "Ready for QA", "In QA"),
            _history(_ts("2026-05-13T12:26:10"), "In QA", "Done"),
            created=_ts("2026-04-24T02:29:00"),
        )
        m = extract_time_metrics(issue)

        # Verificar rangos razonables (exactos pueden variar por timezone del server)
        assert 40 < (m["ready_for_qa_biz_hours"] or 0) < 60, "Ready for QA debería ser ~47h"
        assert 15 < (m["qa_biz_hours"] or 0) < 30, "In QA debería ser ~19h"
        assert 70 < (m["dev_resp_biz_hours"] or 0) < 90, "dev_resp debería ser ~79h"


class TestStateConstants:
    def test_handoff_states_defined(self) -> None:
        assert "Ready for QA" in HANDOFF_QA_STATES

    def test_active_qa_states_defined(self) -> None:
        assert "In QA" in ACTIVE_QA_STATES
        assert "Testing" in ACTIVE_QA_STATES

    def test_no_overlap_between_handoff_and_active(self) -> None:
        assert not set(HANDOFF_QA_STATES) & set(ACTIVE_QA_STATES), (
            "HANDOFF_QA_STATES y ACTIVE_QA_STATES no deben tener estados en común"
        )
