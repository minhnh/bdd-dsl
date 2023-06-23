# Metamodels for Specifying BDD Scenarios for Robotic Applications

## Metamodel Design

### Quick Review of Behaviour-Driven Development (BDD)

Requirements in Test-Driven Development (TDD) are often represented using _User Stories_,
typically in the following format:

```
As a [Stakeholder role]
I want [Feature]
So that [Benefit]
```

In his original blog post[^north2003bdd] introducing BDD, North proposed to represent acceptance criteria for each user story as a list of scenarios capturing the expected behaviours of the system,
each using the following formulation:

``` Gherkin
Given [Precondition]
When [Event]
Then [Expected Outcome]
```

> **TODO**: refer to previous deliverables? public links available?

### Specifying Robotic Scenarios

A challenge of applying BDD to any complex domains is to deal with the myriad variations that may
exist for the same scenario. Alferez et al.[^alferez2019] proposed to define scenario templates for
common system behaviours, e.g. in their use case for operations on different data structures.
Concrete BDD scenarios can then be generated from these templates depending on the particular data
object being tested.

|![Rulebook feature model](assets/img/rulebook_features-current-colored.svg)|
|:-:|
|Figure 1: A Feature Model of Robotic Competitions|

We aim to apply a similar idea for representing robotic scenarios, whose variability dimensions can
be vastly more numerous and complex compared to the application investigated by
Alferez et al.[^alferez2019]. To this end, we analysed rulebooks from several robotic benchmarks
and competitions[^nguyen2023rulebook] to identify common elements used to describe test scenarios
at these events. We consolidate our findings is a
[Feature Model](https://en.wikipedia.org/wiki/Feature_model), shown in Figure 1.
This serves as the basis for the metamodels described below.

## Metamodel Description

We choose to represent our metamodels and models for specifying BDD scenarios with the
[JSON-LD Schema](https://json-ld.org/). The metamodels described below can be found in the
following files:

| File | Description |
|:---|:---|
| [`agent.json`](https://hbrs-sesame.github.io/metamodels/agent.json) | Metamodel for specifying agents in a scenario |
| [`environment.json`](https://hbrs-sesame.github.io/metamodels/environment.json) | Metamodel for specifying the environment in a robotic scenario |
| [`event.json`](https://hbrs-sesame.github.io/metamodels/coordination/event.json) | Metamodel for specifying event-driven coordination of robot behaviours |
| [`bdd.json`](https://hbrs-sesame.github.io/metamodels/acceptance-criteria/bdd.json) | Metamodel for specifying BDD templates and their variants |

### JSON-LD Recap

JSON-LD extends the JSON format for representing linked data. More details on this W3C standard
can be found on the corresponding [online documentation](https://www.w3.org/TR/json-ld/). Models in
JSON-LD are identified using International Resource Identifiers (IRI) with the `@id` keyword.
For brevity, we also use [compact IRIs](https://www.w3.org/TR/json-ld/#compact-iris)
(`:` separating prefix and suffix) when referring to metamodels concepts and relations below.
Other important keywords:
- `@context`
- `@graph`
- `@type`

> **TODO**: refer to Sven's modelling tutorial or describe the basic keywords here?

### Agent

|Prefix|
|:-|
|`{ agn: "https://hbrs-sesame.github.io/metamodels/agent#" }`|

### Environment

### Task

> TODO: rename VariableConnection to TaskVariation

### BDD Scenario Templates and Variants

## References

[^north2003bdd]: [D. North, "Behavior Modification: The evolution of behaviour-driven development", _Better Software_, 2006.](https://dannorth.net/introducing-bdd/)

[^nguyen2023rulebook]: M. Nguyen, N. Hochgeschwender, S. Wrede, "An analysis of behaviour-driven requirement specification for robotic competitions", [_5th International Workshop on Robotics Software Engineering (RoSE’23)_](https://rose-workshops.github.io/rose2023/), May 2023.

[^alferez2019]: M. Alferez, F. Pastore, M. Sabetzadeh, et al., "Bridging the Gap between Requirements Modeling and Behavior-Driven Development," _22nd MODELS_, 2019, doi: [10.1109/MODELS.2019.00008](https://doi.org/10.1109/MODELS.2019.00008).
