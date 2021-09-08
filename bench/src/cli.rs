//! The CLI interface of bench

pub use clap::Clap;
use shellwords;
use std::ffi::{CString, OsString};
use std::os::raw::{c_char, c_int};

// ——————————————————————————————— Bench CLI ———————————————————————————————— //

/// A small benchmarking tool for linux built on top of perf_event.
///
/// Bench can operate either with executables or shared libraries.
///
/// When running with an executable the program is simply run with the provided
/// arguments.
///
/// When running with a shared library (.so) the -c (or -r) flag must be passed,
/// and the program must satisfy the following C interface:
///
/// void init(int argc, char *argv[]);
///
/// void run();
///
/// void cleanup();
///
/// `init` will be called first before starting performance counters and timer,
/// then `run` is called and its performance is measured, finally the statistics
/// are collected and `cleanup` is called before printing results and exiting.
/// A Rust interface is also available with the `-r` or `--rust` flag, onlu the
/// `init` function signature is changed for:
///
/// fn init_rust(args: &Vec<OsString>)
#[derive(Clap)]
pub struct Args {
    /// Path to the program to benchmark.
    pub path: String,

    /// Arguments passed down to the program.
    #[clap(short, long, default_value = " ")]
    pub args: String,

    /// Verbose output.
    #[clap(short, long)]
    pub verbose: bool,

    /// Shared library mode, with the C ABI
    #[clap(short, long)]
    pub c: bool,

    /// Shared library mode, use the Rust ABI instead of C
    #[clap(short, long)]
    pub rust: bool,

    /// Print results as JSON
    #[clap(short, long)]
    pub json: bool,
}

// ——————————————————————————— Host Programs CLI ———————————————————————————— //

pub struct CArgs {
    argc: c_int,
    argv: *const *const c_char,
    _args: Vec<CString>,
    _args_ptr: Vec<*const c_char>,
}

pub struct RustArgs {
    args: Vec<OsString>,
}

impl CArgs {
    // We could also implement the "From" trait
    /// Convert a string to a list of C arguments.
    pub fn new(args: &str) -> Self {
        let mut c_args = vec![CString::new("bench_target").unwrap()];
        c_args.extend(
            shellwords::split(args)
                .unwrap()
                .into_iter()
                .map(|arg| CString::new(arg).unwrap()),
        );
        let argv = c_args
            .iter()
            .map(|arg| arg.as_ptr())
            .collect::<Vec<*const c_char>>();
        let argc = argv.len() as c_int;
        Self {
            argc,
            argv: argv.as_ptr(),
            _args: c_args,
            _args_ptr: argv,
        }
    }

    pub fn argc(&self) -> c_int {
        self.argc
    }

    pub fn argv(&self) -> *const *const c_char {
        self.argv
    }
}

impl RustArgs {
    pub fn new(args: &str) -> Self {
        let mut rust_args = vec!["bench_target".into()];
        rust_args.extend(
            shellwords::split(args)
                .unwrap()
                .iter()
                .map(|arg| arg.into()),
        );
        Self { args: rust_args }
    }

    pub fn args(&self) -> &Vec<OsString> {
        &self.args
    }
}
