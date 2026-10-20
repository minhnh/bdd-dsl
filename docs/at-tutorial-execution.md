# Acceptance Testing Tutorial 2: Observations and Execution

This tutorial connects the scenario from [Tutorial 1](at-tutorial-scenarios.md)
to evidence and an executable behavior. Both execution backends test one cube and one
destination; [set-valued sorting](at-tutorial-sorting.md) remains specification-only.

In the [test workflow](at-tutorial-scenarios.md#the-end-to-end-test-workflow),
this is the transition from **Scenario Specification** to **Scenario Execution Specification**,
connecting the problem-side scenario models to a concrete System under Test (SuT).
This includes scene configurations as well as evidence sources and evaluation policies
used to determine whether the SuT meets the specified acceptance criteria.

## Contents

<!-- mtoc-start -->

1. [Connect the shared scenario specification to a SuT](#connect-the-shared-scenario-specification-to-a-sut)
1. [Choose evidence for each criterion](#choose-evidence-for-each-criterion)
1. [Connect provider, observation, and policy](#connect-provider-observation-and-policy)
1. [Interpret event windows and results](#interpret-event-windows-and-results)
1. [Continue with a backend](#continue-with-a-backend)

<!-- mtoc-end -->

## Connect the shared scenario specification to a SuT

The [robbdd_tutorials](https://github.com/minhnh/robbdd_tutorials) package provides
two example Systems under Test (SuTs) to demonstrate the acceptance-testing process:
a Kinova manipulator controlled by [`motion-spec`](https://secoro.uni-bremen.de/motion-spec/)
and a [`coord-dsl` finite-state machine (FSM)](https://secoro.uni-bremen.de/coord-dsl/)
in MuJoCo, and a Panda manipulator controlled by [MoveIt](https://moveit.picknik.ai/main/index.html)
and a [`BehaviourTree.CPP` tree](https://www.behaviortree.dev/docs/intro) in Isaac Sim.
Both examples reuse the same scenario template, acceptance criteria,
and abstract objects and workspaces.

The common `.bdd` template defines the _fluent clauses_ that must hold, while the common `.scene`
defines the environment and available agent sets. Each backend supplies:

- A `.bdd` scenario variant selecting the acting robot. Both examples use the same object and
  workspace bindings; the MuJoCo variant additionally selects a specialized scene to accommodate
  `motion-spec`'s separate gripper agent.
- A `.scenex` instance mapping abstract entities to assets and sampled poses.
- A `.bddx `execution model binding the variant, scene instance, behavior server,
  and observation policies.

Normally, the acting robot is selected through the scenario variant's robot variable
rather than included explicitly in the scene. The Isaac Panda variant follows this approach,
representing the arm and gripper as one agent. The MuJoCo backend uses a specialized scene
containing Kinova and Robotiq because `motion-spec` requires the gripper to be modeled
as a separate agent.

The coordinator's `graph-models.yaml` lists the common template, backend scenario variant,
and BDDX execution model to load.

| Aspect | MuJoCo / motion-spec | Isaac Sim / MoveIt |
| --- | --- | --- |
| Acting robot | `mujoco_agents.kinova` | `panda_agents.panda` |
| Gripper | Separate Robotiq agent | Part of the Panda agent |
| Concrete assets | MJCF models | USD models |
| Behavior action | `/bdd/pickplace_bhv_server` | `/bdd/prepare` |
| Object/workspace evidence | URI-keyed detection topic | Simulation entity states and tabletop TF |
| End-effector evidence | Same detection topic | `panda_hand` TF |
| Timing | Simulation `/clock` | Simulation `/clock` |

Both backends use simulation time for the coordinator and evidence timestamps.
The MuJoCo runtime publishes `/clock`; `--rtf` controls playback speed without
changing the time basis.

## Choose evidence for each criterion

The behavior's successful action result establishes completion. The three
fluent clauses require additional evidence:

| Fluent | Evidence | Evaluation |
| --- | --- | --- |
| `object-at-pick` | Object and tabletop poses | Linear distance below 0.3 m before `E_PICK_START` |
| `object-held` | Object and grasp poses | Linear distance below 0.12 m from `E_PICK_END` until `E_PLACE_START` |
| `object-at-place` | Object and bin poses | Object center inside inset bin XY bounds after `E_PLACE_END` |

The distance checks are proxies for the stated requirements. The configured
containment check transforms the object center into the bin frame and applies
a cube-sized margin; it does not establish physical support or full 3D containment.
The bin dimensions and margin are calibrated separately for each backend.

## Connect provider, observation, and policy

~~~text
Provider data -> Entity observations -> Policy evaluator -> Fluent verdict
~~~

- A **provider** supplies raw evidence, such as ROS messages, simulation states,
  or TF transforms.
- An **observation** maps that evidence to scenario entities and extracts timestamps.
  `observes var` follows the entity selected by a scenario variable.
- A **policy** connects observations to a fluent and selects an evaluator,
  synchronization tolerance, and any finite evidence horizon.
- `Scenario Exec` selects the policies and binds the variant to its concrete scene
  and Behaviour action server.

The linear-distance policies retain the latest observation samples. A pair whose
timestamps differ by at most 0.1 seconds can produce a verdict: a distance below
the threshold gives `TRUE`, otherwise `FALSE`. Missing usable evidence gives
`UNKNOWN`; a mismatched pair waits for compatible evidence rather than adding
a verdict.

Both backends use simulated ground truth. Their providers are different ways
of observing simulator state, rather than perception pipelines.

## Interpret event windows and results

~~~text
E_PICK_START -> E_PICK_END -> E_PLACE_START -> E_PLACE_END
~~~

- **Before pick:** a two-second horizon selects evidence immediately preceding
  `E_PICK_START`. It is a lookback window, not a required two-second sleep.
- **During transport:** the held policy evaluates between pick completion and
  the start of placing.
- **After place:** the coordinator collects the two-second at-place window after
  `E_PLACE_END`, including evidence after the Behaviour result arrives.

For a passing test, expect a successful Behaviour result and `TRUE` for all
three policies. An action success alone is insufficient; inspect the policy
verdicts and reasons when analyzing `/bdd/status` or the web visualizer.

## Continue with a backend

The integration guides explain the concrete models and evidence wiring. The
package README maintains setup, launch, configuration, and debugging commands.

- [MuJoCo integration](at-tutorial-execution-mujoco.md): build a topic-based
  provider-observation-policy chain step by step.
- [Isaac Sim / MoveIt integration](at-tutorial-execution-isaac.md): connect the
  Panda behavior tree, simulation poses, and TF observations.
- [Tutorial 3: Set Quantifiers and Sorting](at-tutorial-sorting.md): extend the
  specification without adding it to the executable graph manifest.
