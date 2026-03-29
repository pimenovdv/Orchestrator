from app.temporal.activities import (
    discover_root_agent_activity,
    build_execution_plan_activity,
    execute_agent_activity,
)


def test_activities_exist() -> None:
    assert discover_root_agent_activity is not None
    assert build_execution_plan_activity is not None
    assert execute_agent_activity is not None
