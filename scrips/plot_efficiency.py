import argparse
import json
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Tuple

BARE_METAL = "bare_metal"
RIO = "Rio"
STARPU = "StarPU"

# Magic values :)

# Number of CPU
P = 24
# Initialization overhead for a 4096*4096 matrix on a Miriel node (in seconds)
MM_INITIALIZATION = 0.86
# Execution time of mkl gemm on a 4096x4096 matrix averaged on 14 runs on a
# Miriel node (in seconds)
SEQUENTIAL_MKL_MM_EXEC_TIME = 4.79 - MM_INITIALIZATION

# ——————————————————————————————————— CLI ———————————————————————————————————— #

parser = argparse.ArgumentParser(description="Plot the graphs for the worker benchmark")
parser.add_argument(
    "-f",
    "--file",
    help="The json file containing the data",
)
parser.add_argument(
    "-r",
    "--report",
    help="Generate the plot for report",
    action="store_true",
)
parser.add_argument(
    "-p",
    "--cpu",
    help="Number of CPU used during benchmark",
    type=int
)

args = parser.parse_args()

if not args.cpu:
    print(f"Assuming {P} cpus (use '-p n' to assume 'n' cpus)")
else:
    P = args.cpu

benchmarks: Dict[str, Dict[str, Dict[str, Any]]] = {}
with open(args.file, "r") as file:
    benchmarks = json.load(file)

# —————————————————————————————————— Utils ——————————————————————————————————— #


def normalize(t_total, t):
    return [t / t_tot for (t, t_tot) in zip(t, t_total)]


def scale_up(t: List[float], rt_data: Dict[str, Any]) -> List[float]:
    scaled_t = t
    if "scaling_factor" in rt_data:
        scaled_t = [t * s for (t, s) in zip(scaled_t, rt_data["scaling_factor"])]
    if "frequency_scaling" in rt_data:
        scaled_t = [t * s for (t, s) in zip(scaled_t, rt_data["frequency_scaling"])]
    return scaled_t


def compute_times(t_seq: List[float], rt_data: Dict[str, Any], runtime: str):
    # Runtime-independent
    t_total = rt_data["execution_time"]
    t_task = t_seq  # By hypothesis, t_task = t_seq as there is no locality effect here

    # Runtime-dependent
    t_idle = None

    if runtime == RIO:
        # In Rio the time spent idle vs working is derived from the CPU usage.
        cpu_usage = rt_data["cpu_usage"]
        t_idle = [(1 - usage / P) * t_tot for (usage, t_tot) in zip(cpu_usage, t_total)]
    elif runtime == STARPU:
        # StarPU explicitely tell us how many time it spent sleeping, but that
        # must be scaled by the number of CPU.
        t_idle = [x / P for x in rt_data["sleeping"]]
    else:
        raise Exception(f"Unexpected runtime: {runtime}")

    # Scale up those times to match the number of tasks in the sequential algorithm
    t_total = scale_up(t_total, rt_data)
    t_idle = scale_up(t_idle, rt_data)

    # Finaly, the time spent not working or sleeping is counted as management.
    t_management = [
        t_tot - t_t - t_i for (t_tot, t_t, t_i) in zip(t_total, t_task, t_idle)
    ]

    return (t_total, t_task, t_idle, t_management)


def compute_efficiencies(
    t_seq: List[float],
    t_total: List[float],
    t_task: List[float],
    t_idle: List[float],
) -> Tuple[List[float], List[float], List[float]]:
    e = [t_seq / t_tot for (t_seq, t_tot) in zip(t_seq, t_total)]
    e_p = [t_t / (t_t + t_i) for (t_t, t_i) in zip(t_task, t_idle)]
    e_m = [(t_t + t_i) / t_tot for (t_tot, t_t, t_i) in zip(t_total, t_task, t_idle)]
    return (e, e_p, e_m)


# —————————————————————————————————— Plots ——————————————————————————————————— #


def subplot_report_grid(
    x: int,
    y: int,
    axs,
    experiment,
    runtime: str,
    t_seq: List[float],
):
    rt_data = experiment[runtime]
    (t_total, t_task, t_idle, _) = compute_times(
        t_seq,
        rt_data,
        runtime,
    )
    (e, e_p, e_m) = compute_efficiencies(t_seq, t_total, t_task, t_idle)
    task_size = rt_data["task_size"]
    axs[x, y].plot(task_size, e, label="$e$", marker="|", markersize=11)
    axs[x, y].plot(task_size, e_p, label="$e_p$", marker="2", markersize=11, color="#d62728")
    axs[x, y].plot(task_size, e_m, label="$e_r$", marker="1", markersize=11, color="#9467bd")

    axs[x, y].set_xscale("log", base=10)
    axs[x, y].set_ybound(-0.05, 1.05)
    axs[x, y].grid(which="major")


