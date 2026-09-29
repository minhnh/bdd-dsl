# Acceptance Testing Tutorial 2: Observations and Execution

This tutorial adds executable evidence rules to the single pick-and-place
variant from [Tutorial 1](at-tutorial-scenarios.md). It deliberately executes one object and
one destination. Set-valued sorting remains a specification-only extension in
[Tutorial 3](at-tutorial-sorting.md).

The complete MuJoCo-specific model is
[pick_place.bddx](https://github.com/minhnh/robbdd_tutorials/blob/main/robbdd_tutorials/models/pick_place/mujoco_motion_spec/pick_place.bddx).

In the [end-to-end test workflow](at-tutorial-scenarios.md#the-end-to-end-test-workflow),
this tutorial starts at **Observation Policy Specification**. It connects the
problem-side scenario models to the system-under-test implementation, test
execution, and resulting evidence for analysis.

## 1. Decide what evidence each fluent needs

The scenario has three fluent clauses:

| Fluent | Evidence | Evaluation |
| --- | --- | --- |
| `object-at-pick` | object pose and pick-workspace pose | pass when their linear distance is below 5 cm before picking |
| `object-held` | a direct trinary observation | use the reported `True`, `False`, or `Unknown` value between pick and place |
| `object-at-place` | object pose and place-workspace pose | pass when their linear distance is below 5 cm after placing |

Pose pairs may differ by at most 0.1 seconds. A two-second horizon bounds how
long the evaluator searches for matching pose evidence. Missing, stale, or
temporally incompatible evidence produces **Unknown** rather than a pass.

## 2. Create the BDDX model

First bind the scenario behavior to the system-under-test action server:

~~~text
bhv impl (ns=tutorial_exec) pick-place-server {
    bhv action: "/bdd/pickplace_bhv_server"
}
~~~

Declare one ROS provider for each pose source, then describe what each message
observes. `header_stamp` extracts evidence time from `PoseStamped`:

~~~text
obs provider (ns=tutorial_exec) object-pose-topic {
    ros topic: "/bdd/observations/object_pose"
    type: "geometry_msgs/msg/PoseStamped"
}

observation (ns=tutorial_exec) object-pose {
    provider: <object-pose-topic>
    observes var <pick-place-template.target-object>
    time extractor: py {
        module: bdd_exec_ros2.observation,
        attr: header_stamp
    }
}
~~~

The location policy combines the object and workspace observations:

~~~text
obs policy (ns=tutorial_exec) object-at-pick-policy
    for <pick-place-template.object-at-pick>
    horizon: 2.0 seconds
{
    observations: { <object-pose>, <pick-workspace-pose> }
    evaluator: linear distance {
        less-than: 0.05 m
        max time offset: 0.1 s
    }
}
~~~

The held-state policy accepts an already evaluated trinary stream:

~~~text
obs policy (ns=tutorial_exec) object-held-policy
    for <pick-place-template.object-held>
{
    trinary topic: "/bdd/observations/object_held"
}
~~~

Finally, select exactly one scenario variant and its MuJoCo SceneX instance:

~~~text
Scenario Exec (ns=tutorial_exec) mujoco-pick-place {
    variant: <pick-place-story.nominal-pick-place>
    scene inst: <pick_place_scene_mjc>
    bhv: <pick-place-server>
    policies: {
        <object-at-pick-policy>,
        <object-held-policy>,
        <object-at-place-policy>
    }
}
~~~

Only `pick_place.bdd` and `pick_place.bddx` belong in the executable graph
manifest. Do not add `sorting.bdd` while quantified execution is unfinished.

## 3. Integrate the system under test

The motion-spec/MuJoCo process owns the controller and simulator. Its ROS
integration must provide:

- a `bdd_ros2_interfaces/action/Behaviour` server at
  `/bdd/pickplace_bhv_server`;
- behavior-boundary events on `/bdd/events` for `E_PICK_START`, `E_PICK_END`,
  `E_PLACE_START`, and `E_PLACE_END`;
- `geometry_msgs/msg/PoseStamped` observations for the object, pick workspace,
  and place workspace on the topics declared in BDDX; and
- a `bdd_ros2_interfaces/msg/TrinaryStamped` observation on
  `/bdd/observations/object_held`.

The process starts the simulator and waits for a behavior goal. The BDD
coordinator sends that goal; the motion-spec controller should not be embedded
in the coordinator launch file.

> The copied motion-spec model is valid, but its ROS behavior-server and
> observation adapter are still being completed. The commands below describe
> the intended process boundary and become end-to-end runnable with that
> adapter.

## 4. Run and visualize one pick-place test

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

## Validate the execution model

From the MuJoCo model directory:

~~~bash
textx check pick_place_single.scenex
textx check pick_place_single.fsm
textx check pick_place_single.robmot
textx check pick_place.bddx
~~~

Each command must report **OK**.
