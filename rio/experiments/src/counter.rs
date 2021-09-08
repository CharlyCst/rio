//! Counter

use std::ptr::write_volatile;
use clap::Clap;

use rio::task;
use rio::{go, ExecutorId, Runtime};

static mut N: u64= 1000;

// —————————————————————————————— Executable ———————————————————————————————— //

fn main() {
    let args = Args::parse();
    let nb_threads = args.nb_threads;

    // The mapping between tasks and executors
    let map = get_mapping(&args);

    // Safe, at this point there is a single thread in the program
    unsafe {
        N = args.n;
    }

    go(nb_threads, map, args, count);
}

// ————————————————————————————————— Utils —————————————————————————————————— //

/// Build a closure representing the mapping from tasks to executor.
fn get_mapping(args: &Args) -> impl Fn(usize) -> ExecutorId + Clone {
    let nb_threads = args.nb_threads;
    move |task_id| ExecutorId::new((task_id % nb_threads) as u32)
}

// —————————————————————————— Task Based Program ———————————————————————————— //

fn counter() {
    let mut c = 0_u64;

    // Safe, there are only reads on this global value
    let n = unsafe {N};

    for i in 0..n {
        // Safe, c is alive and properly aligned.
        unsafe {
            write_volatile(&mut c, i);
        }
    }
}

fn count(mut rt: Runtime, args: Args) {
    for _ in 0..args.n_tasks {
        task! {
            rt, counter
        }
    }
}

// —————————————————————————————————— CLI ——————————————————————————————————— //

/// Counter
///
/// An application performing a compute bound task.
#[derive(Clap, Clone)]
struct Args {
    #[clap(default_value = "1000")]
    n_tasks: u64,

    #[clap(default_value = "1000")]
    n: u64,

    #[clap(short, long, default_value = "2")]
    nb_threads: usize,

    #[clap(short, long)]
    debug: bool,

    #[clap(short, long)]
    verbose: bool,
}
