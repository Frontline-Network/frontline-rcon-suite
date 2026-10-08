"""Structured AI contract and capability checks with mocked providers only."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from discord_service.tests.test_service import setup_function, _seed, app, TestClient
from discord_service.app import report_reason as ai
from discord_service.app.report_reason_contract import (
    ReportReasonDecision,
    ReportReasonRequest,
)


def test_discord_shows_semantic_rationale_as_untrusted_text():
    from discord_service.app.report_admin_display import case_fields

    fields = case_fields(
        {
            "reason_analysis": {
                "decision": {
                    **decision().model_dump(),
                    "rationale": "@everyone <script> claimed **no voice**",
                }
            }
        },
        "en",
    )
    assert len(fields) == 1
    assert "AI report interpretation" in fields[0]["name"]
    assert "@everyone" not in fields[0]["value"]
    assert "<script>" not in fields[0]["value"]
    assert "SL no VOIP" in fields[0]["value"]


def test_classifying_report_does_not_claim_communication_already_proven():
    from discord_service.tests.test_service import _event
    from discord_service.app.contracts import IncidentEventEnvelope
    from discord_service.app.discord_client import render_message

    event = _event()
    event["incident"]["report_admin"] = {"status": "classifying", "rule": "pending"}
    rendered = str(render_message(IncidentEventEnvelope.model_validate(event), None))
    assert "AI reading complete report" in rendered
    assert "Communication reported" not in rendered


def job():
    return ReportReasonRequest(
        installation_id="11111111-1111-1111-1111-111111111111",
        incident_id="22222222-2222-2222-2222-222222222222",
        server_number=3,
        message="!admin Example SL no VOIP (he is back)",
        roster=[
            {
                "name": "Example",
                "team": "allies",
                "role": "Officer",
                "squad": "Able",
            }
        ],
        reporter_name="Reporter",
        reporter_team="allies",
        ai_provider="api_key",
        ai_model="configured-model",
        api_key="mock-secret-that-must-not-reach-prompt",
    )


def decision():
    return ReportReasonDecision(
        rule="communication",
        target_kind="player",
        target_text="Example",
        allegation_excerpt="SL no VOIP",
        unambiguous=True,
        uncertainties=[],
        rationale="Current report of no voice communication; return is background.",
    )


def test_full_context_and_strict_model_schema_no_tools_or_credentials_in_prompt():
    client = MagicMock()
    client.responses.parse.return_value = SimpleNamespace(
        status="completed", output_parsed=decision(), usage=None
    )
    with patch.object(ai, "OpenAI") as constructor:
        constructor.return_value.__enter__.return_value = client
        answer, _, _ = ai.analyze_report_reason(job())
    assert answer.rule == "communication"
    sent = client.responses.parse.call_args.kwargs
    assert sent["text_format"] is ReportReasonDecision
    assert sent["store"] is False and "tools" not in sent
    prompt = str(sent["input"])
    assert job().message in prompt
    assert job().api_key not in prompt and "must-not-reach-model" not in prompt
    data = json.loads(sent["input"][1]["content"])
    assert data["reporter"]["name"] == "Reporter"
    assert "negation" in sent["input"][0]["content"]
    assert "illustrative, not a list" in sent["input"][0]["content"]
    assert constructor.call_args.kwargs["max_retries"] == 0


@pytest.mark.parametrize(
    "state,output", [("incomplete", decision()), ("completed", None)]
)
def test_refusal_or_incomplete_output_is_not_a_decision(state, output):
    client = MagicMock()
    client.responses.parse.return_value = SimpleNamespace(
        status=state, output_parsed=output
    )
    with patch.object(ai, "OpenAI") as constructor:
        constructor.return_value.__enter__.return_value = client
        with pytest.raises(ValueError):
            ai.analyze_report_reason(job())


def test_codex_uses_existing_isolated_runtime_without_sending_key():
    request = job().model_copy(update={"ai_provider": "codex"})
    with patch.object(
        ai, "run_structured", return_value=decision().model_dump()
    ) as run:
        ai.analyze_report_reason(request)
    assert run.call_args.args[0] == request.installation_id
    assert request.api_key not in run.call_args.kwargs["prompt"]
    assert request.message in run.call_args.kwargs["prompt"]
    assert run.call_args.kwargs["priority"] is True
    assert run.call_args.kwargs["timeout_seconds"] == 35


def test_role_guidance_and_squad_semantics_are_sent_without_ids():
    request = job().model_copy(
        update={
            "ai_provider": "codex",
            "roster": [
                {
                    "name": "Example",
                    "team": "allies",
                    "role": "helicopterlogisticsofficer",
                    "squad": "charlie",
                    "leadership_role": "squadleader",
                }
            ],
        }
    )
    with patch.object(
        ai, "run_structured", return_value=decision().model_dump()
    ) as run:
        ai.analyze_report_reason(request)
    prompt = run.call_args.kwargs["prompt"]
    data = json.loads(prompt.split("UNTRUSTED REPORT DATA:\n", 1)[1])
    assert data["roster"][0]["leadership_role"] == "squadleader"
    assert "CHarlie no comms" in prompt and "kommder" in prompt
    assert "Short partial names" in prompt
    assert "still target_kind=player, including a misspelled full handle" in prompt
    assert "never an unrecognized player handle" in prompt
    assert "SHORT contiguous allegation phrase copied literally" in prompt


@pytest.mark.parametrize("fail", [False, True])
def test_authenticated_one_attempt_endpoint_never_posts_to_discord_or_rcon(
    fail, caplog
):
    capability = _seed()
    client = TestClient(app)
    payload = job().model_dump()
    with patch(
        "discord_service.app.main.analyze_report_reason",
        return_value=(decision(), 12, 9),
    ) as run:
        if fail:
            run.side_effect = RuntimeError("private-response-must-not-leak")
        assert client.post("/v1/report-reason", json=payload).status_code == 404
        run.assert_not_called()
        headers = {"Authorization": "Bearer " + capability}
        first = client.post("/v1/report-reason", headers=headers, json=payload)
        assert first.status_code == (503 if fail else 200)
        assert "private-response" not in first.text
        assert (
            client.post("/v1/report-reason", headers=headers, json=payload).status_code
            == 409
        )
        run.assert_called_once()
    assert "private-response-must-not-leak" not in caplog.text
    if fail:
        assert "Report reason analysis unavailable: RuntimeError" in caplog.text


def test_only_typed_pre_inference_busy_allows_later_admission():
    from discord_service.app.codex_runtime import CodexRuntimeBusy, CodexRuntimeError

    capability = _seed()
    client = TestClient(app)
    headers = {"Authorization": "Bearer " + capability}
    payload = job().model_dump()
    with patch(
        "discord_service.app.main.analyze_report_reason",
        side_effect=[CodexRuntimeBusy("codex_runtime_busy"), (decision(), 12, 9)],
    ) as analyze:
        busy = client.post("/v1/report-reason", headers=headers, json=payload)
        assert busy.status_code == 429
        assert busy.json()["detail"] == "report_reason_not_started_busy"
        assert busy.headers["Retry-After"] == "2"
        assert (
            client.post("/v1/report-reason", headers=headers, json=payload).status_code
            == 200
        )
        assert (
            client.post("/v1/report-reason", headers=headers, json=payload).status_code
            == 409
        )
        assert analyze.call_count == 2  # one refusal before inference, one analysis
    payload["incident_id"] = "different-incident"
    with patch(
        "discord_service.app.main.analyze_report_reason",
        side_effect=CodexRuntimeError("codex_runtime_busy"),
    ) as analyze:
        assert (
            client.post("/v1/report-reason", headers=headers, json=payload).status_code
            == 503
        )
        assert (
            client.post("/v1/report-reason", headers=headers, json=payload).status_code
            == 409
        )
        analyze.assert_called_once()  # a string match is not proof of no inference
