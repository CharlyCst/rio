# Run-in-Order

This repository contains the source code of the Rio (Run-in-Order) runtime and
benchmarks for both Rio and StarPU measuring their ability to execute
fine-grained Sequential Task Flow (STF) programs.

The repository is organized as follow:

- `rio`: A Rust project containing two crates:
  - `rio`: The source code of the Rio runtime.
  - `experiments`: The source code of experiments used for benchmarking Rio.
- `starpu`: The source of experiments usef for benchmarking StarPU.
- `bare_metal`: A single threaded C implementation of the Rio and StarPU
  experiments, used for reference.
- `scripts`: Python scripts to automate the benchmarks.
- `bench`: A tool for collecting statistics about programs using performance
  counters, used by the python scripts.

## Requirements

Compiling and running the benchmarks require the following dependencies (in
parenthesis are the versions we used):

- A C compiler (gcc 10.2.0)
- A Rust compiler (rustc 1.51)
- StarPU (1.3.8)
- hwloc (2.4.1)
- python (3.9.6)

## Usage

The experiments are run using the benchmark scrips
`scripts/benchmark_efficiency.py` and `scripts/benchmark_workers.py`. Both
script produce a json file that can be used to plot different figures using the
`scripts/plot_efficiency.py` and `scripts/plot_workers.py` scripts. All scripts
accept a `-h` or `--help` argument that can be used to learn about
configuration options.

To plot the efficiency decomposition, the following commands can be used:

```sh
python scrips/benchmark_efficiency.py -f efficiency.json --timeout 100 --average-on 3 --nb-threads 24 --experiment counter_deps --verbose
python scripts/plot_efficiency.py -f efficiency.json
```

And to plot the execution time for different number of workers with a miximum of 64 (2⁶) workers:

```sh
python scripts/benchmark_workers.py -f workers.json --timeout 100 --average-on 3 --nb-threads 6 --size 22 --task-size 20
python scripts/plot_workers.py -f workers.json
```

