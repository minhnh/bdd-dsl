# Metamodels for Specifying BDD Scenarios in Robotics

## Table of content

<!-- mtoc-start -->

* [Background](#background)
  * [Behaviour-Driven Development (BDD)](#behaviour-driven-development-bdd)
  * [AC in robotic competitions & benchmarks](#ac-in-robotic-competitions--benchmarks)
* [Conceptualizing Robotic Acceptance Criteria (AC)](#conceptualizing-robotic-acceptance-criteria-ac)
  * [Example: modelling a pick-and-place scenario](#example-modelling-a-pick-and-place-scenario)
  * [Clauses as fluents](#clauses-as-fluents)
  * [Variation and Scene](#variation-and-scene)
  * [Scenario Template, Variant, & User Story](#scenario-template-variant--user-story)
* [Representing Robotic AC as Knowledge Graphs](#representing-robotic-ac-as-knowledge-graphs)
* [References](#references)

<!-- mtoc-end -->

## Background

### Behaviour-Driven Development (BDD)

Requirements in Test-Driven Development (TDD) are often represented using _User Stories_,
typically in the following format:

```text
As a [Stakeholder role]
I want [Feature]
So that [Benefit]
```

In his original blog post[^north2003bdd] introducing BDD, North proposed to represent
AC for each user story as a list of scenarios capturing the expected behaviours
of the system, each using the following formulation:

```Gherkin
Given [Precondition]
When [Event/Action]
Then [Expected Outcome]
```

This formulation extends user stories with _narratives_, each consist of initial condition(s),
events or actions that signal the start of the behaviour, and the criteria that characterizes
what constitute a successful behaviour. We consider the `Given-When-Then` formulation a
good metamodel because of its simple concepts, which are both easy to understand and flexible
to different interpretations and extensions. Furthermore, BDD approaches, e.g. with the popular
[Gherkin syntax](https://cucumber.io/docs/gherkin/reference/), has wide support in the
software engineering community for test automation in many program languages and frameworks.
This can reduce the effort in generating executable implementations for verifying BDD
AC in the future.

### AC in robotic competitions & benchmarks

A challenge of applying BDD to any complex domains is to deal with the myriad variations that may
exist for the same scenario. Alferez et al.[^alferez2019] proposed to define scenario templates for
common system behaviours, e.g. in their use case for operations on different data structures.
Concrete BDD scenarios can then be generated from these templates depending on the particular data
object being tested.

|![Rulebook feature model](assets/img/rulebook_features-current-colored.svg)|
|:-:|
|Fig. 1: A Feature Model of Robotic Competitions|

We aim to apply a similar idea for representing robotic scenarios, whose variability dimensions can
be vastly more numerous and complex compared to the application investigated by
Alferez et al.[^alferez2019]. To this end, we analysed rulebooks from several robotic benchmarks
and competitions[^nguyen2023rulebook] to identify common elements used to describe test scenarios
at these events. We consolidate our findings is a
[Feature Model](https://en.wikipedia.org/wiki/Feature_model), shown in Fig. 1.
This serves as the basis for designing a metamodel, i.e., model of model,
for BDD robotic scenarios, as shown in Fig. 2

## Conceptualizing Robotic Acceptance Criteria (AC)

|![BDD meta-model concepts](assets/img/bdd-concepts.svg)|
|:-:|
|Fig. 2: A metamodel to specify BDD scenarios in robotics|

### Example: modelling a pick-and-place scenario

To help with understanding the design of our MM, let's start with a BDD specification for a
simple pick & place application. Below is a potential Gherkin feature for this example, where the
scenario is split into two phases for object picking and placing:

```Gherkin
Feature: Object pick and place

  Scenario Outline: Object pickup
    Given "<object>" is located at "<pick_ws>"
    When "<robot>" picks up "<object>"
    Then "<object>" is held by "<robot>"
    Examples:
      |object|pick_ws|robot|
      |...|...|...|

  Scenario Outline: Object placing
    Given "<object>" is held by "<robot>"
    When "<robot>" places "<object>" at "<place_ws>"
    Then "<object>" is located at "<place_ws>"
    Examples:
      |object|robot|place_ws|
      |...|...|...|
```

Issues with Gherkin & current BDD frameworks, including implicit timing information & limited
flexibility in coordinating scenario execution, are discussed at length in [^nguyen2023rulebook].
Here, we use this example to help explaining the design of our metamodels in the following sections.

### Clauses as fluents

Current BDD approaches generally do not support specifying _when_ scenario clauses should hold
true. For instance, the “is held by” clause in the Gherkin example above asserts that the robot
holds the target object after completing the pickup behaviour. The same assertion must hold before
the placing behaviour in the second scenario. To capture temporal element in BDD clauses, we model
them using the fluent concept, i.e., time varying properties of the world [^miller2002]. A fluent
includes a predicate asserting a property of interest and a term indicating when the assertion
should be valid. Different formalisms of dynamic logic diverge mainly in how to represent the
temporal term.

|![Pick & place example model - Fluents](assets/img/bdd-example-pickplace-fluents.svg)|
|:-:|
|Fig. 3: Modelling BDD clauses as fluents|

Fig. 3 shows an example of how we apply the fluent concept to model BDD clauses.
Key design points:

* A `FluentClause` represents a BDD clause that is also a fluent, and can be a `Given` or a `Then`
  clause of a BDD scenario. The concept links to the scenario via the `clause-of` relation.
  Whether the clause connects to a `Given` or `Then` denotes its role in the scenario,
  i.e., whether it's a pre- or post- condition of the behaviour to be verified.
* The semantics of the fluent's predicate is introduced via additional types of
  the `FluentClause` node, e.g. `IsHeldPredicate` & `IsLocatedPredicate` in Fig. 3.
* A `FluentClause` composes the fluent/predicate with its subject, e.g. the `target-object`
  to be held in Fig. 3, where the subjects are `ScenarioVariable`, and their role in the fluent
  is encoded in the relation to the `FluentClause`, e.g. `ref-object`. Variables allow preserving
  semantics of elements in clauses, interdependent scenarios, and variations. For example,
  in Fig. 3 the same `target-object` should be located at `pick-ws` before picking & at `place-ws`
  after placing.
* A `FluentClause` also links to a `TimeConstraint`, which can have more specific types denoting
  how the temporal term should be interpreted, e.g. `BeforeEventConstraint` & `AfterEventConstraint`
  in Fig. 3 for assertions that should hold relative to an event, i.e. time instant. Here, the
  example shows how the 2 "is held by" fluent clauses have different time constraints in the 2
  scenarios -- after picking & before placing.

### Variation and Scene

Fig. 1 lists objects, workspaces & agents as part of scenario specification. These elements may
vary between variations of a scenario (possible in Gherkin via the [`Examples`](https://cucumber.io/docs/gherkin/reference/#examples) table).
A scenario specification may also include invariant elements, e.g., for specifying grasping from
cluster tasks or furnitures that remain unchanged.

|![Pick example model - Scene & task variation](assets/img/bdd-example-pickplace-scene_variation.svg)|
|:-:|
|Fig. 4: Modelling varying & invariant elements in a BDD scenario|

Therefore, we introduce in our metamodel the `Scene` & `TaskVariation` concepts for specifying
invariant & varying elements, respectively. An example of this design is shown in Fig. 4.
Key design points:

* Each `ScenarioTemplate` is associated with a `Scene`, which can be composed with objects,
  workspaces, agents, e.g. cup & bottle in Fig. 4.
* A `TaskVariation` composes a scenario's variables with its values in different scenario variants
* `TaskVariation` can have additional types for specific variation mechanism. In Fig. 4,
  `object-variation` has type `TableVariation`, which allows specifying variables' values in
  a table similar to Gherkin's `Examples`. We also support `CartesianProductVariation` that allows
  specifying set of values for each variable & compute the Cartesian product of these sets as the
  scenario variations.
* A `ScenarioVariant` composes a template and its `TaskVariation`

### Scenario Template, Variant, & User Story

|![Pick example model - composition](assets/img/bdd-example-pickplace-compositions.svg)|
|:-:|
|Fig. 5: Modelling BDD scenario template, variant & user story|

Our metamodel includes two composites to represent concrete BDD scenarios, namely
`ScenarioTemplate` and `ScenarioVariant`. `UserStory` is then a composite of scenario variants.
Key design points:

* A `ScenarioTemplate` is associated with 1 `Scene` (as described in the previous section).
* A `ScenarioVariant` composes variations with scenario variables, as well as the template's scene
  with concrete elements (as described in previous section).
* A scenario variant may have additional `FluentClause` that is not part of the template, e.g.
  `clause-not-collide-pick` in Fig. 5.

## Representing Robotic AC as Knowledge Graphs

We choose to represent our metamodels and models for specifying BDD scenarios with the
[JSON-LD Schema](https://json-ld.org/). The JSON-LD representation of the BDD metamodel described
here can be found on our [metamodels](https://secorolab.github.io/metamodels/) page, and the
corresponding models on the [models](https://secorolab.github.io/models/) page.
Notable models:

| Model | Description |
|:-|:-|
| [pickplace.tmpl.json](https://secorolab.github.io/models/acceptance-criteria/bdd/templates/pickplace.tmpl.json) | JSON-LD model for a pick & place scenario template |
| [pickplace-secorolab-isaac.var.json](https://secorolab.github.io/models/acceptance-criteria/bdd/pickplace-secorolab-isaac.var.json) | JSON-LD model for variants of the above template |
| [secorolab-env.scene.json](https://secorolab.github.io/models/acceptance-criteria/bdd/scenes/secorolab-env.scene.json) | JSON-LD model of scenes used in the above scenario variants |
| [secorolab.env.json](https://secorolab.github.io/models/acceptance-criteria/bdd/environments/secorolab.env.json) | JSON-LD model for the environment elements used in the scenes & scenario variants above |

For an overview of main JSON-LD keywords used in our models, please take a look at our
[modelling tutorial](https://github.com/comp-rob2b/modelling-tutorial#json-ld). More details on
this standard can be found on the [official online documentation](https://www.w3.org/TR/json-ld/).

## References

[^north2003bdd]: [D. North, "Behavior Modification: The evolution of behaviour-driven development", _Better Software_, 2006.](https://dannorth.net/introducing-bdd/)

[^nguyen2023rulebook]: M. Nguyen, N. Hochgeschwender, S. Wrede, "An analysis of behaviour-driven requirement specification for robotic competitions", [_5th International Workshop on Robotics Software Engineering (RoSE’23)_](https://rose-workshops.github.io/rose2023/), May 2023.

[^alferez2019]: M. Alferez, F. Pastore, M. Sabetzadeh, et al., "Bridging the Gap between Requirements Modeling and Behavior-Driven Development," _22nd MODELS_, 2019, doi: [10.1109/MODELS.2019.00008](https://doi.org/10.1109/MODELS.2019.00008).

[^miller2002]: R. Miller and M. Shanahan, “Some Alternative Formulations of the Event Calculus,” in Comp. Logic: Logic Programming and Beyond, vol. 2408, 2002, pp. 452–490, doi: [10.1007/3-540-45632-5_17](https://doi.org/10.1007/3-540-45632-5_17).
