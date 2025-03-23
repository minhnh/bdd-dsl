# Metamodels for Specifying BDD Scenarios in Robotics

## Conceptualizing Robotic Acceptance Criteria (AC)

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

### Foundation: AC in robotic competitions & benchmarks

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
This serves as the basis for designing a metamodel for BDD robotic scenarios, as shown in Fig. 2

### A BDD Metamodel for robotics

|![Rulebook feature model](assets/img/bdd-concepts.svg)|
|:-:|
|Fig. 2: A metamodel to specify BDD scenarios in robotics|

#### Example: modelling a pick-and-place scenario

To help with understanding the design of our metamodel, let's start with a BDD specification for a
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

#### Clauses as fluents

Current BDD approaches generally do not support specifying _when_ scenario clauses should hold
true. For instance, the “is held by” clause in the Gherkin example above asserts that the robot
holds the target object after completing the pickup behaviour. The same assertion must hold before
the placing behaviour in the second scenario. To capture temporal element in BDD clauses, we model
them using the fluent concept, i.e., time varying properties of the world [^miller2002]. A fluent
includes a predicate asserting a property of interest and a term indicating when the assertion
should be valid. Different formalisms of dynamic logic diverge mainly in how to represent the
temporal term.

|![Rulebook feature model](assets/img/bdd-example-pickplace-fluents.svg)|
|:-:|
|Fig. 3: A metamodel to specify BDD scenarios in robotics|

Fig. 3 shows an example of how we apply the fluent concept to model BDD clauses.
Key design points:

- A `FluentClause` represents a BDD clause that is also a fluent, and can be a `Given` or a `Then`
  clause of a BDD scenario. The concept links to the scenario via the `clause-of` relation.
- The semantics of the fluent's predicate is introduced via additional types of
  the `FluentClause` node, e.g. `IsHeldPredicate` & `IsLocatedPredicate` in Fig. 3.
- A `FluentClause` composes the fluent/predicate with its subject, e.g. the `target-object`
  to be held in Fig. 3, where the subjects are `ScenarioVariable`, and their role in the fluent
  is encoded in the relation to the `FluentClause`, e.g. `ref-object`. Variables allow preserving
  semantics of elements in clauses, interdependent scenarios, and variations. For example,
  in Fig. 3 the same `target-object` should be located at `pick-ws` before picking & at `place-ws`
  after placing.
- A `FluentClause` also links to a `TimeConstraint`, which can have more specific types denoting
  how the temporal term should be intepreted, e.g. `BeforeEventConstraint` & `AfterEventConstraint`
  in Fig. 3 for assertions that should hold relative to an event, i.e. time instant. Here, the
  example shows how the 2 "is held by" fluent clauses have different time constraints in the 2
  scenarios -- after picking & before placing.

#### Variation and Scene

## Representing Robotic AC as Knowledge Graphs

