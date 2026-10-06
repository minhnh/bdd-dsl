# Acceptance Testing Tutorial 2: Observations and Execution

This tutorial adds executable evidence rules to the single pick-and-place variant from
[Tutorial 1](at-tutorial-scenarios.md). It deliberately executes one object and
one destination. Set-valued sorting remains a specification-only extension in
[Tutorial 3](at-tutorial-sorting.md).

The complete MuJoCo-specific model is
[pick_place.bddx](https://github.com/minhnh/robbdd_tutorials/blob/main/models/pick_place/mujoco_motion_spec/pick_place.bddx).

In the [end-to-end test workflow](at-tutorial-scenarios.md#the-end-to-end-test-workflow),
this tutorial first binds the behavior and scenario execution, then continues
with **Observation Policy Specification**. It connects the problem-side
scenario models to the system-under-test implementation, test execution, and
resulting evidence for analysis.

## Shared specification and backend models

The `.bdd` and `.scene` models from Tutorial 1 describe the test independently
of a simulator or behavior implementation. Each execution backend supplies its
own SceneX model, behavior binding, observation providers, and BDDX execution
model. This keeps backend-specific assets and frame mappings out of the shared
specification.

## 1. Decide what evidence each fluent needs

The scenario has three fluent clauses:

| Fluent | Evidence | Evaluation |
| --- | --- | --- |
| `object-at-pick` | object pose and table-top pose | pass when their linear distance is below 30 cm before picking |
| `object-held` | object and end-effector poses | pass while their linear distance remains below 12 cm between pick and place |
| `object-at-place` | object pose and bin pose | pass when the cube footprint is within the bin after placing |

## 2. Bind the behavior and scenario execution

The minimal BDDX model below uses `Scenario Exec` to bind a scenario variant,
such as the one defined in Tutorial 1, to a behavior implementation and a
concrete scene instance. It can also select observation policies for evaluating
the variant's fluent clauses. ROS 2 execution of BDDX models is currently
provided by [`bdd_exec_ros2`](https://github.com/minhnh/bdd_exec_ros2), which
supports behaviors exposed as a
[ROS 2 action server](https://github.com/minhnh/bdd_ros2_interfaces/blob/-/action/Behaviour.action).

~~~text
import "../common/pick_place.bdd"
import "pick_place_single.scenex"

ns tutorial_exec = "https://secorolab.github.io/robbdd/tutorials/pick-place/execution/"

bhv impl (ns=tutorial_exec) pick-place-server {
    bhv action: "/bdd/pickplace_bhv_server"
}

Scenario Exec (ns=tutorial_exec) mujoco-pick-place {
    variant: <pick-place-story.nominal-pick-place>
    scene inst: <pick_place_scene_mjc>
    bhv: <pick-place-server>
    policies: { }
}
~~~

## 3. Add the first provider-observation-policy chain

Begin with the `object-at-pick` fluent and build its evidence path one part at a
time.

### Declare the provider

An observation provider defines the source and type of raw evidence. Here it is
a ROS 2 topic carrying `vision_msgs/msg/Detection3DArray`. The message is
published directly from the MuJoCo simulation state, so it represents simulated
ground truth rather than the output of a perception system.

~~~diff
+++ pick_place.bddx
@@
 bhv impl (ns=tutorial_exec) pick-place-server {
     bhv action: "/bdd/pickplace_bhv_server"
 }
+
+obs provider (ns=tutorial_exec) ground-truth {
+    ros topic: "/sim/ground_truth/recognized_objects"
+    type: "vision_msgs/msg/Detection3DArray"
+}
 Scenario Exec (ns=tutorial_exec) mujoco-pick-place {
~~~

### Map provider messages to observations

An observation gives provider data meaning in the scenario. The two
observations below map detections to the entities bound to `target-object` and
`pick-workspace`. `map_detection3d_array_by_uri` matches each detection ID to
the corresponding scene-entity URI. `header_stamp` reads the standard ROS
message-header timestamp and falls back to the message receipt time when the
header stamp is zero.

~~~diff
+++ pick_place.bddx
@@
 obs provider (ns=tutorial_exec) ground-truth {
     ros topic: "/sim/ground_truth/recognized_objects"
     type: "vision_msgs/msg/Detection3DArray"
 }
+
+observation (ns=tutorial_exec) object-pose {
+    provider: <ground-truth> observes var <pick-place-template.target-object>
+    time extractor: py { module: bdd_exec_ros2.observation, attr: header_stamp }
+    entity mapper: py {
+        module: bdd_exec_ros2.observation,
+        attr: map_detection3d_array_by_uri
+    }
+}
+observation (ns=tutorial_exec) pick-workspace-pose {
+    provider: <ground-truth> observes var <pick-place-template.pick-workspace>
+    time extractor: py { module: bdd_exec_ros2.observation, attr: header_stamp }
+    entity mapper: py {
+        module: bdd_exec_ros2.observation,
+        attr: map_detection3d_array_by_uri
+    }
+}
 Scenario Exec (ns=tutorial_exec) mujoco-pick-place {
~~~

### Evaluate the fluent with a policy

The policy connects these observations to the `object-at-pick` fluent and
selects the built-in
[linear-distance evaluator](https://github.com/minhnh/bdd-dsl/blob/-/src/bdd_dsl/models/observation.py#L277).
The evaluator retains the latest sample for each observation and evaluates
them together only when their timestamps differ by no more than 0.1 seconds.
A synchronized pair less than 30 cm apart produces **True**;
a pair at or beyond the threshold produces **False**.
Missing evidence produces **Unknown**, while a time-mismatched pair
does not add a verdict and waits for compatible evidence.
If no usable verdict is available when the fluent is evaluated, its result is therefore **Unknown**.
The two-second horizon limits evidence for this `before` clause to
the interval immediately preceding `E_PICK_START`.

Finally, select the policy in `Scenario Exec`:

~~~diff
+++ pick_place.bddx
@@
 observation (ns=tutorial_exec) pick-workspace-pose {
     provider: <ground-truth> observes var <pick-place-template.pick-workspace>
     time extractor: py { module: bdd_exec_ros2.observation, attr: header_stamp }
     entity mapper: py {
         module: bdd_exec_ros2.observation,
         attr: map_detection3d_array_by_uri
     }
 }
+
+obs policy (ns=tutorial_exec) object-at-pick-policy
+    for <pick-place-template.object-at-pick>
+    horizon: 2.0 seconds
+{
+    observations: { <object-pose>, <pick-workspace-pose> }
+    evaluator: linear distance {
+        less-than: 0.3 m
+        max time offset: 0.1 s
+    }
+}
 Scenario Exec (ns=tutorial_exec) mujoco-pick-place {
@@
-    policies: { }
+    policies: {
+        <object-at-pick-policy>
+    }
 }
~~~

## 4. Add policies for the remaining clauses

The remaining clauses reuse the ground-truth provider and object observation.
Add observations for the place workspace and end effector, add their policies,
then select both policies in the scenario execution.

The policies demonstrate the two different evaluators:

- The built-in `linear distance` is supported in RobBDD textx grammar;
  its thresholds and synchronization tolerance are declared in the BDDX model.
  This is meant for evaluation of common point-to-point proximity.
- `cube_inside_bin` is a configured `PlanarContainmentEvaluator`: it transforms
  the cube center into the bin frame and checks the bin's XY bounds.

The configured instance belongs to the tutorial package rather than to
`bdd-dsl`, because its entity URIs and dimensions are model-specific:

~~~python
cube_inside_bin = PlanarContainmentEvaluator(
    URIRef("https://secorolab.github.io/models/environments/pick-place-single/cube"),
    URIRef("https://secorolab.github.io/models/environments/pick-place-single/bin-ws"),
    boundary_size_xy=(0.23, 0.19),
    margin_m=0.02,
)
~~~

The corresponding BDDX additions are:

~~~diff
+++ pick_place.bddx
@@
 observation (ns=tutorial_exec) pick-workspace-pose {
     provider: <ground-truth> observes var <pick-place-template.pick-workspace>
     time extractor: py { module: bdd_exec_ros2.observation, attr: header_stamp }
     entity mapper: py {
         module: bdd_exec_ros2.observation,
         attr: map_detection3d_array_by_uri
     }
 }
+observation (ns=tutorial_exec) place-workspace-pose {
+    provider: <ground-truth> observes var <pick-place-template.place-workspace>
+    time extractor: py { module: bdd_exec_ros2.observation, attr: header_stamp }
+    entity mapper: py {
+        module: bdd_exec_ros2.observation,
+        attr: map_detection3d_array_by_uri
+    }
+}
+observation (ns=tutorial_exec) end-effector-pose {
+    provider: <ground-truth> observes var <pick-place-template.robot>
+    time extractor: py { module: bdd_exec_ros2.observation, attr: header_stamp }
+    entity mapper: py {
+        module: bdd_exec_ros2.observation,
+        attr: map_detection3d_array_by_uri
+    }
+}
@@
 obs policy (ns=tutorial_exec) object-at-pick-policy
     for <pick-place-template.object-at-pick>
     horizon: 2.0 seconds
 {
     observations: { <object-pose>, <pick-workspace-pose> }
     evaluator: linear distance {
         less-than: 0.3 m
         max time offset: 0.1 s
     }
 }
+obs policy (ns=tutorial_exec) object-not-dropped-policy
+    for <pick-place-template.object-held>
+{
+    observations: { <object-pose>, <end-effector-pose> }
+    evaluator: linear distance { less-than: 0.12 m max time offset: 0.1 s }
+}
+obs policy (ns=tutorial_exec) object-at-place-policy
+    for <pick-place-template.object-at-place>
+    horizon: 2.0 seconds
+{
+    observations: { <object-pose>, <place-workspace-pose> }
+    evaluator: py {
+        module: robbdd_tutorials.observation_evaluators,
+        attr: cube_inside_bin
+    }
+}
@@
     policies: {
-        <object-at-pick-policy>
+        <object-at-pick-policy>,
+        <object-not-dropped-policy>,
+        <object-at-place-policy>
     }
 }
~~~

## 5. MuJoCo execution with motion-spec

### Concrete models and assets

The MuJoCo-specific resources live under
`models/pick_place/mujoco_motion_spec` in the `robbdd_tutorials` package. The
table MJCF is copied from `bdd_collab_bhv_cpp` and represents the smaller table
used in the physical lab. Additional can, cereal-box, and bottle assets are
copied from the
[robosuite object collection](https://github.com/ARISE-Initiative/robosuite/tree/master/robosuite/models/assets/objects).
The current executable variant still selects only the cube. The `Scenario Exec`
built above binds that variant to the MuJoCo SceneX instance.

Only `pick_place.bdd` and `pick_place.bddx` belong in the executable graph
manifest. Do not add `sorting.bdd` while quantified execution is unfinished.

### Integrate the system under test

The motion-spec/MuJoCo process owns the controller and simulator. Its ROS
integration must provide:

- a `bdd_ros2_interfaces/action/Behaviour` server at
  `/bdd/pickplace_bhv_server`;
- behavior-boundary events on `/bdd/events` for `E_PICK_START`, `E_PICK_END`,
  `E_PLACE_START`, and `E_PLACE_END`;
- one `vision_msgs/msg/Detection3DArray` on
  `/sim/ground_truth/recognized_objects` containing URI-keyed poses for the
  object, pick workspace, place workspace, and robot end effector.

The motion-spec model publishes those poses directly from its MuJoCo state:

~~~text
publish at 20.0 Hz to <ros.publishers.scene-poses> with {
    <pickplace_objects.cube>: <shared.world.pose-cube-base>,
    <pickplace_workspaces.table-ws>: <shared.world.pose-table-base>,
    <pickplace_workspaces.bin-ws>: <shared.world.pose-bin-base>,
    <pickplace_agents.arm1>: <shared.world.pose-ee-base>,
}
~~~

The process starts the simulator and waits for a behavior goal. The BDD
coordinator sends that goal; the motion-spec controller should not be embedded
in the coordinator launch file.

The tutorial motion-spec model implements this action server, publishes the
boundary events, and maps its live scene poses into the observation message.
The commands below therefore run the complete MuJoCo execution path.

### Run and visualize one pick-place test

Build and source the workspace first. Keep the long-lived processes separate
so restarting a test does not restart the web UI or simulator.

Terminal 1 — start the web visualizer once, then open
<http://127.0.0.1:8080>:

~~~bash
ros2 run bdd_exec_ros2 web_visualizer --ros-args -p use_sim_time:=true
~~~

Terminal 2 — start MuJoCo and leave it waiting for the behavior goal:

~~~bash
motion-spec run \
  "$(ros2 pkg prefix --share robbdd_tutorials)/models/pick_place/mujoco_motion_spec/pick_place_single.robmot" \
  --headless
~~~

Terminal 3 — start only the BDD coordinator:

~~~bash
ros2 launch robbdd_tutorials pick_place_coordinator.launch.yaml
~~~

Terminal 4 — trigger one execution:

~~~bash
ros2 topic pub --once /bdd/start std_msgs/msg/Empty '{}'
~~~

The coordinator selects `nominal-pick-place`, sends one behavior goal, gathers
the configured evidence, and publishes scenario status for the web visualizer.

### Validate the execution model

From the MuJoCo model directory:

~~~bash
textx check pick_place_single.scenex
textx check pick_place_single.fsm
textx check pick_place_single.robmot
textx check pick_place.bddx
~~~

Each command must report **OK**.

## 6. Isaac Sim execution with MoveIt and a behavior tree

The Isaac Sim backend will use separate concrete models rather than reuse the
MuJoCo resources. Its SceneX model can map the shared scene entities to Isaac
Sim USD assets, such as YCB objects and KLT bins, while MoveIt and a behavior
tree implement the pick-and-place behavior.

This backend should keep its SceneX and BDDX files in a separate model
directory while importing the same common `.scene` and `.bdd` files. The
`bdd_bt_executor_ros2` integration is still work in progress, so execution
commands will be added once its behavior action server, boundary events, and
observation providers are available.
