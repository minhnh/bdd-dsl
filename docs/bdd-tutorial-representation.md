# Tutorial: Modelling a Pickup application as RDF graphs

This tutorial will showcase how [concepts from our metamodels](bdd-concepts.md) can be used
to model acceptance criteria of a pickup task as Behaviour-Driven Development (BDD) scenarios,
as well as how variations of such scenarios can be introduced in the model. An example
is then presented to show how to transform this model into a
[Gherkin](https://cucumber.io/docs/gherkin/reference/) feature for integration with appropriate
BDD tool chains, e.g. `behave`[^behave] for the Python language.

## Table of content

<!-- mtoc-start -->

* [Example: BDD Scenario for a Robotic Pickup Task](#example-bdd-scenario-for-a-robotic-pickup-task)
* [Specifying BDD Acceptance Criteria for A Pickup Task](#specifying-bdd-acceptance-criteria-for-a-pickup-task)
  * [Specifying Scenario Templates](#specifying-scenario-templates)
  * [Specifying A Concrete Scenario Variant](#specifying-a-concrete-scenario-variant)
    * [Specifying Concrete Agents, Environment, and Coordination Models](#specifying-concrete-agents-environment-and-coordination-models)
    * [Specifying Variations](#specifying-variations)
* [Generating Gherkin Features from BDD Models](#generating-gherkin-features-from-bdd-models)
  * [Parsing JSON-LD models](#parsing-json-ld-models)
  * [Generating from Jinja Templates](#generating-from-jinja-templates)
  * [Additional tools](#additional-tools)
* [References](#references)

<!-- mtoc-end -->

## Example: BDD Scenario for a Robotic Pickup Task

Consider a simple robotic pickup task, where a robot must pick an object from a surface.
A typical BDD scenario for such a task, when realized in the Gherkin format, may look
something as follows:

```gherkin
Scenario: pickup scenario
  Given an object is located on the table
  When the robot starts picking
  Then the object is held by the robot
```

In robotics, even such a simple task can vary in many dimensions: the objects to be picked up,
the operational space in which the task take place, the robotic systems that carry out the task,
or the mechanisms available for verifying the different BDD clauses. While some mechanisms are
available in Gherkin to deal with variations of scenarios, applying existing BDD approaches
like Gherkin directly to robotic scenarios remains challenging. These challenges are discussed
in more details in our workshop paper [^nguyen2023rulebook]. The rest of this tutorial
will present the process of composing a scenario template for such a pickup task, as well as
how to introduce variations to the template for concrete scenarios. Finally, we will show
how Gherkin feature files similar to the snippet above can be generated from the
scenario variant model using our library.

## Specifying BDD Acceptance Criteria for A Pickup Task

| ![BDD Template and Variant Example](assets/img/bdd-example-pick-complete.svg) |
|:-:|
| Fig. 1: Partial example of a BDD scenario template and variant for the pickup task. |

As mentioned in the [description of our metamodels](bdd-concepts.md), our models are graphs
represented using the JSON-LD schema. Figure 1 shows how all the elements described there would
fit together to form a complete scenario specification for a pickup task. The motivation for
this template-variant design is discussed in more details on [the documentation of our metamodels](bdd-concepts.md).
Complete JSON-LD models for the scenario [template](https://secorolab.github.io/models/acceptance-criteria/bdd/templates/pickplace.tmpl.json)
and [variant](https://secorolab.github.io/models/acceptance-criteria/bdd/pickplace-secorolab-isaac.var.json),
along with their generated [visualization](assets/img/bdd_pickplace_generated_graph.svg) are publicly available
for download. The rest of this section will walk through the process of composing these models
from our metamodels.

### Specifying Scenario Templates

First, we define the skeleton of the BDD scenario for the pickup task: a `bdd:Scenario` having
composition relation to exactly one instance of `bdd:GivenClause`, `bdd:WhenClause`, and
`bdd:ThenClause`. A `bdd:Scenario` should also be associated with a `bhv:Behaviour` & a `task:Task`
for potential extension with behaviour & task models in the future.

```json
{ "@id": "tmpl:bhv-pickup", "@type": ["bhv:Behaviour", "bhv:Pick"] },
{ "@id": "tmpl:task-pickup", "@type": "task:Task" },
{ "@id": "pick-given", "@type": "bdd:Given" },
{ "@id": "pick-when", "@type": "bdd:When" },
{ "@id": "pick-then", "@type": "bdd:Then" },
{
    "@id": "scenario-pick", "@type": "bdd:Scenario",
    "of-behaviour": "tmpl:bhv-pickup",
    "of-task": "tmpl:task-pickup",
    "bdd:given": "pick-given",
    "bdd:when": "pick-when",
    "bdd:then": "pick-then"
}
```

Next, we define `bdd:ScenarioVariable` instances, which are points of variation of the
scenario template. Here, we may change the object, workspace, and agent in different variants of
the pickup scenario.

```json
{ "@id": "tmpl:var-target-obj", "@type": "bdd:ScenarioVariable" },
{ "@id": "tmpl:var-pick-ws", "@type": "bdd:ScenarioVariable" },
{ "@id": "tmpl:var-pick-robot", "@type": "bdd:ScenarioVariable" }
```

Having defined the variables, we can now create `bdd:FluentClause` instances and attach them to
`pick-given` and `pick-then` using the `bdd:clause-of` relation to denote their role in the
`scenario-pick` scenario. Here, we have made a choice to represent BDD clauses as
[fluents](https://en.wikipedia.org/wiki/Fluent_(artificial_intelligence)),
i.e. time-dependent predicates. The composable design allows us to make this choice without
limiting our metamodel to this single representation.

```json
{ "@id": "tmpl:evt-pick-end", "@type": "time:Event" },
{
   "@id": "tmpl:ftc-after-pick", "@type": ["time:TimeConstraint", "time:AfterEventConstraint"],
   "after-event": "tmpl:evt-pick-end"
},
{
   "@id": "tmpl:flc-obj-held-by-robot", "@type": ["bdd:FluentClause", "bdd:IsHeldPredicate"],
   "clause-of": "tmpl:pickup-then",
   "holds-at": "tmpl:ftc-after-pick",
   "ref-object": "tmpl:var-target-obj",
   "ref-agent": "tmpl:var-pick-robot"
}
```

In the example above, we define `fluent-obj-held-by-robot`, which asserts that the object is held
by the robot at the end of the picking behaviour. This `bdd:FluentClause` instance is a
composition linking to several elements in the template:

- Instances of `bdd:ScenarioVariable`, namely `var-target-obj` and `var-pick-robot`, which are
  the fluent's subjects.
- Instance `ftc-after-pick` of type `bdd:TimeConstraint` & `time:AfterEventConstraint`,
  which represents _when_ the fluent should hold true. The latter type denotes a more specific
  type of constraint -- the fluent should hold _after_ an event.

Additionally, the model at this point contains no assumption about how the fact that a robot is
holding an object can be verified. Further transformations and/or generations can be introduced
to produce concrete, executable implementations for verification.

The `bdd:ScenarioTemplate` then link to the scene & the scenario clauses:

```json
{ "@id": "scene:scn-pickplace", "@type": "bdd:Scene" },
{
    "@id": "tmpl:tmpl-pick", "@type": "bdd:ScenarioTemplate",
    "of-scenario": "tmpl:scenario-pick",
    "has-scene": "scene:scn-pickplace",
    "has-clause": [
        "tmpl:flc-located-at-pick-ws", "tmpl:when-pickplace",
        "tmpl:flc-move-safely", "tmpl:flc-located-at-place-ws"
   ]
}
```

### Specifying A Concrete Scenario Variant

The BDD scenario template defined above can now be extended with concrete variations, e.g. for
generating concrete Gherkin feature files as shown in
[the next section](#generating-gherkin-features-from-bdd-models).
This is done via linking the `bdd:ScenarioVariable` instances above to concrete instances of
objects, workspaces and agents. For example, consider the use case where we want to test the
pickup behaviour in the robotics lab at Bonn-Rhein-Sieg University using battery cells
sent from [AVL](https://www.avl.com) (An use case partner of the SESAME project), as well as
some objects readily available in the lab.

#### Specifying Concrete Agents, Environment, and Coordination Models

We first need concrete models of the objects, workspaces, and agents that we may test with,
as well as the scene collections to be used in the scenarios:

```json
{ "@id": "bottle", "@type": "env:Object" },
{ "@id": "ball", "@type": [ "bdd:Object", "avl:PouchCell" ] },
{ "@id": "cube", "@type": [ "bdd:Object", "avl:PrismaticCell" ] },
{ "@id": "dining-table-ws", "@type": "env:Workspace" },
{ "@id": "kinova1", "@type": [ "agn:Agent", "kinova:gen3-robots" ] },
{ "@id": "kinova2", "@type": [ "agn:Agent", "kinova:gen3-robots" ] },

{
    "@id": "scene:scn-pickplace-objects", "@type": "bdd:SceneHasObjects",
    "of-scene": "scene:scn-pickplace",
    "has-object": [
        "lab:obj-ball", "lab:obj-bottle", "lab:obj-cube"
    ]
},
```

#### Specifying Variations

A `task:TaskVariation` associates the scenario variables above with possible entities.
More specific types denote how the variation can be specified. For example, a table style
variation similar to the `Examples` keyword in Gherkin is available:

```json
{
    "@id": "var:var-table", "@type": [ "bdd:TaskVariation", "bdd:TableVariation" ],
    "of-task": "tmpl:task-pickplace",
    "variable-list": [ "tmpl:var-target-obj", "tmpl:var-pick-ws", "tmpl:var-place-ws" ],
    "rows": [
        [ "lab:obj-bottle", "lab:ws-table", "lab:ws-shelf" ],
        [ "lab:obj-ball", "lab:ws-table", "lab:ws-shelf" ],
        [ "lab:obj-ball", "lab:ws-table", "lab:ws-table" ]
    ]
}
```

One can also specify a list of possible entities for each variable, and parametrize the scenario
variations with the Cartesian product of these lists. We support this mechanism with the
`bdd:CartesianProductVariation` type:

```json
{
    "@id": "var:var-product-panda", "@type": [ "bdd:TaskVariation", "bdd:CartesianProductVariation" ],
    "of-task": "tmpl:task-pick",
    "variable-list": [
        "tmpl:var-target-obj", "tmpl:var-pick-ws", "tmpl:var-robot"
    ],
    "of-sets": [
        [ "lab:obj-bottle", "lab:obj-ball", "lab:obj-cube" ],
        [ "lab:ws-table", "lab:ws-shelf" ],
        [ "isaac-agn:panda" ]
    ]
}
```

We can now specify a `ScenarioVariant` as a composition of the `ScenarioTemplate` with the
`task:TaskVariation` instance & relevant scene elements. The `UserStory` is then a composite of
scenario variants.

```json
{
    "@id": "var:scr-var-panda-pickplace", "@type": "bdd:ScenarioVariant",
    "of-template": "tmpl:tmpl-pickplace",
    "has-scene": [
        "scene-lab:scn-pickplace-secorolab-objects",
        "scene-lab:scn-pickplace-secorolab-workspaces",
        "scene-isaac:scn-pickplace-isaac-panda"
    ],
    "has-variation": "var:var-product-panda"
},
{
    "@id": "var:us-obj-transport", "@type": "bdd:UserStory",
    "bdd:has-criteria": [ "var:scr-var-panda-pickplace" ]
}
```

## Generating Gherkin Features from BDD Models

After creating scenario variants and templates, we can transform these models into other formats
for use with existing tools. For example, from our BDD user stories, we can generate
Gherkin feature files which has wide support for test automation in most programming languages,
e.g. [behave](https://behave.readthedocs.io) library in Python. In the following example, we use
the [Jinja](https://jinja.palletsprojects.com/) template engine for the final text generation step.
The script [`examples/generate_bdd_specs.py`](https://github.com/minhnh/bdd-dsl/blob/-/examples/generate_bdd_specs.py)
in the `bdd-dsl` repository is used for loading our sample JSON-LD models
& generating Gherkin features.

### Parsing JSON-LD models

The JSON-LD graph of a `bdd:UserStory` can be loaded & processed using
[rdflib](https://rdflib.readthedocs.io/) & the `UserStoryLoader` class available in `bdd-dsl`:

```python
import rdflib
from bdd_dsl.models.user_story import UserStoryLoader

# dictionary mapping from URL to RDF graph format (not complete)
MODEL_URLS = {
    f"{URL_SECORO_M}/acceptance-criteria/bdd/templates/sorting.tmpl.json": "json-ld",
    f"{URL_SECORO_M}/acceptance-criteria/bdd/sorting-secorolab-isaac.var.json": "json-ld",
}
g = rdflib.Dataset()
for url, fmt in MODEL_URLS.items():
    g.parse(url, format=fmt)

# process the UserStory graph with exception handling for when remote models are not available
try:
    us_loader = UserStoryLoader(g)
except HTTPError as e:
    print(f"error loading models URL '{e.url}':\n{e.info()}\n{e}")
```

### Generating from Jinja Templates

The extracted and transformed JSON data can then be used to automatically render feature files using
[Jinja](https://jinja.palletsprojects.com/api/).

```jinja
{% raw %}
Feature: {{ data.name }}
...
{%- for scenario_data in data.criteria %}
{% for var_data in scenario_data.variations %}
  Scenario: {{ var_data.name }}
    {% for clause in var_data.clauses%}
    {{ clause|safe }}{% endfor %}
{% endfor %}
{%- endfor -%}
{% endraw %}
```

The complete & up-to-date version of this template
[is available online](https://secorolab.github.io/models/acceptance-criteria/bdd/jinja/feature.jinja)
for download. `bdd-dsl` also provides utilities to further process the transformed data shown above
before performing the final text transformation with Jinja. The code snippet below should generate
one feature file for each `bdd:UserStory` instance.

```python
from rdf_utils.naming import get_valid_filename
from bdd_dsl.utils.jinja import (
    load_template_from_url,
#    load_template_from_file,
    prepare_jinja2_template_data,
)

processed_bdd_data = prepare_jinja2_template_data(us_loader, g)

feature_template = load_template_from_url("http://my.url/to/feature.jinja")
# feature_template = load_template_from_file("path/to/feature.jinja")

for us_data in processed_bdd_data:
    feature_content = feature_template.render(data=us_data)
    feature_filename = f"{get_valid_filename(us_data["name"])}.feature"
    filepath = join("path/to/generated/dir", feature_filename)
    with open(filepath, mode="w", encoding="utf-8") as of:
        of.write(feature_content)
```

The generation result should produce be a valid Gherkin feature file like shown below:

```gherkin
Feature: var:us-pickplace
  ...

  Scenario: var:scr-var-panda-pickplace -- 1

    Given "['lab:obj-ball1']" is located at "lab:ws-table" before event "tmpl:evt-pick-start"
    When "isaac-agn:panda" picks "['lab:obj-ball1']" and places it at "['lab:ws-bin1']"
    Then "isaac-agn:panda" moves safely from "tmpl:evt-pick-start" until "tmpl:evt-place-end"
    Then "['lab:obj-ball1']" is located at "['lab:ws-bin1']" after event "tmpl:evt-place-end"
    ...
```

The generated feature files can then be used with existing BDD frameworks, e.g. `behave`[^behave],
for test automation, which we go over in
[the tutorial about test execution](bdd-tutorial-execution.md)

### Additional tools

Internally, we use [SPARQL queries](https://rdflib.readthedocs.io/en/stable/intro_to_sparql.html)
& `rdflib` methods to extract relevant info from a `rdflib.Graph`. We also check structural
constraints, e.g. cardinality & types, using [SHACL](https://www.w3.org/TR/shacl/).

## References

[^nguyen2023rulebook]: M. Nguyen, N. Hochgeschwender, S. Wrede, "An analysis of behaviour-driven requirement specification for robotic competitions", [_5th International Workshop on Robotics Software Engineering (RoSE’23)_](https://rose-workshops.github.io/rose2023/), May 2023.

[^behave]: [behave](https://behave.readthedocs.io) - library for executing Gherkin features in Python
