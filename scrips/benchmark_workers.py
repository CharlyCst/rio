import subprocess
import json
import argparse
import time
import sys
from os import path, getcwd, chdir, environ
from typing import List, Optional, Dict

t = time.time()

# Paths
root = getcwd()
program = "counter"
benchmark_path = "/tmp"
bench_path = path.join(root, "bench")
exec_path = path.join(benchmark_path, program)
rio_path = path.join(root, "rio")
program_path = path.join(root, "rio", "target", "release", program)

# —————————————————————————————————— Flags ——————————————————————————————————— #

hwloc_bind_flags = ["core:0:%n"]
bench_flags = ["-j", "--args", "%p %t -n %n"]

# ——————————————————————————————————— CLI ———————————————————————————————————— #

parser = argparse.ArgumentParser(
    description="Run the worker benchmark",
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
    help="timeout (in seconds)",
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
    help="the maximum number of threads, in power of 2 (default to 2)",
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
parser.add_argument(
    "-e",
    "--experiment",
    help="name of the experiment, (default to 'default')",
    default="default",
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


# ——————————————————————————————— Build Utils ———————————————————————————————— #


def build_reactrt_target(target: str) -> str:
    """Build a ReactRT target and return the name the produced artefact"""
    chdir(rio_path)
    run(
        ["cargo", "build", "--package", "experiments", "--release"],
        with_timeout=False,
    )
    dlib = "reactrt_" + target
    reacrt_target_path = path.join("target", "release")
    run(["cp", path.join(reacrt_target_path, target), path.join(benchmark_path, dlib)])
    return dlib


# —————————————————————————— Analyze CLI arguments ——————————————————————————— #

if not args.average_on >= 1:
    print(f"Invalid number of runs: got '{args.average_on}'")
    sys.exit(1)

print("Experiment setting:\n")
print(f"  - problem size:\t{2 ** args.problem_size}")
print(f"  - maximum task size:\t{2 ** args.maximum_task_size}")
print(f"  - number of threads:\t{2 ** (args.nb_threads - 1)}")
print(f"  - timeout:\t\t{args.timeout}s")
print(f"  - averaged on:\t{args.average_on} run{'s' if args.average_on>1 else ''}")
print()

# ——————————————————————————————— Build Phase ———————————————————————————————— #

log("Checking `hwloc-bind` availability...")
run(["hwloc-bind", "--version"])

log("Loading data file if it exists...")
experiments = {}
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
chdir(rio_path)
run(["cargo", "build", "--release", "--examples"], with_timeout=False)
run(["cp", program_path, exec_path], with_timeout=False)

# ———————————————————————————————— Benchmark ————————————————————————————————— #

chdir(benchmark_path)
problem_size = 2 ** args.problem_size
n_runs = args.average_on
experiments[args.experiment] = []
for k in range(args.nb_threads):
    nb_threads = 2 ** k
    log(f"Running with {nb_threads} thread{'s' if nb_threads > 1 else ''}...")

    # Stats to be collected
    experiment = {}
    cycles = []
    cpu_usage = []
    instr_per_cycle = []
    execution_time = []
    cache_miss_rate = []
    task_size = []

    is_first_loop = True
    for t_size in range(2, args.maximum_task_size + 1):
        t_size = 2 ** t_size
        p_size = problem_size * nb_threads
        experiment_args = (
            ["hwloc-bind"]
            + prepare_flags(hwloc_bind_flags, nb_threads, p_size, t_size)
            + ["bench", f"{exec_path}"]
            + prepare_flags(bench_flags, nb_threads, p_size, t_size)
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
            results = run_benchmark(experiment_args, dict(**environ))
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

    experiment["cycles"] = cycles
    experiment["cpu_usage"] = cpu_usage
    experiment["instr_per_cycle"] = instr_per_cycle
    experiment["execution_time"] = execution_time
    experiment["cache_miss_rate"] = cache_miss_rate
    experiment["task_size"] = task_size
    experiment["nb_threads"] = nb_threads
    experiments[args.experiment].append(experiment)

log(f"Done in {time.time() - t:.2f}s")

if args.file is not None:
    chdir(root)
    with open(args.file, "w") as file:
        json.dump(experiments, file, indent=2)
else:
    print(json.dumps(experiments, indent=2))
