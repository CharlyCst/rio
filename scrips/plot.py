import argparse
import json
import math
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Optional, Tuple

# Magic values :)
# Execution time of mkl gemm on a 4096x4096 matrix averaged on 14 runs on a
# Miriel node (in seconds)
SEQUENTIAL_MKL_MM_EXEC_TIME = 4.79
# Execution time of mkl getrfnpi (LU factorization without pivoting) on a
# 4096x4096 matrix, averaged on 14 runs on a Miriel node (in seconds)
SEQUENTIAL_MKL_LU_EXEC_TIME = 1.615
# Total execution time of a task consisting in incrementing a counter 2**18
# times as a function of the number of increments (in power of two)
COUNTER_EXEC_TIME = {
    24: 1777.4,
    23: 893.1,
    22: 442.0,
    21: 221.5,
    20: 111.3,
    19: 55.57,
    18: 27.83,
    17: 13.92,
    16: 6.963,
    15: 3.491,
    14: 1.779,
    13: 0.908,
    12: 0.478,
    11: 0.264,
    10: 0.156,
    9: 0.096,
    8: 0.059,
    7: 0.043,
    6: 0.029,
    5: 0.017,
    4: 0.014,
    3: 0.011,
    2: 0.010,
}

# ——————————————————————————————————— CLI ———————————————————————————————————— #

parser = argparse.ArgumentParser(
    description="Plot the execution statistics collected by run.py"
)
parser.add_argument("-f", "--file", help="The json file containing the data")
parser.add_argument(
    "-a",
    "--all",
    help="Plot all the figures",
    action="store_true",
)
parser.add_argument(
    "-e",
    "--experiment",
    help="Plot experiment reports",
    action="store_true",
)
parser.add_argument(
    "-t",
    "--thread",
    help="Plot thread efficiency figures",
    action="store_true",
)
parser.add_argument(
    "-r",
    "--report",
    help="Plot figures used in the report",
    action="store_true",
)
args = parser.parse_args()

EXPERIMENT: bool = args.experiment
THREAD: bool = args.thread
REPORT: bool = args.report
if args.all:
    EXPERIMENT = True
    THREAD = True
    REPORT = True

# —————————————————————————————————— Utils ——————————————————————————————————— #


def normalize_series(*series):
    """Takes tuples (values, timestamp) and return the values on the
    intersections of timestamps.

    Example:
    > normalize_series((['a', 'b', 'c'], [1, 2, 3]), (['d', 'e'], [2, 3]))
    ([2, 3], [['b', 'c'], ['d', 'e']])
    """
    timestamps = None
    for (_, ts) in series:
        if timestamps is None:
            timestamps = set(ts)
        else:
            # takes set intersection
            timestamps &= set(ts)

    final_timestamps = []
    final_series = []
    register_ts = True

    for (data, ts) in series:
        serie = []
        for i in range(len(ts)):
            if ts[i] in timestamps:
                serie.append(data[i])
                if register_ts:
                    final_timestamps.append(ts[i])
        final_series.append(serie)
        register_ts = False
    return (final_timestamps, final_series)


def to_superscript(num: int) -> str:
    superscripts = {
        "0": "⁰",
        "1": "¹",
        "2": "²",
        "3": "³",
        "4": "⁴",
        "5": "⁵",
        "6": "⁶",
        "7": "⁷",
        "8": "⁸",
        "9": "⁹",
    }
    str_num = ""
    for char in f"{num}":
        str_num += superscripts[char]
    return str_num


def subplot_comparison(
    nb_plots: int,
    index: int,
    runtimes: Dict[str, Any],
    x: str,
    x_label: str,
    y: str,
    y_label: str,
    y_log_scale: bool = False,
    y_limits: Optional[List[Optional[int]]] = None,
):
    ax = plt.subplot(nb_plots, 1, index)
    ticks = set()
    for (runtime, data) in runtimes.items():
        ax.plot(data[x], data[y], label=runtime, marker="x")
        ticks.update(data[x])
    ticks = [tick for tick in ticks]
    ticks.sort()
    ax.grid()
    ax.set(ylabel=y_label, xlabel=x_label)
    ax.set_xscale("log", base=2)
    ax.set_xticks(ticks)
    if y_limits is not None:
        ax.set_ylim(y_limits)
    if y_log_scale:
        ax.set_yscale("log", base=10)
    plt.legend()


