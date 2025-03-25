# Tutorial: Modelling and Executing BDD Tests for a Pickup Task

> [!NOTE]
> This tutorial is still WIP. Modelling steps & updated videos will be added in the future.

This tutorial will walk through how to introduce models, in addition to the ones for _representing_
BDD scenarios (see [corresponding tutorial](bdd-tutorial-representation.md)), to specify test
test execution. These "execution models" can be used by the test orchestration framework,
e.g. `behave`[^behave], to parametrize scenario executions.

## Videos

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
