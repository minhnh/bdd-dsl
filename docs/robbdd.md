# Tutorial: Modeling pick & place applications using RobBDD

This tutorial shows how to use the [RobBDD](https://github.com/minhnh/robbdd)
Domain-Specific-Language (DSL) to model robotics acceptance criteria and generate
[Gherkin](https://cucumber.io/docs/gherkin/reference/) feature files for acceptance test
execution of pick & place scenarios. The following model examples can also be found under
the `examples/models` folder in the RobBDD repository.

## Specifying a scenario template

We begins with specifying a simple pick & place scenario, which in Gherkin may look like
the following:

```gherkin
Scenario Outline: pickplace scenario
  Given <object> is located at <pick_ws>
  When the robot picks <object> and places it at <place_ws>
  Then the object is located at <place_ws>
```

With RobBDD, we first specify this as a scenario template:

```txt
// pickplace.bdd
ns bdd_tmpl='https://secorolab.github.io/models/acceptance-criteria/bdd/templates/'

Task (ns=bdd_tmpl) tsk_pickplace
Event (ns=bdd_tmpl) evt_pick_start
Event (ns=bdd_tmpl) evt_place_end

Scenario Template (ns=bdd_tmpl) tmpl_pickplace {
    task: <tsk_pickplace>

    var target_object
    var robot
    var pick_ws
    var place_ws

    Given:
        holds(<target_object> is located at <pick_ws>, before <evt_pick_start>)
    When:
        Behaviour (ns=bdd_tmpl) pickplace: <robot> picks <target_object> and places at <place_ws>
    Then:
        holds(<target_object> is located at <place_ws>, after <evt_pick_start>)
}
```

### Identifiers

RDF graphs use [Internationalized Resource Identifiers (IRIs)](https://datatracker.ietf.org/doc/html/rfc3987)
to identify nodes. To accomodate this during graph generation, we include the namespace declaration
syntax `ns bdd_tmpl='http://...'`, which different models can point to, e.g. with `(ns=bdd_tmpl)`,
to form complete IRIs. The `bdd_tmpl` string is also used as prefix to form [compact IRIs](https://www.w3.org/TR/json-ld11/#dfn-compact-iri).
For example, `(ns=bdd_tmpl) tmpl_pickplace` will be transformed into a node with IRI
`https://secorolab.github.io/models/acceptance-criteria/bdd/templates/tmpl_pickplace`,
which has the short form `bdd_tmpl:tmpl_pickplace`.
IRIs allow extending a model in the generated graph with any additional information as needed,
as long as they refer the model's IRI.

### Template elements

A scenario template consists of the following essential elements:

- A template reference a `Task`. For now, this is not exploited but can be extended with more
  specific task models in the future.
- Declared variables, e.g. `var target_object`, can be referred to by clauses & behaviour.
  A later section describes how scenario variations can be introduced via these variables.
- A declared behaviour, e.g. `Behaviour (ns=bdd_tmpl) pickplace`, where the following part
  link to variable parameter of the behaviour. For now, only pick & place behaviours are
  supported, via the following syntax:
  - `<agn> picks <obj>`
  - `<agn> places <obj> at <ws>`
  - `<agn> picks <obj> and places at <ws>`
- A fluent clause, e.g. `holds(...)`, can be added to the `Given` & `Then` parts of the scenario,
  and composes a predicate, e.g. `is located at`, a time constraint, e.g. `before ...`, with
  corresponding variables, e.g. `<target_object>`. More details on this composition is described
  on [the "concepts" page](./bdd-concepts). A general language for predicates is not available
  at the moment. Available syntax:
  - supported predicates (all can generate RDF graphs, but some won't generate Gherkin for now):
    - `<obj> is located at <ws>`: fully supported
    - `<obj> is held by <agn>`: fully supported
    - `<obj> are sorted into <ws_set>`: fully supported
    - `<subject> has config <config>`: Gherkin gen. N/A
    - `<agn> can reach <obj>`: Gherkin gen. N/A
    - `<agn> does not drop <obj>`: Gherkin gen. N/A
    - `<agn> does not collide <target>`: Gherkin gen. N/A
  - supported time constraints (all works with all generators):
    - `before <event>`
    - `after <event>`
    - `from <start_event> until <end_event>`

## Specifying a scene

## Specifying a scenario variant

### Table variation

### Cartesian product variation

## Code generation

## From pick & place to sorting