def plot_comparison(title: str, file_name: str, runtimes: Dict[str, Any]):
    nb_plots = 4
    fig = plt.figure(figsize=(8, 15))
    fig.suptitle(title)
    subplot_comparison(
        nb_plots,
        1,
        runtimes,
        "task_size",
        "",
        "execution_time",
        "execution time (s)",
        y_log_scale=True,
    )
    subplot_comparison(
        nb_plots,
        2,
        runtimes,
        "task_size",
        "",
        "cpu_usage",
        "cpu usage",
        y_limits=[0, None],
    )
    subplot_comparison(
        nb_plots,
        3,
        runtimes,
        "task_size",
        "",
        "instr_per_cycle",
        "instructions/cycle",
        y_limits=[0, None],
    )
    subplot_comparison(
        nb_plots,
        4,
        runtimes,
        "task_size",
        "tile size",
        "cache_miss_rate",
        "cache miss rate",
        y_limits=[0, 1],
    )
    fig.savefig(f"{file_name}.pdf")
    plt.close(fig)


def plot_thread_efficiency(
    runtime: str,
    problem_size: int,
    experiment: str,
    data: List[Tuple[int, List, List]],
):
    fig = plt.figure(figsize=(8, 4.5))
    fig.suptitle(
        f"{experiment} - {problem_size}x{problem_size} matrix with {runtime}",
    )
    ax = plt.subplot()
    for (nb_threads, execution_time, task_size) in data:
        ax.plot(
            task_size,
            execution_time,
            label=f"{nb_threads} threads",
            marker="x",
        )
    ax.set(ylabel="execution time (s)", xlabel="task size")
    ax.set_yscale("log", base=10)
    ax.set_xscale("log", base=2)
    ax.grid(which="both")
    plt.legend()
    fig.savefig(f"thread_efficiency_{runtime}_{problem_size}_{experiment}.pdf")
    plt.close(fig)


def plot_time_vs_task_size(
    runtime: str,
    experiment: str,
    data: Tuple[int, List, List],
    expriment_description: Optional[str] = None,
):
    (nb_threads, execution_time, task_size) = data
    exp_description = experiment
    if expriment_description is not None:
        exp_description = expriment_description

    fig = plt.figure(figsize=(8, 4.5))
    fig.suptitle(
        f"{problem_size}x{problem_size} {exp_description} with {runtime} ({nb_threads} threads)",
    )
    ax = plt.subplot()
    ax.plot(
        task_size,
        execution_time,
        marker="x",
    )
    ax.set(ylabel="execution time (s)", xlabel="task size")
    ax.set_yscale("log", base=10)
    ax.set_xscale("log", base=2)
    ax.grid(which="major")
    fig.savefig(f"report_{runtime}_{problem_size}_{experiment}.pdf")


def plot_experiment_simple(
    runtimes: Dict[str, Any],
    experiment: str,
    expriment_description: str,
):
    fig = plt.figure(figsize=(8, 4.5))
    fig.suptitle(
        f"{problem_size}x{problem_size} {expriment_description} ({nb_threads} threads)",
    )
    ax = plt.subplot()
    for (runtime, data) in runtimes.items():
        ax.plot(data["task_size"], data["execution_time"], label=runtime, marker="x")
    ax.set(ylabel="execution time (s)", xlabel="task size")
    ax.set_yscale("log", base=10)
    ax.set_xscale("log", base=2)
    ax.grid(which="major")
    plt.legend()
    fig.savefig(f"report_experiment_{problem_size}_{experiment}.pdf")
    plt.close(fig)


def plot_counter_experiment(
    runtimes: Dict[str, Any],
    problem_size: int,
):
    fig = plt.figure(figsize=(8, 4.5))
    problem_size = int(math.log(problem_size, 2))
    fig.suptitle(
        f"Execution time for executing $2^{{problem_size}}$ tasks consisting in incrementing a counter ({nb_threads} threads)",
    )
    ax = plt.subplot()
    for (runtime, data) in runtimes.items():
        ax.plot(data["task_size"], data["execution_time"], label=runtime, marker="x")
    ax.set(ylabel="execution time (s)", xlabel="number of counter increments per task")
    ax.set_yscale("log", base=10)
    ax.set_xscale("log", base=10)
    ax.grid(which="major")
    plt.legend()
    fig.savefig(f"report_counter_{problem_size}.pdf")
    plt.close(fig)


