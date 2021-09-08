use super::data::TaskId;
use crossbeam::thread;

// ————————————————————————————————— Runtime ———————————————————————————————— //

#[derive(PartialEq, Eq, Clone, Copy)]
pub struct ExecutorId {
    pub thread_id: u32,
}

impl ExecutorId {
    pub fn new(thread_id: u32) -> Self {
        Self { thread_id }
    }
}

/// A trait representing a mapping, automatically implemented for closures satisfying the
/// prototype. The default argument type is `usize` and corresponds to the task ID, but custom
/// arguments can be used.
///
/// # Safety
///
/// Data access synchronization rely on the determinism of the mapping function, failing to produce
/// deterministic outputs may result in fauly synchronization and potentially data races.
pub trait Mapping<Args = usize>: FnMut(Args) -> ExecutorId + Send {}

impl<T, Args> Mapping<Args> for T where T: FnMut(Args) -> ExecutorId + Send {}

/// Create a simple mapping, attributing tasks among `nb_threads` in a round robin fashion.
pub fn get_round_robin_mapping(nb_threads: u32) -> impl Mapping + Clone {
    move |task_id: usize| ExecutorId {
        thread_id: ((task_id) % (nb_threads as usize)) as u32,
    }
}

/// A thread-local data structure used to decide what tasks to execute on that thread.
pub struct Runtime<'map, Args = usize> {
    executor_id: ExecutorId,
    task_counter: usize,
    map: Box<dyn Mapping<Args> + 'map>,
}

/// Represents the ownership of a task.
/// The owner is the only thread that has to execute the task.
pub enum TaskOwnership {
    Owner,
    NotOwner,
}

impl<'map, Args> Runtime<'map, Args> {
    pub fn new(thread_id: u32, map: impl Mapping<Args> + 'map) -> Self {
        Self {
            executor_id: ExecutorId { thread_id },
            task_counter: 0,
            map: Box::new(map),
        }
    }

    /// Given the arguments to the mapping function, return the next task ID and wether the current
    /// thread has ownership of the task.
    ///
    /// # Safety
    ///
    /// This function or `next_task` should be called exactly once per task (for each thread).
    /// Instead of calling the function directly, the `task!` macro is provided to ensure correct
    /// usage.
    pub unsafe fn next_task_args(&mut self, args: Args) -> (TaskId, TaskOwnership) {
        self.task_counter += 1;
        let task_id = TaskId(self.task_counter);
        let ownership = if (self.map)(args) == self.executor_id {
            TaskOwnership::Owner
        } else {
            TaskOwnership::NotOwner
        };

        (task_id, ownership)
    }
}

impl <'map> Runtime<'map, usize> {
    /// Return the next task ID and whether the current thread has ownership of the task.
    ///
    /// # Safety
    ///
    /// This function or `next_task_args` should be called exactly once per task (for each thread).
    /// Instead of calling the function directly, the `task!` macro is provided to ensure correct
    /// usage.
    pub unsafe fn next_task(&mut self) -> (TaskId, TaskOwnership) {
        self.next_task_args(self.task_counter + 1)
    }
}

/// Start the computation on `nb_threads` threads.
///
/// Each thread will execute the given function, but tasks declared with the `task!` macro will
/// only be executed by the thread mapped to that task by the mapping function.
pub fn go<'computation, Map, Args, T>(
    nb_threads: usize,
    map: Map,
    args: Args,
    fun: fn(Runtime<'computation, T>, Args),
) where
    Map: Mapping<T> + Clone + 'computation,
    Args: Send + Clone + 'computation,
{
    // The threads are scoped, they are guaranteed to terminate before `thread::scope` returns.
    thread::scope(|scope| {
        for thread_id in 0..nb_threads {
            // Each thread receives its own copy of the mapping function, arguments and runtime
            // object.
            let map = map.clone();
            let args = args.clone();
            let rt = Runtime::<'computation>::new(thread_id as u32, map);

            // Spawn the thread
            scope
                .builder()
                .name(format!("T{}", thread_id))
                .spawn(move |_| fun(rt, args))
                .unwrap();
        }
    })
    .expect("One of the workers panicked");
}
