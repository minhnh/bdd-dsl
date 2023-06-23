# Tutorial: Generating Gherkin features for a simple pickup task

This tutorial showcases how [concepts from our metamodels](bdd-concepts.md) can be used to model
a template of a simple pickup scenario in the Behaviour-Driven Development (BDD) paradigm.
Variations of both the scenario definition and acceptance criteria can then be introduced to this
template for tailoring to different variants of the pickup task, e.g. for different robotic
competitions. Finally, these scenario variants can then be used to generate
[Gherkin](https://cucumber.io/docs/gherkin/reference/) feature files for integration with
appropriate BDD toolchains, e.g. [`behave`](https://behave.readthedocs.io) for the Python language.

## Specifying the pickup BDD template

### BDD clauses

### Scenario variables

## Specifying concrete scenario variant

### Variation of objects, workspaces, agents

### Variation of criteria

## Generating Gherkin Feature files

## Discussion

Here, the idea of defining common "templates" for BDD scenarios of the same behaviour is inspired
by the work by Alferez et al.[^alferez2019], in which the behaviours are different operations on
data structures in a database. Variations of robotic scenarios, even for the simple pickup task
currently in consideration, can be vastly more complex. This motivates the design of our metamodels
to accommodate such complexity.
TODO: rephrase end

## References

[^alferez2019]: M. Alferez, F. Pastore, M. Sabetzadeh, et al., "Bridging the Gap between Requirements Modeling and Behavior-Driven Development," _22nd MODELS_, 2019, doi: [10.1109/MODELS.2019.00008](https://doi.org/10.1109/MODELS.2019.00008).
