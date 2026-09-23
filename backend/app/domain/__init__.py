from app.core.contracts import DomainModule
from app.domain.api import router
from app.domain.examples import EXAMPLES
from app.domain.instructions import build_instructions, build_task_prompt
from app.domain.schemas import CaseInput, DispatchProposal
from app.domain.scripts import SCRIPTS, auto_script
from app.domain.seed import seed
from app.domain.service import execute_actions, fingerprint, load_case_view, snapshot, validate_proposal, verify_outcome
from app.domain.tools import TOOLS

DOMAIN = DomainModule(
    key="dispatch",
    title="Field-service dispatch (sample data)",
    agent_name="Dispatch planner",
    case_input_model=CaseInput,
    proposal_model=DispatchProposal,
    tools=TOOLS,
    instructions=build_instructions,
    task_prompt=build_task_prompt,
    load_case_view=load_case_view,
    validate_proposal=validate_proposal,
    fingerprint=fingerprint,
    snapshot=snapshot,
    execute_actions=execute_actions,
    verify_outcome=verify_outcome,
    seed=seed,
    examples=EXAMPLES,
    api_router=router,
    scripts=SCRIPTS,
    auto_script=auto_script,
)

__all__ = ["DOMAIN"]
