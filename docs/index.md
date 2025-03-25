# Model-Based BDD for Robotics

This is the landing page for the associated tooling to support the specification and
execution of acceptance tests for robotic applications using the
Behaviour-Driven Development (BDD)[^north2003bdd] methodology.
BDD complements the ExSce by introducing the scenario view on the robotic system using
a `Given-When-Then` cascade. The "Given" clause captures the pre-conditions including
the robotic system and its state, the "When" clause describes an event that the system
should react to, while the "Then" clause specifies the desired or expected behaviour.
However, applying traditional BDD approaches to MRS applications can be challenging
due to the complex interplay of multiple variability dimensions and domains involved in
describing robotic scenarios. To address these challenges more effectively, `bdd-dsl`
introduces a metamodel for defining composable BDD scenario templates that can be
customized to specific robotic use cases. The metamodel design takes inspiration from
a similar approach used for managing data structures [^alferez2019] and is further supported
by an analysis of competition rulebooks to identify the variability dimensions that may arise
when evaluating robotic scenarios [^nguyen2023rulebook].

This library is one of the tools developed for the
[Executable Scenario Workbench](https://sesame-project.github.io/exsce/)

## Content

Details on the design of the metamodel and a tutorial on how to compose and transform
BDD models can be found on the following pages:

1. [Concepts and relations for specifying robotic scenarios](bdd-concepts.md)
2. [Tutorial: Modelling a pickup task as JSON-LD graphs and generating Gherkin features](bdd-tutorial-representation.md)
3. [Tutorial: Modelling & executing BDD tests for a pickup task](bdd-tutorial-execution.md) (WIP)

## Acknowledgement

This work is partly funded by the [SESAME H2020 project](https://www.sesame-project.org/),
under grant agreement No 101017258.

## References

[^north2003bdd]: D. North, "Behavior Modification: The evolution of behaviour-driven development",
    _Better Software_, 2006 ([Original blog post](https://dannorth.net/introducing-bdd/)).

[^alferez2019]: M. Alferez, F. Pastore, M. Sabetzadeh, et al., "Bridging the Gap between
    Requirements Modeling and Behavior-Driven Development," _22nd MODELS_, 2019,
    doi: [10.1109/MODELS.2019.00008](https://doi.org/10.1109/MODELS.2019.00008).

[^nguyen2023rulebook]: M. Nguyen, N. Hochgeschwender, S. Wrede, "An analysis of behaviour-driven
    requirement specification for robotic competitions",
    [_5th International Workshop on Robotics Software Engineering (RoSE’23)_](https://rose-workshops.github.io/rose2023/),
    May 2023.
