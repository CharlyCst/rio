import subprocess
import json
import argparse
import time
import sys
import math
from os import path, getcwd, chdir, environ
from typing import List, Optional, Dict, Union, Tuple, Iterator, Callable

# Constants
RIO = "Rio"
BARE_METAL = "bare_metal"
STARPU = "StarPU"

t = time.time()
join = path.join

# Paths
root = getcwd()
benchmark_path = "/tmp"
bench_path = join(root, "bench")
rio_path = join(root, "rio")
starpu_path = join(root, "starpu")
bare_metal_path = join(root, "bare_metal")

experiment_targets = {
    "counter": {
        RIO: "counter",
        BARE_METAL: "counter",
        STARPU: "counter",
    },
    "counter_deps": {
        RIO: "counter_deps",
        STARPU: "counter_deps",
    },
    "lu_counter": {
        RIO: "lu_counter",
        STARPU: "lu_counter",
        BARE_METAL: "lu_counter",
    },
    # "lu_counter_2d": {
    #     RIO: "lu_counter"
    # },
    # "lu_counter_1d": {
    #     RIO: "lu_counter"
    # },
    "mm_counter": {
        RIO: "mm_counter",
        STARPU: "mm_counter",
        BARE_METAL: "mm_counter",
    },
}

runtime_environments = {
    RIO: {},
    BARE_METAL: {},
    STARPU: {
        "STARPU_PROFILING": "1",
        "STARPU_WORKER_STATS": "1",
    },
}

# Extra bash commands that can be passed to further refine benchmark output.
# The output will be piped (unix '|') into them.
runtime_extra_processing = {
    RIO: None,
    BARE_METAL: None,
    # StarPU output stats to stderr, we pipe that into awk to extend the json with useful data
    STARPU: [
        "awk",
        "-v",
        "CONVFMT=%.12g",
        r"""/task/{tasks+=$1}; /total:/{working+=$5; sleeping+=$8; overhead+=$11}; /{.*}/{json=substr($0, 2, length($0)-2)}; END{print "{" json ",\"tasks\":" tasks ",\"working\":" working / 1000 ",\"sleeping\":" sleeping / 1000 ",\"overhead\":" overhead / 1000 "}"}""",
    ],
}

# —————————————————————————————————— Flags ——————————————————————————————————— #

hwloc_bind_flags = ["core:0:%n"]
bench_flags = {
    RIO: ["-j", "--args", "%p %t -n %n"],
    BARE_METAL: ["-j", "--args", "%p %t"],
    STARPU: ["-j", "--args", "%p %t"],
}
bench_flag_overwrite = {
    "lu_counter_2d": {
        RIO: ["-j", "--args", "%p %t -n %n --2d"],
    },
    "lu_counter_1d": {
        RIO: ["-j", "--args", "%p %t -n %n --1d"],
    },
}

# ——————————————————————————————————— CLI ———————————————————————————————————— #

