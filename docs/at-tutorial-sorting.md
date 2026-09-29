# Acceptance Testing Tutorial 3: Set Quantifiers and Sorting

> Set-valued scenario execution is work in progress. This tutorial covers
> specification and validation only. The executable tutorial runs one
> pick-and-place scenario.

This tutorial extends [Tutorial 1](at-tutorial-scenarios.md) from one object to a set of
objects while reusing the same scene. The complete model is
[sorting.bdd](https://github.com/minhnh/robbdd_tutorials/blob/main/robbdd_tutorials/models/pick_place/common/sorting.bdd).

## Declare set-valued variables

~~~text
var robot
set var target-objects
var pick-workspace
set var place-workspaces
~~~

The singular variables identify the acting robot and source workspace. The set
variables describe the objects and their allowed destinations.

## Quantify the criteria

**for all** applies the nested Given–When–Then clauses to every selected
object:

~~~text
for all ( var object in <target-objects> ) {
    Given:
        object-at-pick: holds(
            <object> is located at <pick-workspace>,
            before <E_PICK_START>
        )

    When:
        Behaviour (ns=tutorial) sort-object-behavior {
            duration: from <E_PICK_START> until <E_PLACE_END>
            <robot> picks <object> and places at <place-workspaces>
        }

    Then:
        object-at-place: holds(
            <object> is located at <place-workspaces>,
            after <E_PLACE_END>
        )
}
~~~

An additional fluent describes the aggregate outcome:

~~~text
Then:
    objects-sorted: holds(
        <target-objects> are sorted into <place-workspaces>,
        after <E_PLACE_END>
    )
~~~

## Bind set variations

~~~text
variation:
    set var <sorting-template.target-objects>:
        select 1 combinations from <pickplace_objects>
    var <sorting-template.pick-workspace>: {
        <pickplace_workspaces.table-workspace>
    }
    set var <sorting-template.place-workspaces>: {
        { <pickplace_workspaces.container-workspace> }
    }
    var <sorting-template.robot>: agn set <pickplace_agents>
~~~

The one-object selection keeps this model valid against the small tutorial
scene. Add more objects before selecting larger combinations.

## Validate the specification

~~~bash
textx check sorting.bdd
~~~

The command must report **OK**. Do not add this model to a graph manifest,
launch file, or integration test until set-valued scenario execution is
supported.
