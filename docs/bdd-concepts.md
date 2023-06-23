# Metamodels for Specifying BDD Scenarios for Robotic Applications

![Rulebook feature model](assets/img/rulebook_features-current-colored.svg "A Feature Model of Robotic Competitions")

A result from our analysis of rulebooks from several robotic benchmarks and
competitions[^nguyen2023rulebook] is a [feature model](https://en.wikipedia.org/wiki/Feature_model)
containing elements, i.e. "features," used to describe test scenarios in robotic competitions.
This serves as the basis for the metamodels described below.

| File | Description |
|:---|:---|
| [`agent.json`](https://hbrs-sesame.github.io/metamodels/agent.json) |  |
| [`environment.json`](https://hbrs-sesame.github.io/metamodels/environment.json) |  |
| [`bdd.json`](https://hbrs-sesame.github.io/metamodels/acceptance-criteria/bdd.json) |  |

## JSON-LD Recap

The metamodels and models included in this library are represented using the
[JSON-LD Schema](https://json-ld.org/), which extends the JSON format for representing linked data.
More details on this W3C standard can be found on the corresponding
[online documentation](https://www.w3.org/TR/json-ld11/). TODO: refer to Sven's modelling tutorial.

## Metamodels for Scenario Definition

Definition of robotic scenarios, as shown in the above figure, requires descriptions of the agent,
the environment and the task.

### Agent

Concepts and relations for specifying agents in a scenario are defined in [`agent.json`](https://hbrs-sesame.github.io/metamodels/agent.json)

### [`environment.json`](https://hbrs-sesame.github.io/metamodels/environment.json)

### Task

TODO: rename VariableConnection to TaskVariation

## BDD Concepts and Relations

### [`bdd.json`](https://hbrs-sesame.github.io/metamodels/acceptance-criteria/bdd.json)

## References

[^nguyen2023rulebook]: M. Nguyen, N. Hochgeschwender, S. Wrede, "An analysis of behaviour-driven requirement specification for robotic competitions", [_5th International Workshop on Robotics Software Engineering (RoSE’23)_](https://rose-workshops.github.io/rose2023/), May 2023.
