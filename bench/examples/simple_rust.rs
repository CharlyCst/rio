use std::ffi::OsString;
use std::thread;
use std::time::Duration;

const NB_ITERATIONS: u64 = 30000000;

fn main() {
    run();
}

#[no_mangle]
pub fn init_rust(_args: &Vec<OsString>) {}

#[no_mangle]
pub fn run() {
    let mut u: u64 = 0;
    for k in 0..NB_ITERATIONS {
        u = (u + k) % NB_ITERATIONS;
    }
    println!("u = {}", u);
    thread::sleep(Duration::from_secs(1));
}

#[no_mangle]
pub fn cleanup() {}
