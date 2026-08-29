# Tutorial: Modelling and Executing BDD Tests for a Pickup Task

This tutorial will walk through how to introduce models, in addition to the ones for _representing_
BDD scenarios (see [corresponding tutorial](bdd-tutorial-representation.md)), to specify test
execution. These "execution models" can be used by a test orchestration framework
to parametrize scenario executions.

## Execution walkthrough with bdd_exec_ros2

This walkthrough uses the tested examples installed by the `bdd_exec_ros2` ROS
package. It composes a RobBDD execution model, connects fluent clauses to
observations, and launches the matching coordinator.

### 1. Compose the execution model

Start with
[`pickplace.bddx`](https://github.com/minhnh/bdd_exec_ros2/blob/-/models/robbdd/pickplace.bddx):

~~~text
import "pickplace.bdd"
import "lab.scenex"

ns bdd_exec='https://secorolab.github.io/models/acceptance-criteria/bdd/executions/'
ns bdd_exec_ros='https://secorolab.github.io/models/acceptance-criteria/bdd/executions/ros/'

bhv impl (ns=bdd_exec_ros) mockup-pp-server {
    bhv action: "/bdd/mockup_bhv_server"
}
~~~

The imported `pickplace.bdd` supplies the fluent clauses and scenario
variation. The imported `lab.scenex` supplies the concrete SceneX instance
used by `scene inst: <pickplace_scene_mjc>`. SceneX element mapping is
provided by scene-dsl.

> TODO: Add a separate scene-dsl tutorial covering SceneX composition,
> instances, and element mapping.

### 2. Link clauses to observation providers

A topic-backed post-place policy declares a provider, then links each
policy-local observation to that provider and to the target variable:

~~~text
obs provider (ns=bdd_exec_ros) detections-3d {
    ros topic: "/obs_policy/detections_3d"
    type: "vision_msgs/msg/Detection3D"
}

obs policy (ns=bdd_exec_ros) fcx-located-after-detections
    for <tmpl_pickplace.fc-located-after>
{
    observation object-pose {
        provider: <detections-3d>
        observes: <tmpl_pickplace.target_object>
    }
    observation workspace-pose {
        provider: <detections-3d>
        observes: <tmpl_pickplace.place_ws>
    }
    py { module: bdd_exec_ros2.observation, attr: poses_are_collocated }
}
~~~

The `for` reference attaches the policy to the fluent clause. Each
`observes` reference is resolved against the concrete scenario variant before
messages are evaluated. The evaluator may be a function, or a callable
stateful class.

The complete scenario execution selects the variant, SceneX instance,
behaviour implementation, and policies:

~~~text
Scenario Exec (ns=bdd_exec) pickplace-mockup-ros {
    variant: <sim_pickplace.pickplace_table>
    scene inst: <pickplace_scene_mjc>
    bhv: <mockup-pp-server>
    policies: {
        <fcx-located-before-topic>,
        <fcx-located-after-detections>
    }
}
~~~

### 3. Add timestamp and entity extraction

The coordinator accepts a message-type adapter registry. The tested mockup
node exports
`TOPIC_OBSERVATION_ADAPTERS` from
[`mockup_behaviour_node.py`](https://github.com/minhnh/bdd_exec_ros2/blob/-/bdd_exec_ros2/executables/mockup_behaviour_node.py):

~~~python
TOPIC_OBSERVATION_ADAPTERS = {
    Detection3D: (detection3d_stamp, map_detection3d_entity_mockup)
}
~~~

`detection3d_stamp` uses the `Detection3D.header.stamp` value. The entity
mapper converts each detection short ID, such as `tomato_soup_can`, to the
corresponding SceneX entity URI and returns the target-specific pose.

The adapter registry is enabled in
[`mockup_configs.yaml`](https://github.com/minhnh/bdd_exec_ros2/blob/-/config/mockup_configs.yaml):

~~~yaml
/bdd/test_coordinator:
  ros__parameters:
    topic_observation_adapters: >-
      bdd_exec_ros2.executables.mockup_behaviour_node:TOPIC_OBSERVATION_ADAPTERS
~~~

### 4. Launch the matching ROS execution

The tested topic model is listed by
[`pickplace-models-robbdd-json.yaml`](https://github.com/minhnh/bdd_exec_ros2/blob/-/models/pickplace-models-robbdd-json.yaml).
Launch it with:

~~~bash
ros2 launch bdd_exec_ros2 launch_mockup_robbdd.yaml
~~~

The launch file loads the coordinator configuration, the RobBDD graph-model
list, and the mockup behaviour node. Override `graph_models` when using a
different BDDX file.

For simulation-backed observations, use the tested
[`pickplace-sim-observations.bddx`](https://github.com/minhnh/bdd_exec_ros2/blob/-/models/robbdd/pickplace-sim-observations.bddx)
and launch file:

~~~bash
ros2 launch bdd_exec_ros2 launch_mockup_robbdd_sim.yaml \
  simulation_service_namespace:=/ \
  world_entity_name:=world
~~~

This launch selects the simulation graph-model list, sets
`scene_setup_mode:=simulation`, loads/resets the SceneX instance, and polls
entity poses through `SimInterface`. Simulation pose timestamps and entity
mapping are supplied by the built-in simulation adapter, so the Detection3D
registry is not needed for this variant.

For API details, see the source docstrings for
[`ObservationManager`](https://github.com/minhnh/bdd-dsl/blob/-/src/bdd_dsl/models/observation.py)
and
[`SimInterface`](https://github.com/minhnh/bdd_exec_ros2/blob/-/bdd_exec_ros2/sim_interfaces.py).

> [!WARNING]
> The videos below document the previous behave-based execution setup and are
> retained for historical context only. They do not describe the current ROS 2
> coordinator, observation providers, or simulation interface.

## Legacy behave execution videos (deprecated)

<video autoplay="autoplay" loop="loop" width="720" height="397">
  <source src="assets/vid/20230731-pickup_feature_gen-q40.webm" type="video/webm" >
</video>

Generating Gherkin features files form `bdd-dsl` scenario templates and variants.

<video autoplay="autoplay" loop="loop" width="720" height="397">
  <source src="assets/vid/20230731-pickup_feature_gen-more_variations-q40.webm" type="video/webm" >
</video>

Adding more objects and agents to a template variant and regenerating Gherkin features files.

## References

[^behave]: [behave](https://behave.readthedocs.io) - library for executing Gherkin features in Python
