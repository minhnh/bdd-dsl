# Acceptance Testing: MuJoCo Integration

This guide realizes the shared contract from
[Tutorial 2](at-tutorial-execution.md) with motion-spec and MuJoCo. For installation,
launch commands, and result inspection, follow the package's
[MuJoCo run instructions](https://github.com/minhnh/robbdd_tutorials#run-the-mujoco-acceptance-test).

The complete backend models live in
[models/pick_place/mujoco_motion_spec](https://github.com/minhnh/robbdd_tutorials/tree/main/models/pick_place/mujoco_motion_spec).
They bind the cube variant to Kinova, with Robotiq as a separately controlled
agent in the MuJoCo scene. The shared objects and workspaces retain their URIs.

## 1. Bind the behavior and scenario execution

The minimal BDDX model below uses `Scenario Exec` to bind a scenario variant,
defined in the local `pick_place.bdd`, to a behavior implementation and a
concrete scene instance. It can also select observation policies for evaluating
the variant's fluent clauses. ROS 2 execution of BDDX models is currently
provided by [`bdd_exec_ros2`](https://github.com/minhnh/bdd_exec_ros2), which
supports behaviors exposed as a
[ROS 2 action server](https://github.com/minhnh/bdd_ros2_interfaces/blob/main/action/Behaviour.action).

~~~text
import "pick_place.bdd"
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

## 2. Add the first provider-observation-policy chain

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
[linear-distance evaluator](https://github.com/minhnh/bdd-dsl/blob/main/src/bdd_dsl/models/observation.py).
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

## 3. Add policies for the remaining clauses

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

## 4. Connect the runtime

The motion-spec process owns the controller and simulator. Its ROS integration provides:

- A Behaviour action server at `/bdd/pickplace_bhv_server`.
- The four pick/place boundary events on `/bdd/events`.
- URI-keyed `Detection3DArray` poses on `/sim/ground_truth/recognized_objects`.

The motion-spec model publishes the evidence directly from MuJoCo state:

~~~text
publish at 20.0 Hz to <ros.publishers.scene-poses> with {
    <pickplace_objects.cube>: <shared.world.pose-cube-base>,
    <pickplace_workspaces.table-ws>: <shared.world.pose-table-base>,
    <pickplace_workspaces.bin-ws>: <shared.world.pose-bin-base>,
    <mujoco_agents.kinova>: <shared.world.pose-ee-base>,
}
~~~

The coordinator sends the behavior goal and evaluates the evidence; it does not
run the motion-spec controller. The deployment enables `[ros.clock]` in
`robot.toml`, publishing MuJoCo simulation time on `/clock` and using it for
ROS event and observation timestamps. The coordinator and visualizer use
`use_sim_time=true`. `--rtf 1` selects real-time playback; other speeds retain
the same simulation-time basis for evaluation.

The [graph manifest](https://github.com/minhnh/robbdd_tutorials/blob/main/models/pick_place/mujoco_motion_spec/graph-models.yaml)
loads three models: the common `pick_place.bdd` template, the local
`pick_place.bdd` story, and the local `pick_place.bddx` execution binding.
Sorting remains outside this executable manifest.

The SceneX model maps the common environment to MuJoCo assets, including the
lab table and robosuite can, cereal box, and bottle. The executable variant
selects the cube; the other objects provide scene context.

## Validate the models

From `models/pick_place/mujoco_motion_spec` in the tutorial package:

~~~bash
textx check pick_place_mujoco.scene pick_place.bdd pick_place.bddx
textx check pick_place_single.scenex pick_place_single.fsm pick_place_single.robmot
~~~

Each model must report **OK**. Then follow the
[run instructions](https://github.com/minhnh/robbdd_tutorials#run-the-mujoco-acceptance-test)
and inspect the Behaviour result and all three policy verdicts.

Compare this evidence path with the [Isaac integration](at-tutorial-execution-isaac.md).
