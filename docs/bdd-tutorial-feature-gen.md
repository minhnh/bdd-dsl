# Tutorial: Modelling and Generating Gherkin features for A Simple Pickup task

This tutorial will first showcase how [concepts from our metamodels](bdd-concepts.md) can be used
to model acceptance criteria of a simple pickup task as Behaviour-Driven Development (BDD)
scenarios, as well as how variations of such scenarios can be introduced in the model. An example
is then presented to show how to transform this model into a
[Gherkin](https://cucumber.io/docs/gherkin/reference/) feature for integration with appropriate
BDD toolchains, e.g. [`behave`](https://behave.readthedocs.io) for the Python language.

## Specifying BDD Acceptance Criteria for A Pickup Task

| ![BDD Template and Variant Example](assests/../assets/img/bdd-example-pickup.svg) |
|:-:|
| Figure 1: Partial example of a BDD scenario template and variant for the pickup task. |

As mentioned in the [description of our metamodels](bdd-concepts.md), our models are graphs
represented using the JSON-LD schema. Figure 1 shows part of such a graph, which consists of a BDD
scenario template and corresponding variants for a simple pickup task. The rest of this section will
walk through the process of creating this example. The motivation of the metamodel design and
detailed descriptions of their concepts and relations can be found on the
[documentation for the relevant metamodels](bdd-concepts.md). Complete JSON for the BDD scenario
[template](https://hbrs-sesame.github.io/models/acceptance-criteria/bdd/templates/pickup.json)
and [variant](https://hbrs-sesame.github.io/models/acceptance-criteria/bdd/pickup-variants.json)
are also available online.

### Specifying Scenario Templates

First, we define the skeleton of the BDD scenario for the pickup task: a `bdd:Scenario` having
composition relation to exactly one instance of `bdd:GivenClause`, `bdd:WhenClause`, and
`bdd:ThenClause`.

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

Next, we define `bdd:ScenarioVariable` instances, which are points of variation of the
scenario template. Here, we may change the object, workspace, and agent in different variants of
the pickup scenario.

```json
{
    "@id": "pick-object", "@type": "bdd:ScenarioVariable",
    "bdd:of-scenario": [ "scenario-pick" ]
},
{
    "@id": "pick-workspace", "@type": "bdd:ScenarioVariable",
    "bdd:of-scenario": [ "scenario-pick" ]
},
{
    "@id": "pick-robot", "@type": "bdd:ScenarioVariable",
    "bdd:of-scenario": [ "scenario-pick" ]
}
```

Having defined the variables, we can now create `bdd:FluentClause` instances and attach them to
`pick-given` and `pick-then` to extend `scenario-pick` with more concrete clauses.
In the example below, we define `fluent-obj-held-by-robot`, which asserts that the object is held
by the robot at the end of the picking behaviour. In the model, this is done via association with
predicate `pred-obj-held-by-robot` and time constraint `after-pick`. `fluent-obj-held-by-robot`
refers to variables `pick-object` and `pick-robot` using the `bdd:ref-object` and `bdd:ref-agent`,
respectively, which implies the domain-specific constraint that `pred-obj-held-by-robot` requires
association with an object and an agent.

```json
{ "@id": "pred-obj-held-by-robot", "@type": "bdd:IsHeldPredicate" },
{ "@id": "after-pick", "@type": "bdd:TimeConstraint" },
{
    "@id": "fluent-obj-held-by-robot",
    "@type": "bdd:FluentClause",
    "bdd:clause-of": [ "pick-then" ],
    "bdd:predicate": "pred-obj-held-by-robot",
    "bdd:time-constraint": "after-pick",
    "bdd:ref-object": "pick-object",
    "bdd:ref-agent": "pick-robot"
}
```

### Specifying A Concrete Scenario Variant

The BDD scenario template defined above can now be extended with concrete variations, e.g. for
generating concrete Gherkin feature files as shown in
[the next section](#generating-gherkin-features-from-bdd-models). For example, we would like
to test the pickup behaviour in the robotics lab at Bonn-Rhein-Sieg University using battery cells
sent from [AVL](https://www.avl.com) (An use case partner of the SESAME project), as well as some
objects readily available in the lab.

#### Specifying Concrete Agents, Environment, and Coordination Models

We first need concrete models of the objects, workspaces, and agents that we may test with:

```json
{ "@id": "bottle", "@type": "env:Object" },
{ "@id": "pouch1", "@type": [ "bdd:Object", "avl:PouchCell" ] },
{ "@id": "cylindrical1", "@type": [ "bdd:Object", "avl:PrismaticCell" ] },
{ "@id": "dining-table-ws", "@type": "env:Workspace" },
{ "@id": "kinova1", "@type": [ "agn:Agent", "kinova:gen3-robots" ] },
{ "@id": "kinova2", "@type": [ "agn:Agent", "kinova:gen3-robots" ] }
```

We also need a coordination model which defines the event that denotes the start of the pickup
behaviour, which we can associate with `pickup-when`.

```json
{ "@id": "pickup-start", "@type": "evt:Event" }
```

#### Specifying Variations

Using the `task:Variation` concept, we can associate the `bdd:ScenarioVariable` instances above
with possible entities via the `task:can-be` relation:

```json
{
    "@id": "obj-variation", "@type": "task:Variation",
    "bdd:of-variable": "pick-object",
    "task:can-be": [ "bottle", "pouch1", "cylindrical1" ]
},
{
    "@id": "ws-variation", "@type": "task:Variation",
    "bdd:of-variable": "pick-workspace",
    "task:can-be": [ "dining-table-ws" ]
},
{
    "@id": "robot-variation", "@type": "task:Variation",
    "bdd:of-variable": "pick-robot",
    "task:can-be": [ "kinova1", "kinova2" ]
}
```

The `pick-when` can be associated with the concrete event `pickup-start`.

```json
{
    "@id": "pick-when-event", "@type": "bdd:WhenEvent",
    "bdd:of-clause": "pick-when", "evt:has-event": "pickup-start"
}
```

We can now define variant `scenario-pick-brsu` as a composition of the `task:Variation`
instances, and user story `us-obj-transport` as a composition of scenario variants, one of which is
`scenario-pick-brsu`.

```json
{
    "@id": "scenario-pick-brsu", "@type": "bdd:ScenarioVariant",
    "of-scenario": "scenario-pick",
    "task:has-variation": [
        "obj-variation", "ws-variation", "robot-variation"
    ]
},

{
    "@id": "us-obj-transport", "@type": "bdd:UserStory",
    "bdd:has-criteria": [ "scenario-pick-brsu" ]
}
```

`bdd-dsl` provide the `load_metamodels` utility method for initializing a
[`rdflib.Graph`](https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.html#graph) object with
our [metamodels](https://github.com/hbrs-sesame/metamodels).
Models can then be loaded to the graph with the
[`parse`](https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.html#rdflib.graph.Graph.parse) method:

```python
from bdd_dsl.utils.json import load_metamodels

g = load_metamodels()
g.parse("path/to/model.json", format="json-ld")
```

## Generating Gherkin Features from BDD Models

After creating scenario variants and templates, we can transform these models into other formats
for use with existing tools. For example, from our BDD user stories, we can generate
[Gherkin feature files](https://cucumber.io/docs/gherkin/reference/) which has wide support for
test automation in most programming languages, e.g. [behave](https://behave.readthedocs.io) library
in Python. In the following example, we use the [Jinja](https://jinja.palletsprojects.com/)
template engine for the final text generation step.

### Extracting Relevant Information and Transforming BDD Models

Extracting the relevant information from a `rdflib.Graph` object can be done with
[SPARQL queries](https://rdflib.readthedocs.io/en/stable/intro_to_sparql.html).
Additionally, [JSON-LD Framing](https://www.w3.org/TR/json-ld-framing/) can force a specific
tree layout to the graph structure of the model, which can be easier to generate to text targets,
as will be shown.

`bdd-dsl` provides several utilities for querying and framing models composed using our metamodels.
The following example shows how BDD user stories akin to the example above can be transformed using
the library's Python API:

```python
from pyld import jsonld
from bdd_dsl.models.queries import BDD_QUERY
from bdd_dsl.models.frames import BDD_FRAME
from bdd_dsl.utils.json import query_graph, process_bdd_us_from_graph

bdd_result = query_graph(g, BDD_QUERY)
model_framed = jsonld.frame(bdd_result, BDD_FRAME)

# alternatively, there's also an utility function that executes the above
# as well as doing some further cleanup of the result
cleaned_bdd_data = process_bdd_us_from_graph(g)
```

The code snippet above should produce the following JSON when run on the above model:

```json
"data": [{
  "name": "us-obj-transport",
  "criteria": [{
    "name": "scenario-pick-brsu",
    "scenario": {
      "name": "scenario-pick",
      "then": {
        "clauses": {
            "name": "fluent-obj-held-by-robot",
            "agents": { "name": "pick-robot" },
            "objects": {"name": "pick-object"}
        },
      },
      "when": {
        "name": "pick-when",
        "trans:has-event": { "name": "pickup-start" }
      }
    },
    "variations": [
      {
        "name": "obj-variation",
        "entities": [
          {"name": "bottle"}, {"name": "pouch1"}, {"name": "cylindrical1"}
        ],
        "trans:of-variable": {"name": "pick-object"}
      },
      ...
    ]
  }]
}]
```

### Generating from Jinja Templates

The extracted and transformed JSON data can be used to automatically render feature files using
[Jinja](https://jinja.palletsprojects.com/api/) with the template below:

```jinja
{% raw %}
Feature: {{ data.name }}
{% for scenario_data in data.criteria %}
  Scenario Outline: {{ scenario_data.name }}
    {% for clause in scenario_data.given_clauses %}
    {{ clause|safe }}{% endfor %}

    When "{{ scenario_data.when_event }}"
    {% for clause in scenario_data.then_clauses %}
    {{ clause|safe }}{% endfor %}

    Examples:
    |{% for var_name in scenario_data.variables %} {{ var_name }} |{% endfor %}
    {% for entity_data in scenario_data.entities %}|{%
      for entity_name in entity_data %} {{ entity_name }} |{% endfor %}
    {% endfor %}
{% endfor %}
{% endraw %}
```

The up-to-date version of this template
[is available online](https://hbrs-sesame.github.io/models/acceptance-criteria/bdd/feature.jinja)
for download.

> TODO: include video, maybe also in top level README

## Conclusions
