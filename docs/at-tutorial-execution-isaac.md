# Acceptance Testing: Isaac Sim / MoveIt Integration

This guide realizes the behavior implementation, evidence sources, and evaluation policies
from [Tutorial 2](at-tutorial-execution.md) for a Panda manipulator running with
MoveIt and a behavior tree in Isaac Sim.

For installation, launch commands, and result inspection, follow the package's
[Isaac run instructions](https://github.com/minhnh/robbdd_tutorials#run-the-isaac-acceptance-test).
The complete models live in
[models/pick_place/isaacsim](https://github.com/minhnh/robbdd_tutorials/tree/-/models/pick_place/isaacsim).

## Contents

<!-- mtoc-start -->

1. [Instantiate the scene](#instantiate-the-scene)
1. [Bind the behavior and scenario execution](#bind-the-behavior-and-scenario-execution)
1. [Add the first provider-observation-policy chain](#add-the-first-provider-observation-policy-chain)
    1. [Add the simulation provider and object observation](#add-the-simulation-provider-and-object-observation)
    1. [Add the TF provider and tabletop observation](#add-the-tf-provider-and-tabletop-observation)
    1. [Add and select the at-pick policy](#add-and-select-the-at-pick-policy)
1. [Add observations and policies for transport and placement](#add-observations-and-policies-for-transport-and-placement)
1. [Connect the behavior tree to execution](#connect-the-behavior-tree-to-execution)
1. [Run and analyze the test](#run-and-analyze-the-test)
1. [Validate the models](#validate-the-models)

<!-- mtoc-end -->

## Instantiate the scene

A SceneX instance connects the abstract scene to concrete models and poses.
Here, `pick_place_positive.scenex` declares `pick_place_scene_isaac` for the common
`pick_place_scene`. Its kinematic graph places the table, bin, and sampled objects;
model declarations link those bodies to USD resources and simulator entity paths.

For example, this declaration inside the scene instance loads the Panda world
from a ROS package and maps its world and table bodies:

~~~text
model panda-world-usd as usd {
    ros pkg = "bdd_exec_ros2", path = "models/panda_moveit.usd"
    map body <pickplace_graph.world> to "world"
    map body <pickplace_graph.table> to "/background/table_low_327"
}
~~~

Additional `obj <...>` sections associate each scene object with its USD model
and map the corresponding kinematic body to a prim path, such as `/spawned/cube`.
See the [complete SceneX instance](https://github.com/minhnh/robbdd_tutorials/blob/-/models/pick_place/isaacsim/pick_place_positive.scenex).

The scenario variant binds the target to `pickplace_objects.cube`, the workspaces to
`table-ws` and `bin-ws`, and the robot to `panda_agents.panda`.

The BDDX model selects `pick_place_positive.scenex`, which samples the cube’s position in a
separate region from the other objects. This reduces collision-planning failures because
the MoveIt behavior includes non-target objects in the planning scene and treats contact
with the gripper as a collision. To explore these failures, use `pick_place_single.scenex`,
which samples all object positions from the same distribution. In the next section,
`Scenario Exec` selects the concrete instance with `scene inst: <pick_place_scene_isaac>`.

## Bind the behavior and scenario execution

Start with the behavior action server and a `Scenario Exec` without observation policies.
The local `pick_place.bdd` selects Panda, the cube, and the table/bin workspaces;
`pick_place_positive.scenex` supplies their concrete scene instance.

~~~text
import "pick_place.bdd"
import "../common/pick_place.bdd"
import "../common/pick_place_single.scene"
import "pick_place_positive.scenex"

ns isaac_exec = "https://secorolab.github.io/robbdd/tutorials/pick-place/isaac/execution/"

bhv impl (ns=isaac_exec) pick-place-server {
    bhv action: "/bdd/pick_place"
}

Scenario Exec (ns=isaac_exec) isaac-pick-place {
    variant: <isaac-pick-place-story.nominal-pick-place>
    scene inst: <pick_place_scene_isaac>
    bhv: <pick-place-server>
    policies: {  }
}
~~~

Launching the BT server advertises `/bdd/pick_place`; a Behaviour goal triggers
its selected tree. The BDD coordinator sends that goal for this scenario execution.

## Add the first provider-observation-policy chain

Begin with `object-at-pick`, which needs the object and tabletop poses.

### Add the simulation provider and object observation

The simulation provider queries ground-truth entity states using the SceneX mappings.
`observes var` follows the selected target object. The mapper preserves full poses,
including orientation; the time extractor uses the latest nonzero source stamp,
falling back to receipt time when none is available.

~~~diff
--- a/pick_place.bddx
+++ b/pick_place.bddx
@@ -9,6 +9,17 @@
     bhv action: "/bdd/pick_place"
 }

+obs provider (ns=isaac_exec) entity-state {
+    ros simulation entity state
+    update-rate: 10 Hz
+}
+
+observation (ns=isaac_exec) object-pose {
+    provider: <entity-state> observes var <pick-place-template.target-object>
+    time extractor: py { module: bdd_exec_ros2.observation, attr: latest_identified_pose_stamp }
+    entity mapper: py { module: bdd_exec_ros2.observation, attr: map_identified_entity_poses }
+}
+
 Scenario Exec (ns=isaac_exec) isaac-pick-place {
     variant: <isaac-pick-place-story.nominal-pick-place>
     scene inst: <pick_place_scene_isaac>
~~~

### Add the TF provider and tabletop observation

The TF provider observes frames relative to `world`. In the supplied scene the
tabletop is at the world origin, while the table entity origin is at its legs.
Map `world` to `table-ws` to use the tabletop as the pick-area reference.

~~~diff
--- a/pick_place.bddx
+++ b/pick_place.bddx
@@ -14,10 +14,22 @@
     update-rate: 10 Hz
 }

+obs provider (ns=isaac_exec) robot-tf {
+    ros transform listener
+    reference-frame: "world"
+    update-rate: 10 Hz
+}
+
 observation (ns=isaac_exec) object-pose {
     provider: <entity-state> observes var <pick-place-template.target-object>
     time extractor: py { module: bdd_exec_ros2.observation, attr: latest_identified_pose_stamp }
     entity mapper: py { module: bdd_exec_ros2.observation, attr: map_identified_entity_poses }
+}
+
+observation (ns=isaac_exec) pick-workspace-pose {
+    provider: <robot-tf> observes var <pick-place-template.pick-workspace>
+    time extractor: py { module: bdd_exec_ros2.observation, attr: header_stamp }
+    entity mapper: string { "world" to ws <pickplace_workspaces.table-ws> }
 }

 Scenario Exec (ns=isaac_exec) isaac-pick-place {
~~~

### Add and select the at-pick policy

The policy evaluates object/tabletop distance below 0.3 m with at most 0.1 seconds
between timestamps. Its two-second horizon selects evidence before `E_PICK_START`;
it does not impose a two-second sleep. Select the policy in `Scenario Exec`.

~~~diff
--- a/pick_place.bddx
+++ b/pick_place.bddx
@@ -32,9 +32,17 @@
     entity mapper: string { "world" to ws <pickplace_workspaces.table-ws> }
 }

+obs policy (ns=isaac_exec) object-at-pick-policy
+    for <pick-place-template.object-at-pick>
+    horizon: 2.0 seconds
+{
+    observations: { <object-pose>, <pick-workspace-pose> }
+    evaluator: linear distance { less-than: 0.3 m max time offset: 0.1 s }
+}
+
 Scenario Exec (ns=isaac_exec) isaac-pick-place {
     variant: <isaac-pick-place-story.nominal-pick-place>
     scene inst: <pick_place_scene_isaac>
     bhv: <pick-place-server>
-    policies: {  }
+    policies: { <object-at-pick-policy> }
 }
~~~

## Add observations and policies for transport and placement

Reuse the simulation provider for the bin and TF for `panda_hand`, which represents
the Panda agent's grasp pose. Add the held and at-place policies and select both
alongside the at-pick policy.

~~~diff
--- a/pick_place.bddx
+++ b/pick_place.bddx
@@ -26,10 +26,22 @@
     entity mapper: py { module: bdd_exec_ros2.observation, attr: map_identified_entity_poses }
 }

+observation (ns=isaac_exec) place-workspace-pose {
+    provider: <entity-state> observes var <pick-place-template.place-workspace>
+    time extractor: py { module: bdd_exec_ros2.observation, attr: latest_identified_pose_stamp }
+    entity mapper: py { module: bdd_exec_ros2.observation, attr: map_identified_entity_poses }
+}
+
 observation (ns=isaac_exec) pick-workspace-pose {
     provider: <robot-tf> observes var <pick-place-template.pick-workspace>
     time extractor: py { module: bdd_exec_ros2.observation, attr: header_stamp }
     entity mapper: string { "world" to ws <pickplace_workspaces.table-ws> }
+}
+
+observation (ns=isaac_exec) grasp-pose {
+    provider: <robot-tf> observes var <pick-place-template.robot>
+    time extractor: py { module: bdd_exec_ros2.observation, attr: header_stamp }
+    entity mapper: string { "panda_hand" to agn <panda_agents.panda> }
 }

 obs policy (ns=isaac_exec) object-at-pick-policy
@@ -40,9 +52,24 @@
     evaluator: linear distance { less-than: 0.3 m max time offset: 0.1 s }
 }

+obs policy (ns=isaac_exec) object-held-policy
+    for <pick-place-template.object-held>
+{
+    observations: { <object-pose>, <grasp-pose> }
+    evaluator: linear distance { less-than: 0.12 m max time offset: 0.1 s }
+}
+
+obs policy (ns=isaac_exec) object-at-place-policy
+    for <pick-place-template.object-at-place>
+    horizon: 2.0 seconds
+{
+    observations: { <object-pose>, <place-workspace-pose> }
+    evaluator: py { module: robbdd_tutorials.observation_evaluators, attr: isaac_cube_inside_bin }
+}
+
 Scenario Exec (ns=isaac_exec) isaac-pick-place {
     variant: <isaac-pick-place-story.nominal-pick-place>
     scene inst: <pick_place_scene_isaac>
     bhv: <pick-place-server>
-    policies: { <object-at-pick-policy> }
+    policies: { <object-at-pick-policy>, <object-held-policy>, <object-at-place-policy> }
 }
~~~

The held policy checks object/grasp proximity between `E_PICK_END` and
`E_PLACE_START`. The at-place policy selects the tutorial's
`isaac_cube_inside_bin` evaluator, calibrated to the KLT interior: 0.178 by
0.277 m with a 0.025 m inset margin. It tests the cube center in bin-local XY
coordinates rather than physical support or full 3D containment.

The resulting model has the providers, observations, and three selected policies
used by the shipped BDDX model. Adapt the tabletop and grasp frame mappings when
using a different world or robot.

## Connect the behavior tree to execution

The [motion tree](https://github.com/minhnh/robbdd_tutorials/blob/-/behavior_trees/isaac_pick_place.xml)
uses reusable executor nodes. Shared preparation resolves the Behaviour
parameters, waits for fresh MoveIt state and TF, queries entity poses, and
constructs the collision scene and offset motion targets.

| Boundary | Placement in the behavior tree |
| --- | --- |
| `E_PICK_START` | After preparation, before opening and approaching |
| `E_PICK_END` | After closing, attaching in MoveIt, and lifting |
| `E_PLACE_START` | After transfer to pre-place, before descent |
| `E_PLACE_END` | After opening, detaching, and retreating |

The pre/post-pick poses use a 0.1 m reference-frame clearance; pre/post-place
use 0.2 m. The tree stops when a node fails, so later boundary events are not emitted.

Three configuration layers have different roles:

| Layer | Purpose |
| --- | --- |
| SceneX | Concrete assets, sampled poses, and model/body mappings for scene setup and simulation observations |
| `config/isaac_pick_place.yaml` | BT entity URI -> prim path mappings, collision geometry and offsets, and Behaviour variable bindings |
| Coordinator YAML and model-loading configuration | Runtime settings and the common template, Panda scenario variant, and BDDX execution model to load |

The BT YAML resolves `object_uri`, `place_workspace_uri`, and `robot_uri` from
the Behaviour parameters. The pick workspace belongs to the Given clause and
is not a parameter of the pick/place Behaviour. BT planning queries and BDD
observation providers are separate consumers of live simulation state.

The tree currently overrides queried entity-pose frame IDs to `world` because
the service returns world coordinates labeled with entity frames. Collision
geometry includes local translations and rotations to align shapes with the assets.

## Run and analyze the test

Follow the [README run sequence](https://github.com/minhnh/robbdd_tutorials#run-the-isaac-acceptance-test):
load the robot scene once, start MoveIt, launch the observation coordinator,
and trigger `/bdd/start`. The observation launch includes the BT server;
a separate standalone server would duplicate `/bdd/pick_place`.

- Initial scene loading makes Panda available before MoveIt initializes.
- `/bdd/start` loads/resets the selected scene again with fresh samples.
- Preparation/readiness provides time to collect pre-pick evidence. No fixed
  pre-pick delay is required by the two-second lookback horizon.
- The coordinator uses simulation time and waits for reset-clock progress
  during scene setup. A backward jump after scenario start fails the run and
  requires restarting the coordinator.
- Resetting time can stall ros2_control until its old clock deadline is reached;
  see [ros2_control #3697](https://github.com/ros-controls/ros2_control/issues/3697).
  The readiness node can wait for recovery, but cannot accelerate it.

Inspect both the Behaviour result and the three fluent verdicts. A successful
MoveIt plan or an attached collision object alone does not prove that the cube
was physically grasped or placed. Use the
[standalone debugging instructions](https://github.com/minhnh/robbdd_tutorials#standalone-isaac-debugging)
to separate planning/geometry failures from observation failures.

For generic node ports, see the executor's
[BT node reference](https://github.com/minhnh/bdd_bt_executor_ros2/blob/-/docs/bt_nodes.md).

## Validate the models

From `models/pick_place/isaacsim` in the tutorial package:

~~~bash
textx check pick_place.bdd pick_place.bddx
textx check pick_place_single.scenex pick_place_positive.scenex
~~~

Each model must report **OK**. The package's
[offline checks](https://github.com/minhnh/robbdd_tutorials#offline-checks)
also verify the shipped tree wiring and Panda bindings.
