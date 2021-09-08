/// # Program Loader
///
/// This module is responsible for defining a foreign interface (C and Rust are supported) and
/// loading the program as a shared object using `dlopen`.
use crate::cli::{CArgs, RustArgs};
use dlopen::wrapper::{Container, WrapperApi};
use std::ffi::{OsStr, OsString};
use std::os::raw::{c_char, c_int};

/// The interface to the external program ABI.
pub trait ExternalProgram {
    /// Load the program at `path`.
    fn load<P: AsRef<OsStr>>(path: P) -> Self;

    /// Call the initialization function of the loaded program.
    /// The arguments will be parsed and made available in the most natural form for all
    /// supported languages.
    fn init(&self, args: &str);

    /// Run the actual job to benchmark.
    fn run(&self);

    /// A hook for giving a chance to the loaded program to release its resources.
    fn cleanup(&self);
}

// —————————————————————————— Language interfaces ——————————————————————————— //

#[derive(WrapperApi)]
struct CBenchmarkAPI {
    init: unsafe extern "C" fn(argc: c_int, argv: *const *const c_char),
    run: unsafe extern "C" fn(),
    cleanup: unsafe extern "C" fn(),
}

#[derive(WrapperApi)]
struct RustBenchmarkApi {
    init_rust: unsafe fn(args: &Vec<OsString>),
    run: unsafe fn(),
    cleanup: unsafe fn(),
}

pub struct CProgram {
    program: Container<CBenchmarkAPI>,
}

pub struct RustProgram {
    program: Container<RustBenchmarkApi>,
}

// ————————————————————————————— C Implementation ——————————————————————————— //

impl ExternalProgram for CProgram {
    fn load<P: AsRef<OsStr>>(path: P) -> Self {
        let program = unsafe {
            Container::<CBenchmarkAPI>::load(path).expect("Could not load dynamic library")
        };
        Self { program }
    }

    fn init(&self, args: &str) {
        let c_args = CArgs::new(args);
        unsafe {
            self.program.init(c_args.argc(), c_args.argv());
        }
    }

    fn run(&self) {
        unsafe {
            self.program.run();
        }
    }

    fn cleanup(&self) {
        unsafe {
            self.program.cleanup();
        }
    }
}

// ——————————————————————————— Rust Implementation —————————————————————————— //

impl ExternalProgram for RustProgram {
    fn load<P: AsRef<OsStr>>(path: P) -> Self {
        let program = unsafe {
            Container::<RustBenchmarkApi>::load(path).expect("Could not load dynamic library")
        };
        Self { program }
    }

    fn init(&self, args: &str) {
        let rust_args = RustArgs::new(args);
        unsafe {
            self.program.init_rust(rust_args.args());
        }
    }

    fn run(&self) {
        unsafe {
            self.program.run();
        }
    }

    fn cleanup(&self) {
        unsafe {
            self.program.cleanup();
        }
    }
}