def plot_counter_efficiency(
    data: Dict[str, Any],
    n_cpu: int,
    problem_size: int,
):
    fig = plt.figure(figsize=(8, 4.5))
    problem_size = int(math.log(problem_size, 2))
    fig.suptitle(
        f"Execution time for executing $2^{ {problem_size} }$ tasks consisting in incrementing a counter ({nb_threads} threads)",
    )
    ax = plt.subplot()
    task_sizes = data["task_size"]
    cpu_usage = [cpu_usage / n_cpu for cpu_usage in data["cpu_usage"]]
    t_granularity = [
        COUNTER_EXEC_TIME[int(math.log(t_size, 2))] for t_size in task_sizes
    ]
    # We take the max between the measured total time and an estimation from a
    # sequential run to keep the efficiency between 0 and 1 (this only affects
    # coarse granularity where the runtime is somethime faster due to
    # experimental fluctuations).
    t_total = [
        max(t_g / n_cpu, t_tot) for (t_g, t_tot) in zip(t_granularity, data["execution_time"])
    ]
    t_idle = [(1 - cpu_usage) * t for (cpu_usage, t) in zip(cpu_usage, t_total)]
    t_task = [t_g / n_cpu for t_g in t_granularity]
    t_management = [
        t_tot - t_i - t_t for (t_tot, t_i, t_t) in zip(t_total, t_idle, t_task)
    ]

    e_p = [
        t_g / (n_cpu * (t_t + t_i))
        for (t_g, t_t, t_i) in zip(t_granularity, t_task, t_idle)
    ]
    e_m = [(t_t + t_i) / t_tot for (t_tot, t_t, t_i) in zip(t_total, t_task, t_idle)]

    # ax.plot(data["task_size"], t_total, label="total", marker="x")
    # ax.plot(data["task_size"], t_task, label="task", marker="x")
    # ax.plot(data["task_size"], t_idle, label="idle", marker="x")
    # ax.plot(data["task_size"], t_management, label="management", marker="x")

    ax.plot(data["task_size"], e_p, label="$e_p$", marker="x")
    ax.plot(data["task_size"], e_m, label="$e_m$", marker="x")

    ax.set(ylabel="execution time (s)", xlabel="number of counter increments per task")
    # ax.set_yscale("log", base=10)
    ax.set_xscale("log", base=10)
    ax.set_ylim = [0, 1]
    ax.grid(which="major")
    plt.legend()
    fig.savefig(f"report_counter_efficiency_{n_cpu}.pdf")
    plt.close(fig)


def plot_kernel_efficiency(
    execution_time: List[float],
    task_sizes: List[int],
    reference: float,
    title: str,
    experiment_name: str,
):
    efficiency = [min(reference / x, 1) for x in execution_time]

    fig = plt.figure(figsize=(8, 4.5))
    fig.suptitle(title)
    ax = plt.subplot()
    ax.plot(task_sizes, efficiency, label=runtime, marker="x")
    ax.set(ylabel="efficiency", xlabel="task size")
    ax.grid(which="both")
    ax.set_xscale("log", base=2)
    ax.set_ylim([0, 1])
    plt.xticks(task_sizes)
    fig.savefig(f"report_efficiency_{experiment_name}.pdf")
    plt.close(fig)


def plot_runtime_efficiceny(
    kernel_execution_time: List[float],
    kernel_task_sizes: List[int],
    runtimes: Dict[str, Any],
    nb_threads: int,
    title: str,
    experiment_name: str,
):
    sequential_reference = {
        task_size: exec_time
        for (task_size, exec_time) in zip(kernel_task_sizes, kernel_execution_time)
    }

    fig = plt.figure(figsize=(8, 4.5))
    fig.suptitle(title)
    ax = plt.subplot()
    for (runtime, data) in runtimes.items():
        rt_task_sizes = []
        rt_efficiency = []
        ts = data["task_size"]
        et = data["execution_time"]
        # Compute efficiency
        for i in range(len(ts)):
            if ts[i] in sequential_reference:
                rt_task_sizes.append(ts[i])
                rt_efficiency.append(
                    sequential_reference[ts[i]] / (nb_threads * et[i]),
                )
        ax.plot(
            rt_task_sizes,
            rt_efficiency,
            label=runtime,
            marker="x",
        )
    ax.set(ylabel="efficiency", xlabel="task size")
    ax.set_xscale("log", base=2)
    ax.grid(which="both")
    ax.set_ylim([0, 1])
    plt.legend()
    fig.savefig(f"report_efficiency_{experiment_name}.pdf")
    plt.close(fig)


