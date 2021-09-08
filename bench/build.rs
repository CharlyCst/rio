use std::process::Command;

const FILE_PATH: &'static str = "examples";
const BUILD_DIR: &'static str = "build";
const C_FILES: [&'static str; 2] = ["simple", "mm"];
const RUST_FILES: [&'static str; 1] = ["simple_rust"];
const CC: &'static str = "gcc";
const RUSTC: &'static str = "rustc";

fn main() {
    println!("cargo:rerun-if-changed={}", FILE_PATH);

    // Compile C files
    for file in &C_FILES {
        let c_file = file_path(file, "c");
        let out = output_path(file);
        let ret = Command::new(CC)
            .args(&["-shared", "-O3", "-fPIC", &c_file, "-o", &out])
            .status()
            .expect(&format!("Failed to build {}.c", file));
        if !ret.success() {
            panic(file, "c");
        }
    }

    // Compile Rust files
    for file in &RUST_FILES {
        let rust_file = file_path(file, "rs");
        let out = output_path(file);
        let ret = Command::new(RUSTC)
            .args(&["--crate-type=dylib", "-O", &rust_file, "-o", &out])
            .status()
            .expect(&format!("Failed to build {}.rs", file));
        if !ret.success() {
            panic(file, "rs");
        }
    }
}

fn file_path(file_name: &str, extension: &str) -> String {
    format!("./{}/{}.{}", FILE_PATH, file_name, extension)
}

fn output_path(file_name: &str) -> String {
    format!("./{}/{}.so", BUILD_DIR, file_name)
}

fn panic(file: &str, extension: &str) -> ! {
    panic!(
        "Failed to compile {}.{}, try `cargo build -vv` for more details",
        file, extension
    );
}
