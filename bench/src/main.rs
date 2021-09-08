#[macro_use]
extern crate dlopen_derive;
mod cli;
mod command;
mod monitor;
mod program;
mod stats;

use cli::{Args, Clap};
use monitor::Monitor;
use program::{CProgram, ExternalProgram, RustProgram};
use stats::Stats;
use std::process::exit;
use ctrlc::set_handler;

fn main() {
    let args = Args::parse();
    set_signal_handler();
    let stats = match (args.c, args.rust) {
        (false, false) => benchmark_executable(&args.path, &args.args),
        (true, false) => benchmark_shared::<CProgram>(&args.path, &args.args),
        (false, true) => benchmark_shared::<RustProgram>(&args.path, &args.args),
        (true, true) => {
            println!(
                "Error: flags '-c' and '-r' can't be both used, only one ABI can be selected."
            );
            exit(1);
        }
    };

    if args.json {
        println!("{}", stats.json());
    } else {
        println!("{}", stats)
    }
}

fn benchmark_executable(path: &str, args: &str) -> Stats {
    // Prepare monitor & command
    let mut monitor = Monitor::new();
    let mut cmd = command::Process::new(path, args);

    // Run & collect stats
    monitor.start();
    let mut child = cmd.spawn().expect("Error: failed to run program");
    let success = child.wait().expect("Error: failed to run program");
    let stats = Stats::new(monitor.stop());

    // Signal potential errors
    if !success.success() {
        println!("Command {} returned with non-zero exit code", path);
    }
    stats
}

fn benchmark_shared<P: ExternalProgram>(path: &str, args: &str) -> Stats {
    let mut monitor = Monitor::new();
    let program = P::load(path);
    program.init(args);

    // Measurement
    monitor.start();
    program.run();
    let stats = Stats::new(monitor.stop());

    // Cleanup & display
    program.cleanup();
    stats
}

/// This function set up signal handlers, so that bench can exit gracefully on SIGINT and
/// SIGTERM.
fn set_signal_handler() {
    set_handler(|| {
        command::kill_all_childs();
        exit(0);
    }).expect("Could not set signal handler.");
}
