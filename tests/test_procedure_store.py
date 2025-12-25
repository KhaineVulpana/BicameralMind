from core.memory.procedure_store import (
    ProcedureStore,
    Procedure,
    ProcedureStep,
    ProcedureStepType,
    ProcedureStatus,
)


def test_procedure_store_crud(tmp_path):
    path = tmp_path / "procedures.jsonl"
    store = ProcedureStore({"procedures": {"path": str(path)}})
    store.load()

    proc = Procedure(
        id="",
        title="Test Procedure",
        description="Test description",
        side="left",
        tags=["test", "unit"],
        steps=[
            ProcedureStep(step_type=ProcedureStepType.TEXT, text="Do something"),
            ProcedureStep(step_type=ProcedureStepType.TOOL, tool_name="local.echo", params_template={"text": "{msg}"}),
        ],
        status=ProcedureStatus.DRAFT,
    )

    created = store.create(proc)
    assert created.id
    assert store.get(created.id) is not None

    updated = store.update(created.id, {"status": "active", "tags": ["updated"]})
    assert updated is not None
    assert updated.status == ProcedureStatus.ACTIVE
    assert updated.tags == ["updated"]

    results = store.search("Test Procedure")
    assert any(p.id == created.id for p in results)

    removed = store.delete(created.id)
    assert removed
    assert store.get(created.id) is None