parser = argparse.ArgumentParser(
    description="Run the efficiency benchmark",
)
parser.add_argument(
    "-v",
    "--verbose",
    help="print progress",
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
    "-n",
    "--nb-threads",
    metavar="N",
    help="the maximum number of threads, in power of 2 (default to 2)",
    type=int,
    default=2,
    dest="nb_threads",
)
parser.add_argument(
    "-e",
    "--experiment",
    metavar="E",
    help="an experiment to run, default to all",
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


def run(cmd_args: List[str]):
    """A small wrapper around subprocess.run"""
    result = subprocess.run(cmd_args, stdout=subprocess.DEVNULL)
    result.check_returncode()


def run_benchmark(
    cmd_args: List[str],
    env: Dict[str, str],
    extra_processing: Union[None, List[str]] = None,
) -> Optional[Dict[str, float]]:
    """A wrapper around subprocess.run for benchmark use.
    The output of the subprocess will be captured, parsed as json and returned.
    In case of timeout, None is returned instead.
    """
    handle = subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
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
                if extra_processing is not None:
                    handle = subprocess.Popen(
                        extra_processing,
                        stdin=handle.stdout,
                        stdout=subprocess.PIPE,
                    )
                    handle.wait()
                # Return the benchmark results
                output = handle.stdout.read()
                return json.loads(output)


def prepare_flags(
    flags: List[str], nb_threads: int, problem_size: int, task_size: int
) -> List[str]:
    """Substiture all placeholders in the given flags."""
    return [
        flag.replace("%n", str(nb_threads))
        .replace("%t", str(task_size))
        .replace("%p", str(problem_size))
        for flag in flags
    ]


def update_run_stats(previous: Dict[str, float], new_run: Dict[str, Union[float, int]]):
    for field, value in new_run.items():
        if not field in previous:
            previous[field] = 0
        previous[field] += value


def append_run_stats(
    stats: Dict[str, List[float]],
    run_stats: Dict[str, float],
    average_on: int,
    task_size: int,
):
    for field, value in run_stats.items():
        if not field in stats:
            stats[field] = []
        stats[field].append(value / average_on)
    if not "task_size" in stats:
        stats["task_size"] = []
    stats["task_size"].append(task_size)


# ——————————————————————————————— Build Utils ———————————————————————————————— #


def build_rio_target(target: str) -> str:
    """Build a Rio target and return the name of the produced artefact"""
    log(f"Building {target} for Rio")
    chdir(rio_path)
    run(["cargo", "build", "--bin", target, "--release"])
    exe = join(benchmark_path, "rio_" + target)
    rio_target_path = join("target", "release")
    run(["cp", join(rio_target_path, target), exe])
    return exe


def build_starpu_target(target: str) -> str:
    """Build a StarPU target and return the name of the produced artifact"""
    log(f"Building {target} for StarPU")
    chdir(starpu_path)
    run(["make", "-B", target])
    exe = join(benchmark_path, "starpu_" + target)
    run(["cp", target, exe])
    return exe


def build_bare_metal_target(target: str) -> str:
    """Build a Bare Metal target and return the name of the produced artefact"""
    log(f"Building {target} for bare metal")
    chdir(bare_metal_path)
    run(["make", "-B", target])
    exe = join(benchmark_path, "bare_metal_" + target)
    run(["cp", target, exe])
    return exe


# ————————————————————— Experiment parameters iterators —————————————————————— #


def counterParameters(runtime: str, nb_threads: int) -> Iterator[Tuple[int, int]]:
    """Calibrate the number of tasks so that one run takes between ~1s and ~10s
    on the counter family of experiments"""
    for g in range(24, 4, -1):
        t_size = 2 ** g
        n_tasks = 2 ** (33 - g)
        if runtime != BARE_METAL:
            n_tasks = n_tasks * nb_threads
        yield (t_size, n_tasks)


def matrixCounterParameters(
    _runtime: str, _nb_threads: int
) -> Iterator[Tuple[int, int]]:
    """An iterator for the LU & MM counter benchmarks"""
    for g in range(24, 4, -1):
        t_size = 2 ** g
        n_tasks = 2 ** (24 - g)
        if runtime == BARE_METAL:
            # Adjust sequential execution time
            if g < 12:
                n_tasks = n_tasks // nb_threads
            else:
                t_size = t_size // nb_threads
        yield (t_size, n_tasks)


def matrixParameters(_runtime: str, _nb_threads: int) -> Iterator[Tuple[int, int]]:
    """An iterator returning appropriate task sizes for matrix operations
    (gemm, LU...) with real data"""
    n_tasks = 2 ** 12
    for g in range(11, 2, -1):
        t_size = 2 ** g
        yield (t_size, n_tasks)


experiment_parameters: Dict[str, Callable[[str, int], Iterator[Tuple[int, int]]]] = {
    "counter": counterParameters,
    "counter_deps": counterParameters,
    "mm_mkl": matrixParameters,
    "lu_counter": matrixCounterParameters,
    "lu_counter_1d": matrixCounterParameters,
    "lu_counter_2d": matrixCounterParameters,
    "mm_counter": matrixCounterParameters,
}

# —————————————————————————— Analyze CLI arguments ——————————————————————————— #

if not args.average_on >= 1:
    print(f"Invalid number of runs: got '{args.average_on}'")
    sys.exit(1)

print("Experiment setting:\n")
print(f"  - number of threads:\t{args.nb_threads}")
print(f"  - averaged on:\t{args.average_on} run{'s' if args.average_on > 1 else ''}")
print(f"  - timeout:\t\t{args.timeout}s")
print(f"  - experiments: \t{args.experiment if args.experiment is not None else 'all'}")
print()

# ——————————————————————————————— Build Phase ———————————————————————————————— #

log("Checking `hwloc-bind` availability...")
run(["hwloc-bind", "--version"])
log("Building bench...")
chdir(bench_path)
run(["cargo", "install", "--path", "."])


log("Loading data file if it exists...")
experiments = {}
todo_experiments = []
try:
    if args.file is not None:
        with open(join("../", args.file), "r") as file:
            experiments = json.load(file)
            log("File found")
except OSError:
    # The file does not yet exists, this is fine
    log("No file found")
    pass


log("\nBuilding targets...")
targets: Dict[str, Dict[str, str]] = {}
for (experiment, exp_targets) in experiment_targets.items():
    targets[experiment] = {}
    for (runtime, target) in exp_targets.items():
        if runtime == RIO:
            targets[experiment][RIO] = build_rio_target(target)
        elif runtime == STARPU:
            targets[experiment][STARPU] = build_starpu_target(target)
        elif runtime == BARE_METAL:
            targets[experiment][BARE_METAL] = build_bare_metal_target(target)
        else:
            raise Exception(f"Unkonw runtime: {runtime}")

# ———————————————————————————————— Benchmark ————————————————————————————————— #

chdir(benchmark_path)
n_runs = args.average_on
nb_threads = args.nb_threads

for (experiment, exp_targets) in targets.items():
    if not (args.experiment == None or args.experiment == experiment):
        continue
    else:
        if not experiment in experiments:
            experiments[experiment] = {}
    parameters = experiment_parameters[experiment]
    for (runtime, target) in exp_targets.items():
        time.sleep(1)  # Sleep to let the OS clean old processes and reduce noise
        log(f"Benchmarking {runtime}")

        # Stats to be collected
        data = {}
        scaling = 1  # Scaling factor
        warm_up = True
        for (t_size, n_tasks) in parameters(runtime, nb_threads):
            log(f"Running with g={int(math.log(t_size, 2))}...")

            # Scale down the number of tasks to keep reasonable execution times
            if int(n_tasks / scaling) >= 1:
                n_tasks = int(n_tasks / scaling)

            exp_bench_flags = bench_flags[runtime]
            if experiment in bench_flag_overwrite:
                exp_bench_flags = bench_flag_overwrite[experiment][runtime]
            experiment_args = (
                ["hwloc-bind"]
                + prepare_flags(hwloc_bind_flags, nb_threads, n_tasks, t_size)
                + ["bench", f"{target}"]
                + prepare_flags(exp_bench_flags, nb_threads, n_tasks, t_size)
            )

            # Warming up for the first run with each runtime
            if warm_up:
                warm_up = False
                run_benchmark(
                    experiment_args,
                    dict(**environ, **runtime_environments[runtime]),
                    runtime_extra_processing[runtime],
                )

            # Run benchmark
            timeout = False
            run_stat = {}
            for _ in range(n_runs):
                results = run_benchmark(
                    experiment_args,
                    dict(**environ, **runtime_environments[runtime]),
                    runtime_extra_processing[runtime],
                )
                if results is None:
                    log("Timeout")
                    timeout = True
                    break
                update_run_stats(run_stat, results)

            if timeout:
                break
            run_stat["scaling_factor"] = scaling * n_runs  # will be averaged on n_runs
            append_run_stats(data, run_stat, n_runs, t_size)

            # Scale down the number of tasks if the execution took too long
            if "execution_time" in run_stat:
                exec_time = run_stat["execution_time"]
                if exec_time >= 40:
                    scaling *= 2
                if exec_time >= 80:
                    scaling *= 2
                if exec_time >= 160:
                    scaling *= 2

        experiments[experiment][runtime] = data

log(f"Done in {time.time() - t:.2f}s")

if args.file is not None:
    chdir(root)
    with open(args.file, "w") as file:
        json.dump(experiments, file, indent=2)
else:
    print(json.dumps(experiments, indent=2))
