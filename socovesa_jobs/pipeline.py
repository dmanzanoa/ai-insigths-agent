from __future__ import annotations

from .actions import ACTION_MAP
from .aws_clients import AwsClients
from .config import Settings, settings
from .decisions import decide_compression_config, decide_next_action, decide_parallelization
from .state import AgentState


def run_agentic_pipeline(label: str, clients: AwsClients, cfg: Settings = settings) -> AgentState:
    state = AgentState(label=label)

    print("\n" + "=" * 70)
    print(f"FULLY AGENTIC PIPELINE: {label.upper()}")
    print("=" * 70)

    max_iterations = 50
    for iteration in range(1, max_iterations + 1):
        state.step = iteration
        next_action = decide_next_action(state)
        print(f"\n[Iteration {iteration}] Next action: {next_action}")

        if next_action == "compress" and not state.compression_strategy:
            state.compression_strategy = decide_compression_config(state.quality_metrics)
            print(f"Compression strategy: {state.compression_strategy}")

        if next_action in {"generate_subproject", "generate_marca"} and not state.parallelization_strategy:
            state.parallelization_strategy = decide_parallelization(state)
            print(f"Parallelization strategy: {state.parallelization_strategy}")

        action = ACTION_MAP.get(next_action)
        if action is None:
            state.add_error(f"Unknown action: {next_action}", terminal=True)
            break

        state = action(clients, state, cfg)

        if next_action == "save_all":
            print("\nPIPELINE COMPLETED")
            break
    else:
        state.add_error(f"Pipeline exceeded {max_iterations} iterations", terminal=True)

    print_summary(state)
    return state


def print_summary(state: AgentState) -> None:
    print("\n" + "=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    print(f"Label: {state.label}")
    print(f"Iterations: {state.step}")
    print(f"Decisions made: {len(state.decisions_made)}")
    for i, decision in enumerate(state.decisions_made, 1):
        print(f"  {i}. {decision}")
    print(f"Errors: {len(state.errors)}")
    for error in state.errors[-5:]:
        print(f"  - {error}")
    print("Outputs generated:")
    print(f"  - General insights: {'yes' if state.general_insights else 'no'}")
    print(f"  - Tendencias: {len(state.tendencias_insights)} months")
    print(f"  - Subprojects: {len(state.subproject_insights)} projects")
    print(f"  - Marcas: {len(state.marca_insights)} brands")
    print("=" * 70 + "\n")

