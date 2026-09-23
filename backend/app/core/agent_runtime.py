from typing import Any

from agents import Agent, Model, ModelSettings, RunConfig, Runner, RunResult
from openai.types.shared import Reasoning

from app.config import Settings
from app.core.context import RunContext
from app.core.contracts import DomainModule
from app.core.tooling import instrument_tools


class AgentRuntime:
    def __init__(self, domain: DomainModule, settings: Settings, model: str | Model) -> None:
        self._domain = domain
        self._model = model
        self._output_model = domain.agent_output_model
        self._tools = instrument_tools(domain.tools, settings)

    def build_agent(self, run_ctx: RunContext) -> Agent[RunContext]:
        return Agent[RunContext](
            name=self._domain.agent_name,
            instructions=self._domain.instructions(run_ctx.case_input),
            tools=list(self._tools),
            output_type=self._output_model,
        )

    async def run(self, run_ctx: RunContext, input: str | list[Any], *, max_turns: int) -> RunResult:
        return await Runner.run(
            self.build_agent(run_ctx),
            input,
            context=run_ctx,
            max_turns=max_turns,
            run_config=RunConfig(model=self._model, tracing_disabled=True, model_settings=ModelSettings(reasoning=Reasoning(effort="none"), max_tokens=6000, temperature=0.2, extra_body={"response_format": None}, tool_choice="required" if self._domain.tools else None)),
        )
