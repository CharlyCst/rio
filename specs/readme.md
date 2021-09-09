# Formal Specification

This folder contains a formal specification of the Sequential Task Flow (STF)
programming model `STFSpec.tla` and of the Run-In-Order execution model
`RunInOrder.tla`.

## Requirements

The only requirements to check the model is to have a version of java
installed. The code was tested with java 11 but might work with other versions.

## Model Checking

The two specification come with models (`STFModelChecker.tla` &
`RunInOrderModelChecker.tla`) that give concrete values to the `Workers`,
`Dara`, `Tasks`, `ControlFlow` and `Mapping` variables and can be use to verify
that the properties of the specification are ensured for all possible
executions given these concrete values.

The models can be check with the TLC model checker, distributed with the TLA
toolbox. For ease of use the toolbox can be downloaded using the
`download_tla.sh` script:

```sh
./download_tla.sh
```

Once downloaded, the STF and Run-In-Order models can be checked using the
corresponding script:

```sh
# Check the STF model
./check_stf.sh

# Check the Run-In-Order model
./check_rio.sh
```

## Properties

Two properties are checked for the STF model: Termination and Data-Race
Freedom. If any of those properties is violated the TLC model checker will
raise an error. There is no explicit property for sequential consistency
because the sequential consistency is encoded in the `Next` state transition: a
task can not be executed if some of the dependencies have not yet been
executed.

The only property checked for the Run-In-Order model is that it implements the
STF specification. This enforces that both Termination and Data-Race Freedom
are valid for any possible execution, and that the execution order is one of
the orders accepter by the STF model (i.e. it respects sequential consistency).

## Modifying the models

The concrete values of the models are defined in `STFModelChecker.tla` and
`RunInOrderModelChecker.tla`. To check the specifications with different values
only those files need to be edited. `STFModelChecker.tla` configures the model
for checking the STF specification while `RunInOrderModelChecker.tla`
configures the model for the Run-In-Order specification.