We choose to represent our metamodels and models for specifying BDD scenarios with the
[JSON-LD Schema](https://json-ld.org/). The JSON-LD representation of the BDD metamodel described
here can be found on our [metamodels](https://secorolab.github.io/metamodels/) page, and the
corresponding models on the [models](https://secorolab.github.io/models/) page.

For an overview of main JSON-LD keywords used in our models, please take a look at our
[modelling tutorial](https://github.com/comp-rob2b/modelling-tutorial#json-ld). More details on
this standard can be found on the [official online documentation](https://www.w3.org/TR/json-ld/).
For brevity, we use [compact IRIs](https://www.w3.org/TR/json-ld/#compact-iris) (i.e. use `:` to
separate prefix and suffix) when referring to metamodels concepts and relations below.

| Prefix | Namespace IRI |
|:-|:-|
| `agn` | `https://hbrs-sesame.github.io/metamodels/agent#` |
| `env` | `https://hbrs-sesame.github.io/metamodels/environment#` |
| `task` | `https://hbrs-sesame.github.io/metamodels/task#` |
| `evt` | `https://hbrs-sesame.github.io/metamodels/coordination/event#` |
| `bdd` | `https://hbrs-sesame.github.io/metamodels/acceptance-criteria/bdd#` |

### Agent

- `agn:Agent`: we adopt the definition from the IEEE Standard Ontologies for Robotics and
  Automation[^ieeestd1872] (cf. [prov:Agent](https://www.w3.org/TR/prov-o/#Agent)):

  Agent
    : Something or someone that can act on its own and produce changes in the world.

- `agn:of-agent`: composition relation with a `agn:Agent` instance.
- `agn:has-agent`: aggregation relation with a `agn:Agent` instance.

### Environment

- `env:Object`: Physical objects in the environment which an agent may interact with. Note that
  instances of `env:Object` are not limited to objects that the agent can move around like
  bottles or cups, but can also include typically stationary objects like tables or sofas.
- `env:Workspace`: Abstract space in which an agent may operate. Instances can be areas surrounding
  objects like tables or kitchen counters, or rooms in a flat. A `env:Workspace` instance may
  contain other instances, e.g. a living room can contain a workspace surrounding the coffee table.
- `env:has-object`, `env:has-workspace` represents aggregation relation to objects and workspaces.
- `env:of-object` represents composition relation to an object, e.g. a property of an object.

### Task

- `task:Variation`: possible variations of a scenario. A `task:Variation` instance can be
  associated with a `bdd:ScenarioTaskVariable` via the `bdd:of-variable` relation, in which case the
  instance denotes possible variations of the variable.
- `task:can-be`: represents an aggregation relation from a `task:Variation` instance to the
  possible entities of the variation.

### Coordination

- `evt:Event`: a time instant, conforms with
  [time:Instant](https://www.w3.org/TR/owl-time/#time:Instant) from the Time Ontology in OWL
  (cf. [prov:InstantaneousEvent](https://www.w3.org/TR/prov-o/#InstantaneousEvent)).
- `evt:has-event`: aggregation relation with a `evt:Event` instance.

### BDD Scenario Templates and Variants

- `bdd:Scenario`: represents a BDD scenario.
- `bdd:of-scenario`: composition relation to `bdd:Scenario`
- `bdd:GivenClause`, `bdd:WhenClause`, `bdd:ThenClause`: represents the three basic elements of a
  BDD formulation.
- `bdd:given`, `bdd:when`, `bdd:then`: composition relations that link a `bdd:Scenario` to
  _exactly one_ instance of `bdd:GivenClause`, `bdd:WhenClause`, `bdd:ThenClause`, correspondingly.
- `bdd:WhenEvent`: associates a `bdd:WhenClause` and a `evt:Event` instances using the
  `bdd:of-clause` and `evt:has-event` relations, respectively. Note that different interpretation
  exists that explain the semantics of the _When_ clause in BDD. In the current iteration of
  `bdd-dsl`, we choose to simply associate _When_ with `evt:Event` instances to denote the start
  of the behaviour being tested.
- `bdd:ScenarioVariant`: aggregate instances of `task:Variation` with relation `bdd:has-variation`;
  has a composition relation `bdd:of-scenario` with a `bdd:Scenario` instance.
- `bdd:UserStory`: aggregate instances `bdd:ScenarioVariant` with relation `bdd:has-criteria`.
- `bdd:ScenarioTaskVariable`: represents points of variation for a scenario.
- `bdd:of-variable`: composition relation to a `bdd:ScenarioTaskVariable`.
- `bdd:IsHeldPredicate`, `bdd:IsNearPredicate`: domain-specific predicates relevant to
  a pickup task.
- `bdd:TimeConstraint`: constraint on when the predicate of `bdd:FluentClause` must hold.
- `bdd:FluentClause`: represents a BDD clause as a
  [fluent](https://en.wikipedia.org/wiki/Fluent_(artificial_intelligence)), i.e. a condition
  evaluated at a point in time. A fluent clause has aggregation relations with one predicate,
  e.g. a `bdd:IsHeldPredicate` instance, and one `bdd:TimeConstraint` instance. The relations
  are `bdd:predicate` and `bdd:time-constraint`, respectively.
- `bdd:clause-of`: aggregation relation between `bdd:FluentClause` instances and instance of
  `bdd:GivenClause` and `bdd:ThenClause`. This relation allows for extending a BDD scenario template
  with any number of clauses.
- `bdd:ref-object`, `bdd:ref-workspace`, `bdd:ref-agent`: A `bdd:FluentClause` instance can
  associate with a `bdd:ScenarioTaskVariable` instance via these relations, which constrain the
  semantic of the variable in the context of the `bdd:FluentClause` instance.

## Constraints

### Structural

- A `bdd:Scenario` _contains_ exactly one `bdd:GivenClause`, `bdd:WhenClause`, and `bdd:ThenClause`.
  This is realized by the `bdd:given`, `bdd:when`, `bdd:then` relations for the respective clause types.
- `bdd:GivenClause`, `bdd:WhenClause`, and `bdd:ThenClause` cannot exist by themselves, i.e. they must be
  associated with exactly one `bdd:Scenario` via the `bdd:given`, `bdd:when`, `bdd:then` relations.
- A `bdd:FluentClause` can only connect by `bdd:clause-of` to `bdd:GivenClause` and `bdd:ThenClause`

## References

[^north2003bdd]: [D. North, "Behavior Modification: The evolution of behaviour-driven development", _Better Software_, 2006.](https://dannorth.net/introducing-bdd/)

[^nguyen2023rulebook]: M. Nguyen, N. Hochgeschwender, S. Wrede, "An analysis of behaviour-driven requirement specification for robotic competitions", [_5th International Workshop on Robotics Software Engineering (RoSE’23)_](https://rose-workshops.github.io/rose2023/), May 2023.

[^alferez2019]: M. Alferez, F. Pastore, M. Sabetzadeh, et al., "Bridging the Gap between Requirements Modeling and Behavior-Driven Development," _22nd MODELS_, 2019, doi: [10.1109/MODELS.2019.00008](https://doi.org/10.1109/MODELS.2019.00008).

[^ieeestd1872]: "IEEE Standard Ontologies for Robotics and Automation," in IEEE Std 1872-2015 , vol., no., pp.1-60, 10 April 2015, doi: [10.1109/IEEESTD.2015.7084073](https://doi.org/10.1109/IEEESTD.2015.7084073).

[^miller2002]: R. Miller and M. Shanahan, “Some Alternative Formulations of the Event Calculus,” in Comp. Logic: Logic Programming and Beyond, vol. 2408, 2002, pp. 452–490, doi: [10.1007/3-540-45632-5_17](https://doi.org/10.1007/3-540-45632-5_17).