def plot_report_grid(benchmarks: Dict[str, Dict[str, Dict[str, Any]]]):
    fig, axs = plt.subplots(
        4,
        2,
        sharex=True,
        sharey=True,
        figsize=(10, 12),
    )
    plt.subplots_adjust(
        hspace=0.05,
        wspace=0.05,
        left=0.08,
        right=0.92,
        top=0.94,
        bottom=0.06,
    )

    # Counter
    experiment = benchmarks["counter"]
    t_seq = experiment[BARE_METAL]["execution_time"]
    t_seq = scale_up(t_seq, experiment[BARE_METAL])
    subplot_report_grid(0, 0, axs, experiment, RIO, t_seq)
    subplot_report_grid(0, 1, axs, experiment, STARPU, t_seq)

    # Counter with dependencies
    experiment = benchmarks["counter_deps"]  # we keep the same t_seq
    subplot_report_grid(1, 0, axs, experiment, RIO, t_seq)
    subplot_report_grid(1, 1, axs, experiment, STARPU, t_seq)

    # Matrix multiplication
    experiment = benchmarks["mm_counter"]
    t_seq = experiment[BARE_METAL]["execution_time"]
    t_seq = scale_up(t_seq, experiment[BARE_METAL])
    subplot_report_grid(2, 0, axs, experiment, RIO, t_seq)
    subplot_report_grid(2, 1, axs, experiment, STARPU, t_seq)

    # LU factorization
    experiment = benchmarks["lu_counter"]
    t_seq = experiment[BARE_METAL]["execution_time"]
    t_seq = scale_up(t_seq, experiment[BARE_METAL])
    subplot_report_grid(3, 0, axs, experiment, RIO, t_seq)
    subplot_report_grid(3, 1, axs, experiment, STARPU, t_seq)

    # Titles, units and labels
    axs[0, 0].set_title("Decentralized In-Order (Rio)")
    axs[0, 1].set_title("Centralized Out-of-Order (StarPU)")

    axs[0, 0].set(ylabel="efficiency")
    axs[1, 0].set(ylabel="efficiency")
    axs[2, 0].set(ylabel="efficiency")
    axs[3, 0].set(ylabel="efficiency")

    axs[-1, 0].set(xlabel="task sizes")
    axs[-1, 1].set(xlabel="task sizes")

    axs[0, 1].set_ylabel("Exp 1: independent tasks", rotation=270, labelpad=20)
    axs[0, 1].yaxis.set_label_position("right")
    axs[1, 1].set_ylabel("Exp 2: random dependencies", rotation=270, labelpad=20)
    axs[1, 1].yaxis.set_label_position("right")
    axs[2, 1].set_ylabel("Exp 3: matrix multiplication pattern", rotation=270, labelpad=20)
    axs[2, 1].yaxis.set_label_position("right")
    axs[3, 1].set_ylabel("Exp 4: LU factorization pattern", rotation=270, labelpad=20)
    axs[3, 1].yaxis.set_label_position("right")

    axs[0, 0].legend()

    # Done :)
    fig.savefig(f"efficiency_report_24_cores.pdf")
    plt.close(fig)


def plot_efficiency(
    t_seq: List[float],
    rt_data: Dict[str, Any],
    runtime: str,
    experiment: str,
):
    task_size = rt_data["task_size"]

    # Discard sequential execution time at a granularity for which the runtime
    # got a timeout
    t_seq = t_seq[len(t_seq) - len(task_size) : len(t_seq)]

    # Times
    (t_total, t_task, t_idle, t_management) = compute_times(
        t_seq,
        rt_data,
        runtime,
    )

    # Efficiencies
    (e, e_p, e_m) = compute_efficiencies(t_seq, t_total, t_task, t_idle)

    # Plot efficiencies
    fig = plt.figure(figsize=(8, 4.5))
    fig.suptitle(f"Efficiency decomposition")
    ax = plt.subplot()
    ax.set(
        ylabel="efficiency",
        xlabel="number of counter increments per task",
    )
    ax.grid(which="major")
    ax.set_xscale("log", base=10)

    ax.plot(task_size, e, label="$e$", marker="x")
    ax.plot(task_size, e_p, label="$e_p$", marker="x")
    ax.plot(task_size, e_m, label="$e_r$", marker="x")

    ax.legend()
    ax.set_ybound(-0.05, 1.05)
    fig.savefig(f"efficiency_{experiment}_{runtime}")
    plt.close(fig)

    # Plot times
    fig = plt.figure(figsize=(8, 4.5))
    fig.suptitle(f"Time repartition")
    ax = plt.subplot()
    ax.set(
        ylabel="relative execution time",
        xlabel="number of counter increments per task",
    )
    ax.grid(which="major")
    ax.set_xscale("log", base=10)

    ax.plot(task_size, normalize(t_total, t_task), label="$\\tau_{p,t}$", marker="x")
    ax.plot(task_size, normalize(t_total, t_idle), label="$\\tau_{p,i}$", marker="x")
    ax.plot(
        task_size, normalize(t_total, t_management), label="$\\tau_{p,m}$", marker="x"
    )

    ax.legend()
    ax.set_ybound(-0.05, 1.05)
    fig.savefig(f"time_repartition_{experiment}_{runtime}")
    plt.close(fig)


