//! Commands
//!
//! This modules handle spawning child processes from a shell command while ensuring that those
//! processes are correctly terminated on exit.

use lazy_static::lazy_static;
use nix::sys::signal::{kill, Signal};
use nix::unistd::Pid;
use shellwords;
use std::collections::HashSet;
use std::process::{Child, Command, ExitStatus};
use std::sync::Mutex;

lazy_static! {
    static ref PROCESSES: Mutex<HashSet<i32>> = Mutex::new(HashSet::new());
}

/// A wrapper around std::process::Child that is killed when dropped.
///
/// This is especially usefull for ensuring that the child process is killed when the main process
/// receive a SIGKILL or equivalent.
pub struct Subprocess {
    process: Child,
}

impl Subprocess {
    pub fn wait(&mut self) -> std::io::Result<ExitStatus> {
        let pid = self.process.id();
        let result = self.process.wait();
        let mut process = PROCESSES.lock().unwrap();
        process.remove(&(pid as i32));
        result
    }
}

impl Drop for Subprocess {
    fn drop(&mut self) {
        self.process.kill().ok();
    }
}

pub struct Process {
    process: Command,
}

impl Process {
    pub fn new(path: &str, args: &str) -> Self {
        let mut cmd = Command::new(path);
        cmd.args(shellwords::split(args).unwrap());
        Process { process: cmd }
    }

    pub fn spawn(&mut self) -> std::io::Result<Subprocess> {
        self.process.spawn().map(|process| {
            let pid = process.id();
            let mut processes = PROCESSES.lock().unwrap();
            processes.insert(pid as i32);
            Subprocess { process }})
    }
}

/// Kill all runing childs.
pub fn kill_all_childs() {
    let processes = PROCESSES.lock().unwrap();
    for process_id in processes.iter() {
        kill(Pid::from_raw(*process_id), Signal::SIGTERM).expect("Failed to kill child processes");
    }
}
