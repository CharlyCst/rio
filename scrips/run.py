""" Run

A script to automatically run benchmarks and record stats about execution as
well as details about the current environment.

To learn more about the script usage, run:

```sh
python3 run.py --help
```
"""
import subprocess
import json
import argparse
import time
import sys
from datetime import datetime
from os import path, getcwd, chdir, environ
from typing import List, Optional, Dict

t = time.time()

# Runtimes
STARPU = "StarPU"
REACTRT = "ReactRT"
BARE_METAL = "Bare Metal"

# Paths
root = getcwd()
benchmark_path = "/tmp"
bench_path = path.join(root, "bench")
starpu_path = path.join(root, "starpu")
reactrt_path = path.join(root, "rust")
bare_metal_path = path.join(root, "bare_metal")

# An experiment consists in a list of runtime-target couples
experiment_targets = {
    "counter": [
        {"runtime": STARPU, "target": "counter"},
        {"runtime": REACTRT, "target": "counter"},
    ],
}


# —————————————————————————————————— Flags ——————————————————————————————————— #
# The flags passed down to child sub-processes.
# Placeholders are denoted with '%x' where x can be:
#  - 'n' for number of threads
#  - 't' for task size
#  - 'p' for problem size
# ———————————————————————————————————————————————————————————————————————————— #

# hwloc-bind will wrap bench to ensure data locality
hwloc_bind_flags = ["core:0:%n"]

# Flags passed to Bench
reactrt_flags = ["-j", "--args", "%p %t -n %n"]
starpu_flags = ["-j", "--args", "%p %t"]
bare_metal_flags = ["-j", "--args", "%p %t"]

# ——————————————————————————————————— CLI ———————————————————————————————————— #

parser = argparse.ArgumentParser(
    description="Run the suite of runtime benchmarks",
)
parser.add_argument(
    "-v",
    "--verbose",
    help="print progress",
    action="store_true",
)
parser.add_argument(
    "-e",
    "--experiments",
    help="the experiments to run, a space-separated list can be used",
    nargs="*",
)
parser.add_argument(
    "--list-experiments",
    help="list all the available experiments and exit",
    action="store_true",
)
parser.add_argument(
    "-f",
    "--file",
    help="the output file (default to stdout)",
)
parser.add_argument(
    "-t",
    "--timeout",
    metavar="T",
    help="timeout (in seconds) for benchmarked programs",
    type=int,
    default=100,
)
parser.add_argument(
    "--size",
    help="problem size, in power of 2 (default to 9)",
    type=int,
    default=9,
    dest="problem_size",
)
parser.add_argument(
    "--task-size",
    metavar="TASK_SIZE",
    help="the maximum task size, in power of 2 (default to 8)",
    type=int,
    default=8,
    dest="maximum_task_size",
)
parser.add_argument(
    "-n",
    "--nb-threads",
    metavar="N",
    help="the number of threads to use (default to 2)",
    type=int,
    default=2,
    dest="nb_threads",
)
parser.add_argument(
    "--average-on",
    metavar="N",
    help="average the results on N runs (default to 1)",
    type=int,
    default=1,
    dest="average_on",
)

args = parser.parse_args()


# —————————————————————————————————— Utils ——————————————————————————————————— #


def log(text: str):
    """Print a message, if verbose mode is activated"""
    if args.verbose:
        print(text)


def run(cmd_args: List[str], with_timeout: bool = True):
    """A small wrapper around subprocess.run, will check for errors & timeout"""
    timeout = args.timeout if with_timeout else None
    result = subprocess.run(cmd_args, timeout=timeout, stdout=subprocess.DEVNULL)
    result.check_returncode()


def run_benchmark(cmd_args: List[str], env: Dict[str, str]) -> Optional[Dict[str, int]]:
    """A wrapper around subprocess.run for benchmark use.
    The output of the subprocess will be captured, parsed as json and returned.
    In case of timeout, None is returned instead.
    """
    handle = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, env=env)
    t = time.time()
    while True:
        ret = handle.poll()
        if ret is None:
            if time.time() - t > args.timeout:
                # kill the process
                handle.terminate()
                handle.wait()
                return None
            else:
                # Wait some more time
                time.sleep(1)
        else:
            if not ret == 0 or handle.stdout is None:
                # Something bad happened
                raise Exception(f"Process exited with non zero code: {cmd_args}")
            else:
                # Return the benchmark results
                return json.loads(handle.stdout.read())


def get_last_commit_hash():
    result = subprocess.run(
        ["git", "log", "-n1", "--format=format:%H"],
        stdout=subprocess.PIPE,
    )
    result.check_returncode()
    return result.stdout.decode()


