//! Monitor
//!
//! A module to collect statistics about the program running time.
use perf_event::events::{Hardware, Software};
use perf_event::{Builder, CountAndTime, Counter};
use std::time::Instant;

/// Measure statistics about the program execution.
pub struct Monitor {
    cycles: Counter,
    ref_cycles: Counter,
    instructions: Counter,
    task_clock: Counter,
    cache_misses: Counter,
    cache_references: Counter,
    start_time: Instant,
}

/// Raw counts of events collected during program execution program execution.
///
/// When the not enought counters are available on the hardware the counts are
/// estimations based on the time the counter was active.
pub struct Counters {
    /// Total number of cycles.
    pub cycles: u64,
    /// Total number of cycles, not affected by frequency scaling.
    pub ref_cycles: u64,
    /// Total number of instructions executed.
    pub instructions: u64,
    /// Total task clock, the sum of active time of all CPUs, in nano seconds.
    pub task_clock: u64,
    /// Wall clock time, in nano seconds.
    pub wall_clock: u64,
    /// Total cache misses, usually only last level caches are counted.
    pub cache_misses: u64,
    /// Total cache access, usually only last level caches are counted.
    pub cache_references: u64,
}

impl Monitor {
    pub fn new() -> Self {
        let cycles = Builder::new()
            .kind(Hardware::CPU_CYCLES)
            .inherit(true)
            .build()
            .expect("Failed to create cycles monitor");
        let ref_cycles = Builder::new()
            .kind(Hardware::REF_CPU_CYCLES)
            .inherit(true)
            .build()
            .expect("Failed to create reference cycles monitor");
        let instructions = Builder::new()
            .kind(Hardware::INSTRUCTIONS)
            .inherit(true)
            .build()
            .expect("Failed to create instructions monitor");
        let task_clock = Builder::new()
            .kind(Software::TASK_CLOCK)
            .inherit(true)
            .build()
            .expect("Failed to create task_clock monitor");
        let cache_misses = Builder::new()
            .kind(Hardware::CACHE_MISSES)
            .inherit(true)
            .build()
            .expect("Failed to create cache misses monitor");
        let cache_references = Builder::new()
            .kind(Hardware::CACHE_REFERENCES)
            .inherit(true)
            .build()
            .expect("Failed to create cache references monitor");
        Self {
            cycles,
            ref_cycles,
            instructions,
            task_clock,
            cache_misses,
            cache_references,
            start_time: Instant::now(),
        }
    }

    /// Start monitoring events.
    pub fn start(&mut self) {
        self.start_time = Instant::now();
        self.task_clock
            .enable()
            .expect("Failed to start task_clock");
        self.cycles.enable().expect("Failed to start cycles");
        self.ref_cycles
            .enable()
            .expect("Failed to start reference cyles");
        self.instructions
            .enable()
            .expect("Failed to start instructions");
        self.cache_references
            .enable()
            .expect("Failed to start cache references");
        self.cache_misses
            .enable()
            .expect("Failed to start cache misses");
    }

    /// Stop moitoring events and return the collected statistics.
    pub fn stop(&mut self) -> Counters {
        // Stop counters
        let elapsed = self.start_time.elapsed().as_nanos();
        self.task_clock
            .disable()
            .expect("Failed to stop task_clock");
        self.cycles.disable().expect("Failed to stop cycles");
        self.instructions
            .disable()
            .expect("Failed to stop instructions");
        self.cache_references
            .disable()
            .expect("Failed to disable cache references");
        self.cache_misses
            .disable()
            .expect("Failes to disable cache misses");
        // Read counts and running times
        let task_clock = self
            .task_clock
            .read_count_and_time()
            .expect("Could not read task_clock");
        let cycles = self
            .cycles
            .read_count_and_time()
            .expect("Could not read cycles");
        let ref_cycles = self
            .ref_cycles
            .read_count_and_time()
            .expect("Could not read reference cycles");
        let instructions = self
            .instructions
            .read_count_and_time()
            .expect("Could not read instructions");
        let cache_references = self
            .cache_references
            .read_count_and_time()
            .expect("Could not read cache references");
        let cache_misses = self
            .cache_misses
            .read_count_and_time()
            .expect("Could not read cache misses");
        // Estimate real counts
        let task_clock = estimate_real_count(task_clock);
        let cycles = estimate_real_count(cycles);
        let ref_cycles = estimate_real_count(ref_cycles);
        let instructions = estimate_real_count(instructions);
        let cache_misses = estimate_real_count(cache_misses);
        let cache_references = estimate_real_count(cache_references);
        Counters {
            cycles,
            ref_cycles,
            instructions,
            task_clock,
            cache_misses,
            cache_references,
            wall_clock: elapsed as u64,
        }
    }
}

fn estimate_real_count(cat: CountAndTime) -> u64 {
    (cat.count as u128 * cat.time_enabled as u128 / cat.time_running as u128) as u64
}
