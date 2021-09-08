use crate::monitor::Counters;
use serde::Serialize;
use serde_json;
use std::fmt;

#[derive(Serialize)]
pub struct Stats {
    cycles: u64,
    cpu_usage: f64,
    instr_per_cycle: f64,
    cache_miss_rate: f64,
    execution_time: f64, // in seconds
    frequency_scaling: f64,
}

impl Stats {
    pub fn new(counters: Counters) -> Self {
        Self {
            cycles: counters.cycles,
            instr_per_cycle: counters.instructions as f64 / counters.cycles as f64,
            cpu_usage: counters.task_clock as f64 / counters.wall_clock as f64,
            cache_miss_rate: counters.cache_misses as f64 / counters.cache_references as f64,
            execution_time: counters.wall_clock as f64 / 1_000_000_000.,
            frequency_scaling: counters.cycles as f64 / counters.ref_cycles as f64,
        }
    }

    pub fn json(&self) -> String {
        serde_json::to_string(self).unwrap()
    }
}

impl fmt::Display for Stats {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "cycles:\t\t{}\nfreq/max freq:\t{:.2}\ninstr/cycles:\t{:.2}\ncpu usage:\t{:.2}\ncache miss:\t{:.2}%\nexec time:\t{:.2}s",
            self.cycles, self.frequency_scaling,self.instr_per_cycle, self.cpu_usage, self.cache_miss_rate * 100.,self.execution_time
        )
    }
}