def plot_runtime_efficiency_decomposition(
    kernel_reference_time: float,
    kernel_execution_time: List[float],
    kernel_task_sizes: List[int],
    runtime_sequential_data: Dict[str, Any],
    runtime_multithread_data: Dict[str, Any],
    nb_threads: int,
    title: str,
    experiment_name: str,
):
    (
        task_sizes,
        [
            kernel_time,
            runtime_sequential_time,
            runtime_multithread_time,
        ],
    ) = normalize_series(
        (kernel_execution_time, kernel_task_sizes),
        (
            runtime_sequential_data["execution_time"],
            runtime_sequential_data["task_size"],
        ),
        (
            runtime_multithread_data["execution_time"],
            runtime_multithread_data["task_size"],
        ),
    )

    # Compute efficiencies
    ep = [
        min(kernel_reference_time / (x * nb_threads), 1)
        for x in runtime_multithread_time
    ]
    e_g = [min(kernel_reference_time / x, 1) for x in kernel_execution_time]
    e_m = [
        min(kernel_t / rt_seq_t, 1)
        for (kernel_t, rt_seq_t) in zip(kernel_time, runtime_sequential_time)
    ]
    e_s = [
        min(rt_seq_t / (rt_mult_t * nb_threads), 1)
        for (rt_seq_t, rt_mult_t) in zip(
            runtime_sequential_time, runtime_multithread_time
        )
    ]

    fig = plt.figure(figsize=(8, 4.5))
    fig.suptitle(title)
    ax = plt.subplot()
    ax.plot(
        task_sizes,
        ep,
        label=r"$e_p$",
        marker="x",
    )
    ax.plot(
        kernel_task_sizes,
        e_g,
        label=r"$e_g$",
        marker="x",
    )
    ax.plot(
        task_sizes,
        e_m,
        label=r"$e_m$",
        marker="x",
    )
    ax.plot(
        task_sizes,
        e_s,
        label=r"$e_s$",
        marker="x",
    )
    ax.set(ylabel="efficiency", xlabel="task size")
    ax.set_xscale("log", base=2)
    ax.grid(which="both")
    ax.set_ylim([0, 1.01])
    ax.set_xlim([2 ** 2 - 1, 2 ** 10 + 500])
    plt.xticks(kernel_task_sizes)
    plt.legend()
    fig.savefig(f"report_efficiency_{experiment_name}.pdf")
    plt.close(fig)


# ——————————————————————————————————— Plot ——————————————————————————————————— #

benchmarks = None
with open(args.file, "r") as file:
    benchmarks = json.load(file)

# Performances of a triple (runtime, problem_size, experiment):
# Map (runtime, problem_size, experiment) -> (nb_threads, exec_time, task_size)
runtime_experiments = {}

for (title, data) in benchmarks.items():
    problem_size = data["problem_size"]
    nb_threads = data["nb_threads"]
    experiment = data["experiment"]

    for (runtime, rt_data) in data["runtimes"].items():
        key = (runtime, problem_size, experiment)
        if not key in runtime_experiments:
            runtime_experiments[key] = []
        runtime_experiments[key].append(
            (
                nb_threads,
                rt_data["execution_time"],
                rt_data["task_size"],
            ),
        )

    runtimes = data["runtimes"]
    if EXPERIMENT:
        plot_comparison(
            f"{title} - {problem_size}x{problem_size} matrix on {nb_threads} threads",
            f"{title}-{problem_size}-{nb_threads}",
            runtimes,
        )

    if REPORT and nb_threads == 24:
        if experiment == "mm_mkl":
            plot_experiment_simple(
                runtimes,
                experiment,
                "Matrix Multiplication",
            )
        elif experiment == "lu_mkl":
            plot_experiment_simple(
                runtimes,
                experiment,
                "LU Factorization without pivoting",
            )
        elif experiment == "counter":
            plot_counter_experiment(runtimes, problem_size)
            if "ReactRT" in runtimes:
                plot_counter_efficiency(runtimes["ReactRT"], nb_threads, problem_size)

if THREAD:
    for ((runtime, problem_size, experiment), data) in runtime_experiments.items():
        if len(data) <= 1:
            continue
        plot_thread_efficiency(runtime, problem_size, experiment, data)

