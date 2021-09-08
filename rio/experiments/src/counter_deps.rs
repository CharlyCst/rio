//! Counter with dependencies

use clap::Clap;
use std::ptr::write_volatile;

use rio::task;
use rio::{go, Data, ExecutorId, Runtime};

type DummyData = Data<()>;

static mut N: u64 = 1000;
const DATA_SHIFT: usize = 7; // 1 << 7 = 128 data objects
const N_DATA: usize = 1 << DATA_SHIFT;

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

    let data = (0..N_DATA)
        .map(|_| Data::new(()))
        .collect::<Vec<DummyData>>();
    let rng = RandomNumberGenerator::new();

    go(nb_threads, map, (args, data, rng), count);
}

// ————————————————————————————————— Utils —————————————————————————————————— //

/// Build a closure representing the mapping from tasks to executor.
fn get_mapping(args: &Args) -> impl Fn(usize) -> ExecutorId + Clone {
    let nb_threads = args.nb_threads;
    move |task_id| ExecutorId::new((task_id % nb_threads) as u32)
}

/// Simple Xorshift pseudo-random number generator
/// See Marsaglia, George (July 2003). "Xorshift RNGs". Journal of Statistical Software. Vol. 8 (Issue 14).
#[derive(Clone)]
struct RandomNumberGenerator {
    state: usize,
}

impl RandomNumberGenerator {
    fn new() -> Self {
        Self { state: 0x92d68ca2 }
    }
}

impl RandomNumberGenerator {
    #[inline]
    fn rand(&mut self) -> usize {
        let mut x = self.state;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.state = x;
        x
    }
}

/// Return three references to objects of a vector. If an index is given more than once, None is
/// returned instead.
#[inline]
fn get_three<'a, T>(
    vec: &'a mut [T],
    a: usize,
    b: usize,
    c: usize,
) -> (&'a mut T, Option<&'a mut T>, Option<&'a mut T>) {
    // Safety: We explicitely check for equality of the indexes to prevent returning two
    // mutable references to the same object. We also take care of binding the lifetime of the
    // resulting references to the vector's one.
    unsafe {
        let first = &mut *((&mut vec[a]) as *mut T);
        let second = if b == a {
            None
        } else {
            Some(&mut *((&mut vec[b]) as *mut T))
        };
        let third = if c == a || c == b {
            None
        } else {
            Some(&mut *((&mut vec[c]) as *mut T))
        };
        (first, second, third)
    }
}

// —————————————————————————— Task Based Program ———————————————————————————— //

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

#[inline]
fn counter_1(_a: &()) {
    counter();
}

#[inline]
fn counter_2(_a: &(), _b: &()) {
    counter();
}

#[inline]
fn counter_3(_a: &(), _b: &(), _c: &mut ()) {
    counter();
}

fn count(mut rt: Runtime, args: (Args, Vec<DummyData>, RandomNumberGenerator)) {
    let (args, mut data, mut rng) = args;
    for _ in 0..args.n_tasks {
        let x = rng.rand();
        let idx_1 = x % N_DATA;
        let idx_2 = (x >> DATA_SHIFT) % N_DATA;
        let idx_3 = (x >> (2 * DATA_SHIFT)) % N_DATA;

        let (a, b, c) = get_three(&mut data, idx_1, idx_2, idx_3);
        match (b, c) {
            (None, None) => {
                task! {
                    rt, counter_1,
                    R: a;
                };
            }
            (Some(b), None) => {
                task! {
                    rt, counter_2,
                    R: a, b;
                }
            }
            (None, Some(b)) => {
                task! {
                    rt, counter_2,
                    R: a, b;
                }
            }
            (Some(b), Some(c)) => {
                task! {
                    rt, counter_3,
                    R: a, b;
                    RW: c;
                };
            }
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
