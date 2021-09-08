import argparse
import json
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description="Plot the graphs for the worker benchmark")
parser.add_argument(
    "-f",
    "--file",
    help="The json file containing the data",
)
args = parser.parse_args()

benchmarks = None
with open(args.file, "r") as file:
    benchmarks = json.load(file)

for (experiment, data) in benchmarks.items():
    fig = plt.figure(figsize=(8, 4.5))
    fig.suptitle(f"Execution time with fixed tasks per worker ratio")
    ax = plt.subplot()
    ax.set(
        ylabel="execution time (s)",
        xlabel="number of counter increments per task",
    )
    ax.grid(which="major")
    ax.set_xscale("log", base=10)
    ax.set_yscale("log", base=10)
    for run in data:
        n = run["nb_threads"]
        ax.plot(
            run["task_size"],
            run["execution_time"],
            marker="x",
            label=f"{n} worker{'s' if n > 1 else ''}",
        )
    ax.legend()
    fig.savefig(f"workers_{experiment}")
    plt.close(fig)