def prepare_flags(flags: List[str], problem_size: int, task_size: int) -> List[str]:
    """Substiture all placeholders in the given flags."""
    return [
        flag.replace("%n", str(args.nb_threads))
        .replace("%t", str(task_size))
        .replace("%p", str(problem_size))
        for flag in flags
    ]


# ——————————————————————————————— Build Utils ———————————————————————————————— #


REACTRT_IS_BUILT = False


def build_starpu_target(target: str) -> str:
    """Build a StarPU target and return the name of produced artefact"""
    chdir(starpu_path)
    run(["make", "-B", target], with_timeout=False)
    dlib = "starpu_" + target
    run(["cp", target, path.join(benchmark_path, dlib)])
    return dlib


def build_bare_metal_target(target: str) -> str:
    """Build a Bare Metal target and return the name of the produced artefact"""
    chdir(bare_metal_path)
    run(["make", "-B", target], with_timeout=False)
    dlib = "bare_metal_" + target
    run(["cp", target, path.join(benchmark_path, dlib)])
    return dlib


def build_reactrt_target(target: str) -> str:
    """Build a ReactRT target and return the name the produced artefact"""
    chdir(reactrt_path)
    global REACTRT_IS_BUILT
    if not REACTRT_IS_BUILT:
        run(
            ["cargo", "build", "--package", "experiments", "--release"],
            with_timeout=False,
        )
        REACTRT_IS_BUILT = True
    dlib = "reactrt_" + target
    reacrt_target_path = path.join("target", "release")
    run(["cp", path.join(reacrt_target_path, target), path.join(benchmark_path, dlib)])
    return dlib


# —————————————————————————— Analyze CLI arguments ——————————————————————————— #


# Print & exit if --list-experiments
if args.list_experiments:
    experiments = experiment_targets.keys()
    print("Available experiments:")
    for exp in experiments:
        print(f"  - {exp}")
    sys.exit()

# Exit if no experiments are selected
if args.experiments is None or len(args.experiments) == 0:
    print("No experiment selected.\n")
    print(
        "You can see the list of available experiments with the '--list-experiments'\nflag and pass a list of experiments with the '--experiments' or '-e' flags\nfollowed by a space-separated list of experiments.\n"
    )
    print("Use '--help' for more details.\n")
    sys.exit(1)

# Exit if one of the experiment target does not exist
for exp in args.experiments:
    if not exp in experiment_targets:
        print(f"Unknown experiment: '{exp}'\n")
        print("Use '--list-experiments' to see available experiments.\n")
        sys.exit(1)

# Exit if average_on is not >= 1
if not args.average_on >= 1:
    print(f"Invalid number of runs: got '{args.average_on}'")
    sys.exit(1)

# Print execution summary
print("Experiment setting:\n")
print(f"  - problem size:\t{2 ** args.problem_size}")
print(f"  - maximum task size:\t{2 ** args.maximum_task_size}")
print(f"  - number of threads:\t{args.nb_threads}")
print(f"  - timeout:\t\t{args.timeout}s")
print(f"  - experiments:\t{' '.join(args.experiments)}")
print(f"  - averaged on:\t{args.average_on} run{'s' if args.average_on>1 else ''}")
print()

# ——————————————————————————————— Build Phase ———————————————————————————————— #


log("Get last commit hash...")
hash = get_last_commit_hash()

log("Checking `hwloc-bind` availability...")
run(["hwloc-bind", "--version"])

log("Loading data file if it exists...")
experiments = {}
todo_experiments = []
try:
    if args.file is not None:
        with open(args.file, "r") as file:
            experiments = json.load(file)
except OSError:
    # The file does not yet exists, this is fine
    pass

log("Building bench...")
chdir(bench_path)
run(["cargo", "install", "--path", "."], with_timeout=False)

