# Acceptance Testing: Isaac Sim / MoveIt Integration

This guide realizes the shared contract from
[Tutorial 2](at-tutorial-execution.md) with Panda, MoveIt, and a behavior tree.
Use the package's [Isaac run instructions](https://github.com/minhnh/robbdd_tutorials#run-the-isaac-acceptance-test)
for installation, scene loading, launch commands, and result inspection.

The complete models live in
[models/pick_place/isaacsim](https://github.com/minhnh/robbdd_tutorials/tree/main/models/pick_place/isaacsim).

## 1. Bind Panda and instantiate the scene

The backend's `pick_place.bdd` imports the shared template and scene definitions.
Its story binds the target to `pickplace_objects.cube`, the workspaces to
`table-ws` and `bin-ws`, and the robot to `panda_agents.panda`.
Panda represents the arm and gripper together; there is no separate gripper agent.

The SceneX instance maps the common environment to USD assets:

- A Panda world containing the robot and table.
- A Dex cube, soup can, cracker box, mustard bottle, and KLT bin.
- Sampled object poses relative to the tabletop.

The common `cereal-box` identity maps to a cracker-box asset here and cereal
geometry in MuJoCo. Shared identities make the contract reusable without
requiring identical meshes or calibrated dimensions.

The BDDX model selects `pick_place_positive.scenex`. Its cube region is separate
from the other objects, giving the cube a clearer approach:

| Objects | Sampled X range (m) | Sampled Y range (m) |
| --- | --- | --- |
| Cube | -0.05 to 0.10 | -0.18 to -0.08 |
| Other objects | 0.10 to 0.25 | 0.18 to 0.28 |

The original `pick_place_single.scenex` uses shared-region sampling. Both scenes
sample poses; the BT queries the resulting live poses. The positive-case layout
reduces clutter but cannot prevent all collisions or object movement while settling.

## 2. Bind the behavior and evidence providers

The BDDX model binds the scenario to the BT server and selects two providers:

~~~text
ns isaac_exec = "https://secorolab.github.io/robbdd/tutorials/pick-place/isaac/execution/"

bhv impl (ns=isaac_exec) pick-place-server {
    bhv action: "/bdd/prepare"
}

obs provider (ns=isaac_exec) entity-state {
    ros simulation entity state
    update-rate: 10 Hz
}
obs provider (ns=isaac_exec) robot-tf {
    ros transform listener
    reference-frame: "world"
    update-rate: 10 Hz
}
~~~

The simulation provider resolves scene entities through the SceneX instance.
The TF provider observes frames relative to `world`.

## 3. Map evidence to scenario entities

Object and bin observations preserve full poses, including orientation. For example:

~~~text
observation (ns=isaac_exec) object-pose {
    provider: <entity-state> observes var <pick-place-template.target-object>
    time extractor: py { module: bdd_exec_ros2.observation, attr: latest_identified_pose_stamp }
    entity mapper: py { module: bdd_exec_ros2.observation, attr: map_identified_entity_poses }
}
~~~

`place-workspace-pose` uses the same provider and mapper for the destination
variable. `latest_identified_pose_stamp` takes the latest nonzero source stamp,
falling back to receipt time when none is available.

The fixed tabletop and robot grasp use TF observations:

~~~text
observation (ns=isaac_exec) pick-workspace-pose {
    provider: <robot-tf> observes var <pick-place-template.pick-workspace>
    time extractor: py { module: bdd_exec_ros2.observation, attr: header_stamp }
    entity mapper: string { "world" to ws <pickplace_workspaces.table-ws> }
}
observation (ns=isaac_exec) grasp-pose {
    provider: <robot-tf> observes var <pick-place-template.robot>
    time extractor: py { module: bdd_exec_ros2.observation, attr: header_stamp }
    entity mapper: string { "panda_hand" to agn <panda_agents.panda> }
}
~~~

In the supplied world, the tabletop is at the world origin; the table entity's
origin is at its legs. Mapping `world` to the tabletop workspace avoids using
the legs as the pick-area reference. `panda_hand` supplies the grasp pose for
the Panda agent. These mappings must be adapted with a different world or robot.

The two distance policies reuse the thresholds and timing from Tutorial 2.
The place policy selects `robbdd_tutorials.observation_evaluators.isaac_cube_inside_bin`,
calibrated to the KLT interior: 0.178 by 0.277 m with a 0.025 m inset margin.
It tests the cube center in bin-local XY coordinates, not physical grasp success
or full 3D containment.

## 4. Connect the behavior tree to the contract

The [motion tree](https://github.com/minhnh/robbdd_tutorials/blob/main/behavior_trees/isaac_pick_place.xml)
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
| Coordinator YAML and graph manifest | Runtime settings and the common template, Panda story, and BDDX execution model to load |

The BT YAML resolves `object_uri`, `place_workspace_uri`, and `robot_uri` from
the Behaviour parameters. The pick workspace belongs to the Given clause and
is not a parameter of the pick/place Behaviour. BT planning queries and BDD
observation providers are separate consumers of live simulation state.

The tree currently overrides queried entity-pose frame IDs to `world` because
the service returns world coordinates labeled with entity frames. Collision
geometry includes local translations and rotations to align shapes with the assets.

## 5. Run and analyze the test

Follow the [README run sequence](https://github.com/minhnh/robbdd_tutorials#run-the-isaac-acceptance-test):
load the robot scene once, start MoveIt, launch the observation coordinator,
and trigger `/bdd/start`. The observation launch includes the BT server;
a separate standalone server would duplicate `/bdd/prepare`.

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
[BT node reference](https://github.com/minhnh/bdd_bt_executor_ros2/blob/main/docs/bt_nodes.md).

## Validate the models

From `models/pick_place/isaacsim` in the tutorial package:

~~~bash
textx check pick_place.bdd pick_place.bddx
textx check pick_place_single.scenex pick_place_positive.scenex
~~~

Each model must report **OK**. The package's
[offline checks](https://github.com/minhnh/robbdd_tutorials#offline-checks)
also verify the shipped tree wiring and Panda bindings.