if REPORT:
    # Plot efficiency for a single StarPU run
    starpu_efficiency_experiment = ("StarPU", 4096, "mm_mkl")
    n_cpu = 24
    if starpu_efficiency_experiment in runtime_experiments:
        for data in runtime_experiments[starpu_efficiency_experiment]:
            if data[0] == n_cpu:
                plot_time_vs_task_size(
                    "StarPU",
                    "mm_mkl",
                    data,
                    expriment_description="Matrix Multiplication",
                )
                break

    # Plot efficiency
    bare_metal_mm_mkl = ("Bare Metal", 4096, "mm_mkl")
    if bare_metal_mm_mkl in runtime_experiments:
        (nb_threads, kernel_execution_time, task_sizes) = runtime_experiments[
            bare_metal_mm_mkl
        ][0]
        if nb_threads != 1:
            print(
                "unexpected number of threads for bare metal MKL matrix multiplication: "
                + str(nb_threads)
            )

        # Efficiency decomposition with matrix multiplication
        runtime_data_sequential_mm = benchmarks["mm_mkl_4096_1"]["runtimes"]
        runtime_data_2_threads_mm = benchmarks["mm_mkl_4096_2"]["runtimes"]
        runtime_data_multithread_mm = benchmarks["mm_mkl_4096_24"]["runtimes"]
        nb_threads: int = benchmarks["mm_mkl_4096_24"]["nb_threads"]

        plot_kernel_efficiency(
            kernel_execution_time,
            task_sizes,
            SEQUENTIAL_MKL_MM_EXEC_TIME,
            "Intel MKL matrix multiplication efficiency on 4096x4096 matrices",
            "mkl_mm_efficiency",
        )
        plot_runtime_efficiceny(
            kernel_execution_time,
            task_sizes,
            runtime_data_multithread_mm,
            nb_threads,
            "Runtime efficiency on 4096x4096 matrix multiplication",
            "runtime_efficiencies_4096_24_mm",
        )
        plot_runtime_efficiency_decomposition(
            SEQUENTIAL_MKL_MM_EXEC_TIME,
            kernel_execution_time,
            task_sizes,
            runtime_data_sequential_mm["ReactRT"],
            runtime_data_multithread_mm["ReactRT"],
            nb_threads,
            f"ReactRT efficiency decomposition on 4096x4096 matrix multiplication ({nb_threads} threads)",
            "reactrt_mm",
        )
        plot_runtime_efficiency_decomposition(
            SEQUENTIAL_MKL_MM_EXEC_TIME,
            kernel_execution_time,
            task_sizes,
            runtime_data_2_threads_mm["StarPU"],
            runtime_data_multithread_mm["StarPU"],
            nb_threads,
            f"StarPU efficiency decomposition on 4096x4096 matrix multiplication ({nb_threads} threads)",
            "starpu_mm",
        )

    bare_metal_lu_mkl = ("Bare Metal", 4096, "lu_mkl")
    if bare_metal_lu_mkl in runtime_experiments:
        (nb_threads, kernel_execution_time, task_sizes) = runtime_experiments[
            bare_metal_lu_mkl
        ][0]
        if nb_threads != 1:
            print(
                "unexpected number of threads for bare metal MKL matrix multiplication: "
                + str(nb_threads)
            )
        # Efficiency decomposition with LU factorization
        runtime_data_sequential_lu = benchmarks["lu_mkl_4096_1"]["runtimes"]
        runtime_data_2_threads_lu = benchmarks["lu_mkl_4096_2"]["runtimes"]
        runtime_data_multithread_lu = benchmarks["lu_mkl_4096_24"]["runtimes"]
        nb_threads: int = benchmarks["lu_mkl_4096_24"]["nb_threads"]

        plot_kernel_efficiency(
            kernel_execution_time,
            task_sizes,
            SEQUENTIAL_MKL_LU_EXEC_TIME,
            "Intel MKL LU factorization efficiency on 4096x4096 matrices",
            "mkl_lu_efficiency",
        )
        plot_runtime_efficiceny(
            kernel_execution_time,
            task_sizes,
            runtime_data_multithread_lu,
            nb_threads,
            "Runtime efficiency on 4096x4096 LU factorization",
            "runtime_efficiencies_4096_24_lu",
        )
        plot_runtime_efficiency_decomposition(
            SEQUENTIAL_MKL_LU_EXEC_TIME,
            kernel_execution_time,
            task_sizes,
            runtime_data_sequential_lu["ReactRT"],
            runtime_data_multithread_lu["ReactRT"],
            nb_threads,
            f"ReactRT efficiency decomposition on 4096x4096 LU factorization ({nb_threads} threads)",
            "reactrt_lu",
        )
        plot_runtime_efficiency_decomposition(
            SEQUENTIAL_MKL_LU_EXEC_TIME,
            kernel_execution_time,
            task_sizes,
            runtime_data_2_threads_lu["StarPU"],
            runtime_data_multithread_lu["StarPU"],
            nb_threads,
            f"StarPU efficiency decomposition on 4096x4096 LU factorization ({nb_threads} threads)",
            "starpu_lu",
        )
