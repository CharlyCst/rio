//! A simple LU factorization without pivoting simulating computation with counter increments.
//!
//! Three mappings are available:
//! - 2D block cyclic
//! - 1D block cyclic
//! - Round robin

use std::cell::UnsafeCell;
use std::default::Default;
use std::ptr::write_volatile;

use clap::Clap;

use rio::task;
use rio::{go, Data, ExecutorId, Runtime};

// Number of tiles in a row & column
// We usa a 32x30 matrix so that we can use a 24 threads 2D block cyclic mapping
const NB_TILES_ROW: usize = 30;
const NB_TILES_COL: usize = 32;
// Number of counter increments per tasks
static mut N: u64 = 1000;

type Tiles = [[Data<()>; NB_TILES_ROW]; NB_TILES_COL];

// —————————————————————————————— Entry Point ——————————————————————————————— //

fn main() {
    let args = Args::parse();
    let nb_threads = args.nb_threads;

    // Safety: there is only one active thread at this point
    unsafe {
        N = args.n as u64;
    }

    // The tiles
    let tiles = Default::default();

    if !args.block_2d && !args.block_1d {
        // Simple round-robin mapping
        let map = move |task_id| ExecutorId::new((task_id % nb_threads) as u32);

        // Start the computation
        go(nb_threads, map, (tiles, args.n_repeat), lu_fact_round_robin);
    } else {
        if args.block_1d {
            // 1D block cyclic mapping
            let map = move |(i, j): (usize, usize)| {
                ExecutorId::new(((i + j * NB_TILES_COL) % nb_threads) as u32)
            };

            // Start the computation
            go(
                nb_threads,
                map,
                (tiles, args.n_repeat),
                lu_fact_block_cyclic,
            );
        } else {
            assert_eq!(
                nb_threads, 24,
                "The two 2 block cyclic mapping assumes 24 threads"
            );

            // 2D block cyclic mapping
            let map = move |(i, j): (usize, usize)| ExecutorId::new(((i % 4) * 6 + j % 6) as u32);

            // Start the computation
            go(
                nb_threads,
                map,
                (tiles, args.n_repeat),
                lu_fact_block_cyclic,
            );
        };
    }
}

// ———————————————————————————————— Program ————————————————————————————————— //

fn lu_fact_block_cyclic(mut rt: Runtime<(usize, usize)>, args: (Tiles, usize)) {
    // For the sake of simplicity, the body of this function is unsafe. It access tiles from the
    // `TILE` matrix directly by mutable references, but this is fine as long as two references
    // to the same tile never live together
    let (tiles, n_repeat) = args;
    let tiles = UnsafeCell::new(tiles);
    let n = if NB_TILES_ROW < NB_TILES_COL {
        NB_TILES_ROW
    } else {
        NB_TILES_COL
    };
    unsafe {
        for _ in 0..n_repeat {
            for i in 0..n {
                // Triangular factorization
                let pivot_tile = get_mut(&tiles, i, i);
                task! {
                    rt, trfr,
                    map: (i, i);
                    RW: pivot_tile;
                }

                // Panel update
                for row in (i + 1)..NB_TILES_COL {
                    let tile = get_mut(&tiles, row, i);
                    task! {
                        rt, panel_update,
                        map: (row, i);
                        R: pivot_tile;
                        RW: tile;
                    }
                }

                // Triangular update
                for col in (i + 1)..NB_TILES_ROW {
                    let tile = get_mut(&tiles, i, col);
                    task! {
                        rt, trsm,
                        map: (i, col);
                        R: pivot_tile;
                        RW: tile;
                    }
                }

                // GEMM update
                for row in (i + 1)..NB_TILES_COL {
                    for col in (i + 1)..NB_TILES_ROW {
                        let a = get_mut(&tiles, row, i);
                        let b = get_mut(&tiles, i, col);
                        let c = get_mut(&tiles, row, col);
                        task! {
                            rt, gemm,
                            map: (row, col);
                            R: a, b;
                            RW: c;
                        }
                    }
                }
            }
        }
    }
}

fn lu_fact_round_robin(mut rt: Runtime, args: (Tiles, usize)) {
    // For the sake of simplicity, the body of this function is unsafe. It access tiles from the
    // `TILE` matrix directly by mutable references, but this is fine as long as two references
    // to the same tile never live together
    let (tiles, n_repeat) = args;
    let tiles = UnsafeCell::new(tiles);
    let n = if NB_TILES_ROW < NB_TILES_COL {
        NB_TILES_ROW
    } else {
        NB_TILES_COL
    };
    unsafe {
        for _ in 0..n_repeat {
            for i in 0..n {
                // Triangular factorization
                let pivot_tile = get_mut(&tiles, i, i);
                task! {
                    rt, trfr,
                    RW: pivot_tile;
                }

                // Panel update
                for row in (i + 1)..NB_TILES_COL {
                    let tile = get_mut(&tiles, row, i);
                    task! {
                        rt, panel_update,
                        R: pivot_tile;
                        RW: tile;
                    }
                }

                // Triangular update
                for col in (i + 1)..NB_TILES_ROW {
                    let tile = get_mut(&tiles, i, col);
                    task! {
                        rt, trsm,
                        R: pivot_tile;
                        RW: tile;
                    }
                }

                // GEMM update
                for row in (i + 1)..NB_TILES_COL {
                    for col in (i + 1)..NB_TILES_ROW {
                        let a = get_mut(&tiles, row, i);
                        let b = get_mut(&tiles, i, col);
                        let c = get_mut(&tiles, row, col);
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

// ————————————————————————————————— Utils —————————————————————————————————— //

/// Return a mutable reference to tile (i, j).
/// This function is unsafe, it is up to the caller to ensure that no two mutable references to the
/// same tile are alive at the same time. In addition, the lifetime is bond to `TILES`.
unsafe fn get_mut(tiles: &UnsafeCell<Tiles>, i: usize, j: usize) -> &mut Data<()> {
    &mut (&mut *tiles.get())[i][j]
}

// ———————————————————————————————— Tasks ——————————————————————————————————— //

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

/// Perform a triangular factorization on the tile.
fn trfr(_tile: &mut ()) {
    counter();
}

/// Update one of the tile bolow the pivot tile after it has been triangularized.
fn panel_update(_pivot_tile: &(), _tile: &mut ()) {
    counter();
}

/// Perform a triangular update.
fn trsm(_pivot_tile: &(), _tile: &mut ()) {
    counter();
}

fn gemm(_a: &(), _b: &(), _c: &mut ()) {
    counter();
}

// —————————————————————————————————— CLI ——————————————————————————————————— //

/// A LU factorization without pivoting.
#[derive(Clap, Clone)]
struct Args {
    /// Number of LU factorization
    #[clap(default_value = "1")]
    n_repeat: usize,

    /// Number of counter increments per task
    #[clap(default_value = "1000")]
    n: usize,

    #[clap(short, long, default_value = "2")]
    nb_threads: usize,

    /// 2D block cyclic mapping
    #[clap(long = "2d")]
    block_2d: bool,

    /// 1D block cyclic mapping
    #[clap(long = "1d")]
    block_1d: bool,

    #[clap(short, long)]
    debug: bool,

    #[clap(short, long)]
    verbose: bool,
}
