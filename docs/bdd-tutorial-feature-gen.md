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
[documentation for the relevant metamodels](bdd-concepts.md).

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

Next, we define `bdd:ScenarioVariable` nodes

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

Attaching fluent clauses

```json
{ "@id": "pred-obj-held-by-robot", "@type": "bdd:IsHeldPredicate" },
{ "@id": "after-pick", "@type": "bdd:TimeConstraint" },
{
    "@id": "fluent-obj-held-by-robot",
    "@type": [ "bdd:FluentClause", "bdd:IsHeldPredicate" ],
    "clause-of": [ "pick-then", "lift-then" ],
    "predicate": "pred-obj-held-by-robot",
    "time-constraint": "after-pick",
    "ref-object": "pick-object",
    "ref-agent": "pick-robot"
}
```

### Specifying concrete agents and environment models

### Specifying event loop coordination model

### Specifying concrete scenario variant

Variable connections / Task variation

```json
{
    "@id": "object-connection", "@type": "bdd:VariableConnection",
    "of-variable": "bdd-tmpl:pick-object",
    "has-variation": [ "hbrs-env:box", "hbrs-env:bottle" ]
},
{
    "@id": "workspace-connection", "@type": "bdd:VariableConnection",
    "of-variable": "bdd-tmpl:pick-workspace",
    "has-variation": [ "hbrs-env:dining-table" ]
},
{
    "@id": "robot-connection", "@type": "bdd:VariableConnection",
    "of-variable": "bdd-tmpl:pick-robot",
    "has-variation": [ "hbrs-agents:kinova1" ]
}
```

Connection to event from coordination model

```json
{
    "@id": "approach-when-event", "@type": "bdd:WhenEvent",
    "of-clause": "bdd-tmpl:approach-when", "has-event": "crdnm:approach-start"
}
```

Scenario composition of the variations

```json
{
    "@id": "scenario-pick-1-arm", "@type": "bdd:ScenarioVariant",
    "of-scenario": "bdd-tmpl:scenario-pick",
    "has-var-connection": [
        "object-connection", "workspace-connection", "robot-connection"
    ]
}
```

Composition of scenarios into user story

```json
{
    "@id": "us-obj-transport-single-arm", "@type": "bdd:UserStory",
    "has-criteria": [ "scenario-pick-1-arm" ]
}
```

## Generating Gherkin Features from JSON-LD Models

### Transform

Querying with [SPARQL](https://www.w3.org/TR/rdf-sparql-query/)

Framing

### Generating from Jinja Templates

> TODO: include graphics

## References

[^alferez2019]: M. Alferez, F. Pastore, M. Sabetzadeh, et al., "Bridging the Gap between Requirements Modeling and Behavior-Driven Development," _22nd MODELS_, 2019, doi: [10.1109/MODELS.2019.00008](https://doi.org/10.1109/MODELS.2019.00008).
