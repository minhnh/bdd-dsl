# Tutorial: Modeling pick & place applications using RobBDD

This tutorial shows how to use the [RobBDD](https://github.com/minhnh/robbdd)
Domain-Specific-Language (DSL) to model robotics acceptance criteria and generate
[Gherkin](https://cucumber.io/docs/gherkin/reference/) feature files for acceptance test
execution of pick & place scenarios. The following model examples can also be found under
the `examples/models` folder in the RobBDD repository.

## Table of contents

<!-- mtoc-start -->

1. [Specifying a scenario template](#specifying-a-scenario-template)
    1. [Identifiers](#identifiers)
    1. [Minimal Scenario Template](#minimal-scenario-template)
    1. [Adding fluent clauses](#adding-fluent-clauses)
1. [Specifying a scene](#specifying-a-scene)
1. [Specifying user stories and scenario variants](#specifying-user-stories-and-scenario-variants)
    1. [Table variation](#table-variation)
    1. [Cartesian product variation](#cartesian-product-variation)
1. [From pick and place to sorting](#from-pick-and-place-to-sorting)
1. [Code generation](#code-generation)
1. [References](#references)

<!-- mtoc-end -->

## Specifying a scenario template

[Behaviour-Driven Development (BDD)](https://en.wikipedia.org/wiki/Behavior-driven_development)
in an acceptance testing approach which defines each acceptance, i.e., "good-enough", criterion,
as a scenario using the _Given_ pre-condition, _When_ action/event occurs, _Then_ expect some outcome
formulation. A popular BDD implmentation is [Gherkin](https://cucumber.io/docs/gherkin/reference).
When applied to a simple pick & place task, a Gherkin scenario may look like the following:

```gherkin
Scenario Outline: pickplace scenario
  Given <object> is located at <pick_ws>
  When the <robot> picks <object> and places it at <place_ws>
  Then the object is located at <place_ws>

  Examples:
    | robot  | object | pick_ws | place_ws |
    | kinova | ball   | table   | shelf    |
    ...
```

Here, in addition to the pick-and-place behaviour, we declare 2 expectations: the target object to
be in the picking area before the behaviour, and at the placing area afterwards.
`<robot>`, `<object>`,... in the excerpt are parameters that can take different values in the
`Examples` table underneath.
We now walk through how we can specify this using RobBDD.
We begin with the following minimal example:

```gherkin
// pickplace.bdd
ns tutorial = "https://secorolab.github.io/robbdd/tutorials/"

Task (ns=tutorial) tutorial-tsk

Event (ns=tutorial) evt-scr-start
Event (ns=tutorial) evt-pick-start
Event (ns=tutorial) evt-place-end
Event (ns=tutorial) evt-scr-end

Scenario Template (ns=tutorial) pickplace-tmpl {
    duration: from <evt-scr-start> until <evt-scr-end>
    task: <tutorial-tsk>
    var robot
    var target-obj
    var place-ws

    When:
        Behaviour (ns=tutorial) pickplace-bhv {
            duration: from <evt-pick-start> until <evt-place-end>
            <robot> picks <target-obj> and places at <place-ws>
        }
}
```

This minimal scenario template can be used to generate to an RDF graph, e.g., in the turtle (TTL) format,
using the following `textx generate` command, which will print the TTL serialization to the terminal:

```sh
textx generate pickplace.bdd --target console --format ttl
```

We now walk through the key elements in this example, before introducing additional specifications.

### Identifiers

RDF graphs use [Internationalized Resource Identifiers (IRIs)](https://datatracker.ietf.org/doc/html/rfc3987)
to identify nodes. To accommodate this during graph generation, we include the namespace declaration
syntax `ns tutorial='http://...'`, which different models can point to, e.g. with `(ns=tutorial)`,
to form complete IRIs. The `tutorial` string is also used as prefix to form [compact IRIs](https://www.w3.org/TR/json-ld11/#dfn-compact-iri).
For example, `(ns=tutorial) pickplace-tmpl` will be transformed into a node with IRI
`https://secorolab.github.io/robbdd/tutorials/pickplace-tmpl`,
which has the short form `tutorial:pickplace-tmpl`.
IRIs allow extending a model in the generated graph with any additional information as needed,
as long as they refer the model's IRI.
In RobBDD, the element IDs, e.g., `evt-scr-start`, are combined with a namespace declaration,
e.g., `ns tutorial`, to generate the full IRI in the graph.
The namespace reference can either be explicit like with task or event declarations, or inherited from
the parent like with variable declarations.

### Minimal Scenario Template

A scenario template, defined with the `Scenario Template (ns=...) ... { ... }` block, outlines the
basic BDD Given-When-Then structure described above.
For a valid generation, a template require the following elements:

* A reference to a `Task`. For now, this is not exploited but can be extended with more
  specific task models in the future.
* A duration specification referring to the boundary events of the scenario.
* A behaviour declaration, e.g. `Behaviour (ns=tutorial) pickplace`, where the following part
  link to variable parameter of the behaviour. For now, only pick & place behaviours are
  supported, via the following syntax:
  - `<agn> picks <obj>`
  - `<agn> places <obj> at <ws>`
  - `<agn> picks <obj> and places at <ws>`
* A variable declaration, e.g. `var target-obj`, can be referred to by clauses & behaviour.
  The [section about scenario variations](#specifying-user-stories-and-scenario-variants) describes how
  variations can be introduced via these variables.
  - RobBDD syntax also includes set variables with syntax `set var var_name` for sets that can
    vary across scenario variants. Usage of this syntax will be explained in [a later section](#from-pick-and-place-to-sorting).

### Adding fluent clauses

Fluent clauses specify expectations about the behaviour under test. A fluent clause, e.g. `holds(...)`,
can be added to the `Given` & `Then` parts of the scenario, and composes a predicate, e.g. `is located at`,
a time constraint, e.g. `before ...`, with  corresponding variables, e.g. `<target-obj>`.
More details on this composition is described on [the "concepts" page](./bdd-concepts).
A general language for predicates is not available at the moment. Available syntax:

* supported predicates (all can generate RDF graphs, but some won't generate Gherkin for now):
  - `<obj> is located at <ws>`: fully supported
  - `<obj> is held by <agn>`: fully supported
  - `<obj> are sorted into <ws_set>`: fully supported
  - `<subject> has config <config>`: Gherkin gen. N/A
  - `<agn> can reach <obj>`: Gherkin gen. N/A
  - `<agn> does not drop <obj>`: Gherkin gen. N/A
  - `<agn> does not collide <target>`: Gherkin gen. N/A
* supported time constraints (all works with all generators):
  - `before <event>`
  - `after <event>`
  - `from <start_event> until <end_event>`

The two "located at" clauses in the above Gherkin example can be reproduced in RobBDD with the
following additions:

```diff
@@ -12,11 +12,18 @@
     task: <tutorial-tsk>
     var robot
     var target-obj
+    var pick-ws
     var place-ws

+    Given:
+        fc-located-before: holds(<target-obj> is located at <pick-ws>, before <evt-pick-start>)
+
     When:
         Behaviour (ns=tutorial) pickplace-bhv {
             duration: from <evt-pick-start> until <evt-place-end>
             <robot> picks <target-obj> and places at <place-ws>
         }
+
+    Then:
+        fc-located-after: holds(<target-obj> is located at <place-ws>, after <evt-place-end>)
 }
```

You can now run the `textx generate` command above again to see how the graph changes. Note that
we cannot generate to Gherkin at this point since no scenario variant is specified.

## Specifying a scene

To vary the above template, we must first specify the possible objects, workspaces, and agents
that can appear in the scene. To this end, RobBDD includes a scene specification DSL:

```txt
// pickplace.scene
ns lab_env='https://secorolab.github.io/models/environments/secorolab/'
ns isaac_agn='https://secorolab.github.io/models/agents/isaac-sim/'

obj set (ns=lab_env) pickplace_objects {
  object box1,
  object box2,
  object ball,
  object bottle
}
obj set (ns=lab_env) ws_objects {
  object container_1,
  object container_2,
  object dining_table,
  object shelf
}
ws set (ns=lab_env) lab_workspaces {
  workspace container_1_ws,
  workspace container_2_ws,
  workspace table_ws,
  workspace shelf_ws
}
agn set (ns=isaac_agn) isaac_agents {
  agent panda,
  agent ur10,
  agent kinova
}
comp (ns=lab_env) comp_table_pickplace of ws <lab_workspaces.table_ws> {
  obj <ws_objects.dining_table>
}
comp (ns=lab_env) comp_shelf_pickplace of ws <lab_workspaces.shelf_ws> {
  obj <ws_objects.shelf>
}
```

As shown in the exceprt, sets of scene elements can be declared, e.g. with
`obj set (ns=lab_env) pickplace_objects`, where the set elements inherit the set's namespace.
RobBDD also includes mechanism to specify compositions of workspaces, e.g.
`comp (ns=lab_env comp_table_pickplace)`. A workspace composition can contain objects, workspaces,
and other compositions. A scene model can then be specified by linking to element sets &
workspace compositions, e.g. in the excerpt below.

```txt
// pickplace.scene
scene (ns=scene_lab) pickplace_scene {
  obj set <pickplace_objects>
  ws comp <comp_table_pickplace>
  ws comp <comp_shelf_pickplace>
  agn set <isaac_agents>
}
```

For a sorting scenario where the robot place objects, in 2 containers, the scene composition
can be specified as follows:

```txt
comp (ns=lab_env) comp_container1 of ws <lab_workspaces.container_1_ws> { obj <ws_objects.container_1> }
comp (ns=lab_env) comp_container2 of ws <lab_workspaces.container_2_ws> { obj <ws_objects.container_2> }
comp (ns=lab_env) comp_table_sort of ws <lab_workspaces.table_ws> {
  obj <ws_objects.dining_table>
  ws comp <comp_container1>
  ws comp <comp_container2>
}
scene (ns=scene_lab) sorting_scene {
  obj set <pickplace_objects>
  ws comp <comp_table_sort>
  agn set <isaac_agents>
}
```

The scenario variant can link to specific scene model, as described further in
[the next section](#specifying-user-stories-and-scenario-variants).

## Specifying user stories and scenario variants

With the scene composition available, we can now specify variants of the above scenario template.
Here, a user story needs to be declared, e.g. `(ns=bdd_var) us_pickplace` below, as a collection
of scenario variants, e.g. `table_pick` below. a scenario variant links to a template,
a scene model, and declares variation of the scenario's variables.
Two types of variation are currently supported by RobBDD: table form like with
[Gherkin's `Examples` table in a `ScenarioOutline`](https://cucumber.io/docs/gherkin/reference/#scenario-outline),
and as the Cartesian products of sets of variable values.

### Table variation

The table-style variation links to scenario variables in the header row, separated from the
corresponding value rows by `|---|`. Each value rows will replace the variables in the scenario
clauses, similar to Gherkin's `Examples` table. Cell values can be links to scene elements,
e.g. `<pickplace_objects.box1>`, links to set of elements, e.g. `obj set <pickplace_objects>`,
or literal values like strings or numbers.

```txt
User Story (ns=bdd_var) us_pickplace {
  As A "Function Developer"
  I Want "Pick and place behaviour"
  So That "I can transport objects"

  Scenarios:
    Scenario table_pick {
      template: <tmpl_pickplace>
      scene: <pickplace_scene>

      variation:
      | <tmpl_pickplace.target_object> | <tmpl_pickplace.pick_ws> | <tmpl_pickplace.place_ws> | <tmpl_pickplace.robot> |
      |---|
      | <pickplace_objects.box1> | <lab_workspaces.table_ws> | <lab_workspaces.shelf_ws> |  <isaac_agents.panda> |
      | <pickplace_objects.ball> | <lab_workspaces.shelf_ws> | <lab_workspaces.table_ws> |  <isaac_agents.ur10> |
      | <pickplace_objects.bottle> | <lab_workspaces.table_ws> | <lab_workspaces.shelf_ws> | <isaac_agents.kinova> |
    }
}
```

### Cartesian product variation

In addition to the table syntax, a scenario variation can also be speficied as the
Cartesian product of sets of possible values:

```txt
Scenario simple_pick {
  template: <tmpl_pickplace>
  scene: <pickplace_scene>

  variation:
    var <tmpl_pickplace.target_object>: obj set <pickplace_objects>
    var <tmpl_pickplace.pick_ws>: set <ws_set>
    var <tmpl_pickplace.place_ws>: set <ws_set>
    var <tmpl_pickplace.robot>: {
      <isaac_agents.panda>, <isaac_agents.ur10>
    }
}
```

Here, value sets can be specified in several ways:

* as a link to scene element sets, e.g. `obj set <pickplace_objects>`
* as inline explicit set, e.g. with `<tmpl_pickplace.robot>`, via the syntax `{ elem1, elem2, ... }`
* link to an explicit set declared before scenario templates, e.g. `ws_set`:

  ```txt
  ...
  const set (ns=bdd_var) ws_set {
    <lab_workspaces.table_ws>, <lab_workspaces.shelf_ws>
  }
  Scenario Template (ns=tutorial) tmpl_pickplace {
  ...
  ```

> [!IMPORTANT]  
> The above syntax is only for non-set variable. Separate syntax is required for a set variable,
> as the collection of its possible values must be a set of sets. We describe this in more details
> in the [following section](#from-pick-and-place-to-sorting).

## From pick and place to sorting

In [^hunecke2025erf], we discussed the extensions needed for our BDD tool chain to represent an
object sorting scenario, which can be considered as repeating the pick & place behaviours for
multiple objects and workspaces. This section describes how this extensions can be specified
with RobBDD. Following is a template for such a sorting scenario:

```txt
Scenario Template (ns=tutorial) tmpl_sort {
  task: <tsk_sorting>

  set var target_objects
  set var place_workspaces
  var robot
  var pick_ws

  for all ( var x in <target_objects> ) {
    Given:
    (
      holds(<x> is located at <pick_ws>, before <evt_pick_start>)
    )
    When:
      Behaviour (ns=tutorial) pickplace: <robot> picks <x> and places at <place_workspaces>
    Then:
      ( var y exists in <place_workspaces> ) such that {
          holds(<x> is located at <y>, after <evt_place_end>)
      }
  }
  Then:
      holds(<target_objects> are sorted into <place_workspaces>, after <evt_place_end>)
}
```

Here, we introduce set quantifiers and set variables to represent the sorting scenario:

* A set variable, e.g. `set var target_objects`, is used for a set of element that can change
  across scenario variations. In the example, the concept is used for the set of objects to be
  sorted and the set of workspaces they should be sorted into. Set variables are also expected
  by the sorting clause at the end of the template.
* Set quantifiers, namely universal & existential quantifiers, are used for specifying clauses
  for sets of elements. Both declares a variable, e.g. `x`, `y`, that the contained clauses can
  refer to. Both must refer to a set variable, e.g. `set var target_objects`,
  as the quantified set.
  - The universal quantifier, e.g. `for all var x in <target_objects>`:
    + repeats contained clauses for all elements in the object set
    + cannot exist in the same scope with the behaviour clause, as the behaviour needs to be
      executed every iteration
  - The existential quantifier evaluates true if the contained expression holds true for
    any of the set elements.

```txt
Scenario simple_pick {
  template: <tmpl_sort>
  scene: <sorting_scene>

  variation:
    set var <tmpl_sort.target_objects>: select 3 combinations from <pickplace_objects>
    var <tmpl_sort.pick_ws>: {
      <lab_workspaces.table_ws>, <lab_workspaces.shelf_ws>
    }
    set var <tmpl_sort.place_workspaces>: select 2 combinations from <sort_ws_set>
    set var <tmpl_sort.place_workspaces>: {
      { <lab_workspaces.container_1_ws>, <lab_workspaces.container_2_ws> },
      { <lab_workspaces.container_2_ws>, <lab_workspaces.container_1_ws> }
    }
    var <tmpl_sort.robot>: agn set <isaac_agents>
}
```

In the scenario variant, variation of a set variable needs to resolve to a set of sets, and
can be specified in 2 main ways:

* set enumeration syntax, e.g. `select [size] combinations from <[linked set]>`:
  - both combination & permutation of sets are supported
  - `repeated` can be added to combination syntax, e.g. `select 2 repeated combinations...`
    to specify that elements can be repeated in enumerations
  - linked set can be explicitly declared sets or scene sets, e.g. `pickplace_objects`
* explicitly listing set of sets elements, like with `place_workspaces` in the excerpt.

## Code generation

Details on the supported generators and addititonal arguments are documented on the
[RobBDD repository](https://github.com/minhnh/robbdd). Generating the Gherkin feature file
from a RobBDD model can be done with:

```console
foo@bar:~$ textx generate path/to/model.bdd --target gherkin -o path/to/generated/dir
```

## References

[^hunecke2025erf]: B. Hunecke, M. Nguyen, N. Hochgeschwender, S. Wrede, "Specification and Execution of Robotic Acceptance Tests for Object Sorting", In: [_European Robotics Forum 2025_](https://link.springer.com/book/9783031894701). Springer Proceedings in Advanced Robotics, vol 36, June 2025.
