//! Matrix Multiplication

use std::cell::UnsafeCell;
use std::default::Default;
use std::ptr::write_volatile;

use clap::Clap;

use rio::task;
use rio::{go, Data, ExecutorId, Runtime};

// Number of tiles in a row & column
const NB_TILES: usize = 24;
// Number of counter increments per tasks
static mut N: u64 = 1000;

type Tiles = [[Data<()>; NB_TILES]; NB_TILES];

// —————————————————————————————— Executable ———————————————————————————————— //

fn main() {
    let args = Args::parse();
    let nb_threads = args.nb_threads;
    let nb_repeats = args.n;

    // Safety: there is only one active thread at this point
    unsafe {
        N = args.nb_increments as u64;
    }

    // The mapping between tasks and executors
    let map = get_mapping(&args);

    // The matrix tiles
    let a = Default::default();
    let b = Default::default();
    let c = Default::default();

    go(nb_threads, map, (nb_repeats, a, b, c), matrix_mult);
}

// ————————————————————————————————— Utils —————————————————————————————————— //

/// Build a closure representing the mapping from tasks to executor.
fn get_mapping(args: &Args) -> impl Fn(usize) -> ExecutorId + Clone {
    let nb_threads = args.nb_threads;
    move |task_id| ExecutorId::new((((task_id - 1) / NB_TILES) % nb_threads) as u32)
}

/// Return a mutable reference to tile (i, j).
/// This function is unsafe, it is up to the caller to ensure that no two mutable references to the
/// same tile are alive at the same time. In addition, the lifetime is bond to `TILES`.
unsafe fn get_mut(tiles: &UnsafeCell<Tiles>, i: usize, j: usize) -> &mut Data<()> {
    &mut (&mut *tiles.get())[i][j]
}

// —————————————————————————— Task Based Program ———————————————————————————— //

fn matrix_mult(mut rt: Runtime, data: (usize, Tiles, Tiles, Tiles)) {
    let (nb_repeats, a, b, c) = data;

    let a = UnsafeCell::new(a);
    let b = UnsafeCell::new(b);
    let c = UnsafeCell::new(c);

    unsafe {
        for _ in 0..nb_repeats {
            for j in 0..NB_TILES {
                for i in 0..NB_TILES {
                    let c = get_mut(&c, i, j);
                    for k in 0..NB_TILES {
                        let a = get_mut(&a, i, k);
                        let b = get_mut(&b, k, j);
                        task! {
                            rt, gemm,
                            R: a, b;
                            RW: c;
                        }
                    }
                }
            }
        }
    }
}

fn gemm(_a: &(), _b: &(), _c: &mut ()) {
    counter();
}

fn counter() {
    let mut c = 0_u64;

    // Safe, there are only reads on this global value
    let n = unsafe { N };

    for i in 0..n {
        // Safe, c is alive and properly aligned.
        unsafe {
            write_volatile(&mut c, i);
        }
    }
}

// —————————————————————————————————— CLI ——————————————————————————————————— //

/// Matrix Multiplication
///
/// A small MM example using shared (i.e. protected by lock) data objects.
#[derive(Clap, Clone)]
struct Args {
    /// Number of runs
    #[clap(default_value = "1")]
    n: usize,

    /// Number of counter increments
    #[clap(default_value = "64")]
    nb_increments: usize,

    #[clap(short, long, default_value = "2")]
    nb_threads: usize,

    #[clap(short, long)]
    debug: bool,

    #[clap(short, long)]
    verbose: bool,
}