log("\nBuilding targets...")
run(["cargo", "build", "--release", "--examples"], with_timeout=False)
for target_name in args.experiments:
    runtimes = experiment_targets[target_name]
    starpu_n_workers = max(args.nb_threads - 1, 1)
    env_vars = {"STARPU_NCPU": f"{starpu_n_workers}", "STARPU_WORKERS_GETBIND": "1"}
    experiment = {
        "problem_size": 2 ** args.problem_size,
        "nb_threads": args.nb_threads,
        "experiment": target_name,
        "commit": hash,
        "env": env_vars,
        "hwloc_bind_flags": hwloc_bind_flags,
        "date": datetime.now().isoformat(),
        "n_runs": args.average_on,
        # title
    }
    experiment_runtimes = {}
    for runtime_spec in runtimes:
        dlib = None
        flags = None
        # Read experiment specification
        runtime = runtime_spec["runtime"]
        target = runtime_spec["target"]
        bench_flags = []
        if "bench_flags" in runtime_spec:
            bench_flags = runtime_spec["bench_flags"]
        runtime_name = runtime
        if "alias" in runtime_spec:
            runtime_name = runtime_spec["alias"]
        env = {}
        if "env" in runtime_spec:
            env = runtime_spec["env"]

        # Build target
        if runtime == STARPU:
            dlib = build_starpu_target(target)
            flags = bench_flags + starpu_flags
        elif runtime == REACTRT:
            dlib = build_reactrt_target(target)
            flags = bench_flags + reactrt_flags
        elif runtime == BARE_METAL:
            # Skip if we run a multi-threaded benchmark
            if args.nb_threads > 1:
                continue
            dlib = build_bare_metal_target(target)
            flags = bench_flags + bare_metal_flags
        else:
            print(f"Error: unknown runtime '{runtime}'")
        experiment_runtimes[runtime_name] = {
            "dlib": dlib,
            "flags": flags,
            "runtime": runtime,
            "env": env,
        }
    experiment["runtimes"] = experiment_runtimes
    experiment_id = f"{target_name}_{2 ** args.problem_size}_{args.nb_threads}"
    experiments[experiment_id] = experiment
    todo_experiments.append(experiment_id)


# ———————————————————————————————— Benchmark ————————————————————————————————— #


chdir(benchmark_path)
problem_size = 2 ** args.problem_size
n_runs = args.average_on
for experiment_id in todo_experiments:
    experiment = experiments[experiment_id]
    env_vars = experiment["env"]
    hwloc_bind_flags = experiment["hwloc_bind_flags"]
    env = dict(environ, **env_vars)
    for (_, runtime) in experiment["runtimes"].items():
        # Experiment parameters
        dlib = runtime["dlib"]
        flags = runtime["flags"]
        experiment_env = env
        if "env" in runtime:
            experiment_env = dict(env, **runtime["env"])

        # Stats to be collected
        cycles = []
        cpu_usage = []
        instr_per_cycle = []
        execution_time = []
        cache_miss_rate = []
        task_size = []

        is_first_loop = True
        log(f"Benchmarking {dlib}...")
        for t_size in range(args.maximum_task_size, 1, -1):
            # Prepare arguments
            t_size = 2 ** t_size
            log(f"Task size: {t_size}")
            experiment_args = (
                ["hwloc-bind"]
                + prepare_flags(hwloc_bind_flags, problem_size, t_size)
                + ["bench", f"./{dlib}"]
                + prepare_flags(flags, problem_size, t_size)
            )

            # Initialize averages
            cycles.append(0)
            cpu_usage.append(0)
            instr_per_cycle.append(0)
            execution_time.append(0)
            cache_miss_rate.append(0)

            # Run benchmark
            timeout = False
            for _ in range(n_runs):
                results = run_benchmark(experiment_args, experiment_env)
                if results is None:
                    log("Timeout")
                    timeout = True
                    break
                # Collect results
                cycles[-1] += results["cycles"]
                cpu_usage[-1] += results["cpu_usage"]
                instr_per_cycle[-1] += results["instr_per_cycle"]
                execution_time[-1] += results["execution_time"]
                cache_miss_rate[-1] += results["cache_miss_rate"]

            if timeout:
                # Remove last data point
                cycles.pop()
                cpu_usage.pop()
                instr_per_cycle.pop()
                execution_time.pop()
                cache_miss_rate.pop()
                if is_first_loop:
                    continue
                else:
                    break
            else:
                # Compute average
                cycles[-1] /= n_runs
                cpu_usage[-1] /= n_runs
                instr_per_cycle[-1] /= n_runs
                execution_time[-1] /= n_runs
                cache_miss_rate[-1] /= n_runs
                task_size.append(t_size)
            is_first_loop = False

        runtime["cycles"] = cycles
        runtime["cpu_usage"] = cpu_usage
        runtime["instr_per_cycle"] = instr_per_cycle
        runtime["execution_time"] = execution_time
        runtime["cache_miss_rate"] = cache_miss_rate
        runtime["task_size"] = task_size

        # Sleep some time, there might be a lot of memory to clean up,
        # better let the system handle that before starting next benchmark.
        time.sleep(3)


log(f"Done in {time.time() - t:.2f}s")

if args.file is not None:
    chdir(root)
    with open(args.file, "w") as file:
        json.dump(experiments, file, indent=2)
else:
    print(json.dumps(experiments, indent=2))
