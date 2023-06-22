# Model-Based BDD for Robotics

This is the landing page for the associated tooling to support the specification and
execution of acceptance tests for robotic applications using the
Behaviour-Driven Development (BDD)[^north2003bdd] methodology.

To this end, we employ the [JSON-LD schema](https://json-ld.org/) to define the BDD concepts as
described in the original article[^north2003bdd], concepts necessary for specifying robotic scenarios,
and the relations needed to compose them into concrete test scenarios. These concepts and relations
are based on our analysis of rulebooks from several robotic benchmarks and competitions, the results
of which is reported in [^nguyen2023rulebook].

## Content

1. [Concepts and relations for specifying robotic scenarios](bdd-concepts.md)
2. [Tutorial: Generating Gherkin features for a simple pickup task](bdd-tutorial-feature-gen.md)

## References

[^north2003bdd]: [D. North, "Behavior Modification: The evolution of behaviour-driven development", _Better Software_, 2006.](https://dannorth.net/introducing-bdd/)

[^nguyen2023rulebook]: M. Nguyen, N. Hochgeschwender, S. Wrede, "An analysis of behaviour-driven requirement specification for robotic competitions", [_5th International Workshop on Robotics Software Engineering (RoSE’23)_](https://rose-workshops.github.io/rose2023/), May 2023.

## Acknowledgement

This work is partly funded by the [SESAME H2020 project](https://www.sesame-project.org/),
under grant agreement No 101017258.
