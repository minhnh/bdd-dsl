# Tutorial: Generating Gherkin features for a simple pickup task

This tutorial will first showcase how [concepts from our metamodels](bdd-concepts.md) can be used
to model acceptance criteria of a simple pickup task as Behaviour-Driven Development (BDD)
scenarios, as well as how variations of such scenarios can be introduced in the model. An example
is then presented to show how to transform this model into a
[Gherkin](https://cucumber.io/docs/gherkin/reference/) feature for integration with appropriate
BDD toolchains, e.g. [`behave`](https://behave.readthedocs.io) for the Python language.

## Specifying BDD Acceptance Criteria for a Pickup Task

| ![BDD Template and Variant Example](assests/../assets/img/bdd-example-pickup.svg) |
|:-:|
| Figure 1: Partial example of a BDD scenario template and variant for the pickup task. |

As mentioned in the [description of our metamodels](bdd-concepts.md), our models are graphs
represented using the JSON-LD schema. Figure 1 shows part of such a graph, which consists of a BDD
scenario template and corresponding variants for a simple pickup task. The rest of this section will
walk through the process of creating this example. The motivation of the metamodel design and
detailed descriptions of their concepts and relations can be found on the
[documentation for the relevant metamodels](bdd-concepts.md). Complete JSON for the BDD scenario
[template](https://hbrs-sesame.github.io/models/acceptance-criteria/bdd/templates/pickup.json)
and [variant](https://hbrs-sesame.github.io/models/acceptance-criteria/bdd/pickup-variants.json)
are also available online.

### Specifying Scenario Templates

First, we define the skeleton of the BDD scenario for the pickup task: a `bdd:Scenario` having one
instance of each `bdd:GivenClause`, `bdd:WhenClause`, and `bdd:ThenClause` concepts.

```json
{ "@id": "pick-given", "@type": "bdd:GivenClause" },
{ "@id": "pick-when", "@type": "bdd:WhenClause" },
{ "@id": "pick-then", "@type": "bdd:ThenClause" },
{
    "@id": "scenario-pick", "@type": "bdd:Scenario",
    "bdd:given": "pick-given",
    "bdd:when": "pick-when",
    "bdd:then": "pick-then"
}
```

Next, we define `bdd:ScenarioVariable` instances, which are points of variation of the
scenario template. Here, we may vary the object, workspace, and agent in the pickup scenario.

```json
{
    "@id": "pick-object", "@type": "bdd:ScenarioVariable",
    "of-scenario": [ "scenario-pick" ]
},
{
    "@id": "pick-workspace", "@type": "bdd:ScenarioVariable",
    "of-scenario": [ "scenario-pick" ]
},
{
    "@id": "pick-robot", "@type": "bdd:ScenarioVariable",
    "of-scenario": [ "scenario-pick" ]
}
```

Having defined the variables, we can now construct `bdd:FluentClause` instances, which can be
attached to `pick-given` and `pick-then` to extend `scenario-pick` with more concrete clauses.
In the example below, we define `fluent-obj-held-by-robot`, which asserts that the object is held
by the robot, e.g. via association with predicate `pred-obj-held-by-robot`, at the end of the
picking behaviour, e.g. via association with time constraint `after-pick`.
`fluent-obj-held-by-robot` is linked to `pick-then` of `scenario-pick`, and refers to variables
`pick-object` and `pick-robot`.

```json
{ "@id": "pred-obj-held-by-robot", "@type": "bdd:IsHeldPredicate" },
{ "@id": "after-pick", "@type": "bdd:TimeConstraint" },
{
    "@id": "fluent-obj-held-by-robot",
    "@type": "bdd:FluentClause",
    "clause-of": [ "pick-then" ],
    "predicate": "pred-obj-held-by-robot",
    "time-constraint": "after-pick",
    "ref-object": "pick-object",
    "ref-agent": "pick-robot"
}
```

### Specifying concrete scenario variant

The BDD scenario template defined above can now be extended with concrete variations, e.g. for
generating concrete Gherkin feature files as shown in
[the next section](#generating-gherkin-features-from-json-ld-models). For example, we would like
to test the pickup behaviour in the robotics lab at Bonn-Rhein-Sieg University using battery cells
sent from [AVL](https://www.avl.com) (An use case partner of the SESAME project), as well as some
objects readily available in the lab.

#### Specifying concrete agents, environment, and coordination models

We first need concrete models of the objects, workspaces, and agents that we may test with:
```json
{ "@id": "bottle", "@type": "env:Object" },
{ "@id": "pouch1", "@type": [ "bdd:Object", "avl:PouchCell" ] },
{ "@id": "prismatic1", "@type": [ "bdd:Object", "avl:PrismaticCell" ] },
{ "@id": "dining-table-ws", "@type": "env:Workspace" },
{ "@id": "kinova1", "@type": [ "agn:Agent", "kinova:gen3-robots" ] },
{ "@id": "kinova2", "@type": [ "agn:Agent", "kinova:gen3-robots" ] }
```

We also need a coordination model which defines the event that denotes the start of the pickup
behaviour, which we can associate with `pickup-when`.

```json
{ "@id": "pickup-start", "@type": "evt:Event" }
```

#### Specifying variations

Using the `task:Variation` concept, we can associate the `bdd:ScenarioVariable` variables above
with possible variations to be tested:

```json
{
    "@id": "obj-variation", "@type": "task:Variation",
    "of-variable": "pick-object",
    "can-be": [ "bottle", "pouch1", "prismatic1" ]
},
{
    "@id": "ws-variation", "@type": "task:Variation",
    "of-variable": "pick-workspace",
    "can-be": [ "dining-table-ws" ]
},
{
    "@id": "robot-variation", "@type": "task:Variation",
    "of-variable": "pick-robot",
    "can-be": [ "kinova1", "kinova2" ]
}
```

The `pick-when` can be associated with the concrete event `pickup-start`.

```json
{
    "@id": "pick-when-event", "@type": "bdd:WhenEvent",
    "of-clause": "pick-when", "has-event": "pickup-start"
}
```

We can now define variant `scenario-pick-brsu` as a composition of the `task:Variation`
instances, and user story `us-obj-transport` as a composition of scenario variants, one of which is
`scenario-pick-brsu`.

```json
{
    "@id": "scenario-pick-brsu", "@type": "bdd:ScenarioVariant",
    "of-scenario": "scenario-pick",
    "has-variation": [
        "obj-variation", "ws-variation", "robot-variation"
    ]
},

{
    "@id": "us-obj-transport", "@type": "bdd:UserStory",
    "has-criteria": [ "scenario-pick-brsu" ]
}
```

## Generating Gherkin Features from JSON-LD Models

### Transform

Querying with [SPARQL](https://www.w3.org/TR/rdf-sparql-query/)

Framing

### Generating from Jinja Templates

> TODO: include video, maybe in top level README
