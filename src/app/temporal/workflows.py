import asyncio
from datetime import timedelta
from typing import Any, Dict, List

from temporalio import workflow
from app.models.api import ExecuteRequest
from app.models.manifest import AgentManifest, ExecutionLimits

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import (
        discover_root_agent_activity,
        build_execution_plan_activity,
        execute_agent_activity,
        get_agent_manifest_activity,
    )


@workflow.defn(name="OrchestratorWorkflow")
class OrchestratorWorkflow:
    @workflow.run
    async def run(self, query: str) -> Dict[str, Any]:
        """
        Main workflow that orchestrates the execution of agents.
        """
        # 1. Find root agent
        root_agent_id: str = await workflow.execute_activity(
            discover_root_agent_activity,
            query,
            start_to_close_timeout=timedelta(seconds=10),
        )

        # 2. Build DAG plan (Execution Waves)
        waves: List[List[str]] = await workflow.execute_activity(
            build_execution_plan_activity,
            root_agent_id,
            start_to_close_timeout=timedelta(seconds=15),
        )

        # 3-5. Execute waves and collect state
        state_store: Dict[str, Any] = {}

        for wave_idx, wave in enumerate(waves):
            # Fetch real agent manifests concurrently
            manifest_tasks = [
                workflow.execute_activity(
                    get_agent_manifest_activity,
                    agent_id,
                    start_to_close_timeout=timedelta(seconds=10),
                )
                for agent_id in wave
            ]
            manifest_dicts = await asyncio.gather(*manifest_tasks)

            # We prepare the requests for the current wave
            requests: List[Dict[str, Any]] = []
            for agent_id, manifest_dict in zip(wave, manifest_dicts):
                # Construct input context based on previous agents' output
                input_context = state_store.copy()
                # Also include the original query
                input_context["_query"] = query

                # Load real manifest
                manifest = AgentManifest.model_validate(manifest_dict)

                req = ExecuteRequest(
                    execution_id=f"{workflow.info().workflow_id}-wave{wave_idx}-{agent_id}",
                    agent_manifest=manifest,
                    input_context=input_context,
                    execution_limits=ExecutionLimits(timeout_ms=30000, max_tokens=1000),
                )
                requests.append(req.model_dump(mode="json"))

            # Execute wave in parallel using asyncio.gather
            # temporalio workflow.execute_activity returns an awaitable
            wave_tasks = [
                workflow.execute_activity(
                    execute_agent_activity,
                    req,
                    start_to_close_timeout=timedelta(seconds=40),
                )
                for req in requests
            ]

            results = await asyncio.gather(*wave_tasks)

            # Collect results back into state_store
            for agent_id, result in zip(wave, results):
                state_store[agent_id] = result

        # 6. Return final result (the output of the last agent)
        # Assuming the root_agent_id is always the last in the final wave
        return {
            "final_output": state_store.get(root_agent_id),
            "state_store": state_store,
        }