def plot_full_efficiency(
    t_seq: List[float],
    rt_data: Dict[str, Any],
    runtime: str,
    experiment: str,
):
    """A full decomposition of the efficiency, including granularity and locality

    WARNING: This only works for the mm_mkl benchmark for now."""
    task_size = rt_data["task_size"]

    # Discard sequential execution time at a granularity for which the runtime
    # got a timeout
    t_seq = t_seq[len(t_seq) - len(task_size) : len(t_seq)]

    # Times
    # Only works for StarPU!
    t_total = rt_data["execution_time"]
    t_task = rt_data["working"]
    t_idle = rt_data["sleeping"]

    # Remove time needed for matrix initialization
    t_seq = [x - MM_INITIALIZATION for x in t_seq]
    t_total = [x - MM_INITIALIZATION for x in t_total]

    # Efficiencies
    e = [SEQUENTIAL_MKL_MM_EXEC_TIME / (P * t_tot) for t_tot in t_total]
    e_g = [SEQUENTIAL_MKL_MM_EXEC_TIME / t_seq for t_seq in t_seq]
    # There is already a hidden factor P in t_tasks (it's the sum of
    # t_task for all threads)
    e_l = [t_seq / t_t for (t_seq, t_t) in zip(t_seq, t_task)]
    e_p = [t_t / (t_t + t_i) for (t_t, t_i) in zip(t_task, t_idle)]
    # We need to scale t_tot here because it is the absolute elasped times
    # whereas t_t and t_i are cumulated times for all threads
    e_m = [
        (t_t + t_i) / (P * t_tot) for (t_tot, t_t, t_i) in zip(t_total, t_task, t_idle)
    ]

    # Plot efficiencies
    fig = plt.figure(figsize=(8, 4.5))
    ax = plt.subplot()
    ax.set(
        ylabel="efficiency",
        xlabel="sub-matrices' sizes",
    )
    ax.grid(which="major")
    ax.set_xscale("log", base=2)

    ax.plot(task_size, e, label="$e$", marker="x")
    ax.plot(task_size, e_g, label="$e_g$", marker="x")
    ax.plot(task_size, e_l, label="$e_l$", marker="x")
    ax.plot(task_size, e_p, label="$e_p$", marker="x")
    ax.plot(task_size, e_m, label="$e_r$", marker="x")

    ax.legend()
    # ax.set_ybound(-0.05, 1.05)
    fig.savefig(f"efficiency_{experiment}_{runtime}.pdf")
    plt.close(fig)


# ———————————————————————————————— Main loop ————————————————————————————————— #

# Reference sequential execution time

if args.report:
    # Plot the figure for the report, expects some experiments to be present
    plot_report_grid(benchmarks)
else:
    # Plot experiments present in the data file as individual plots
    for (experiment, data) in benchmarks.items():
        for (runtime, rt_data) in data.items():
            if runtime == BARE_METAL:
                continue
            elif experiment == "counter_deps":
                seq_data = benchmarks["counter"][BARE_METAL]
                t_seq = seq_data["execution_time"]
                t_seq = scale_up(t_seq, seq_data)
                plot_efficiency(t_seq, rt_data, runtime, experiment)
            elif experiment == "lu_counter_1d" or experiment == "lu_counter_2d":
                seq_data = benchmarks["lu_counter"][BARE_METAL]
                t_seq = seq_data["execution_time"]
                t_seq = scale_up(t_seq, seq_data)
                plot_efficiency(t_seq, rt_data, runtime, experiment)
            else:
                seq_data = data[BARE_METAL]
                t_seq = data[BARE_METAL]["execution_time"]
                t_seq = scale_up(t_seq, seq_data)
                if experiment == "mm_mkl":
                    plot_full_efficiency(t_seq, rt_data, runtime, experiment)
                else:
                    plot_efficiency(t_seq, rt_data, runtime, experiment)
