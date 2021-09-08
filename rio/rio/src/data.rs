//! # Data
//!
//! The `Data` struct represents a piece of data shared among worker threads, it is the piece
//! responsible for synchronization.  Because the runtime optimizes for low overhead on fine
//! grained tasks the synchronization must be efficient when dealing with huge number of tasks and
//! dependencies, ideally performing very little work when the current thread is not responsible
//! for executing the task. Avoiding a central synchronization point (such as in a master-workers)
//! model is also an explicit goal.
//!
//! In the proposed design all the threads have symmetric roles, they all maintain a local data
//! structure tracking read an write access but still have to perform point-to-point
//! synchronization when performing a task.
//!
//! The `Data` object has the following structure:
//! - local:  a local copy of the past reads and writes.
//! - shared: a shared state among all workers, itself composed of:
//!   + data:    a pointer to the data.
//!   + condvar: a conditional variable used for synchronization.
//!   + inner:   the record of last reads and writes that have been executed, protected behind a
//!              lock.
//!
//! Tasks are represented by a `TaskId`, a unique and monotonically increasing ID. This makes the
//! local and shared state very space efficient (two `usize`s) and enable fast checking and
//! maintenance of availability status.

use std::cell::UnsafeCell;
use std::default::Default;
use std::mem::drop;
use std::ops::{Deref, DerefMut, Drop};
use std::sync::{Arc, Condvar, Mutex};

// —————————————————————————————————— Data —————————————————————————————————— //

/// A unique Task identifier.
#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub struct TaskId(pub(crate) usize);

/// The structure holding the data and responsible for synchronization.
pub struct Data<T> {
    local: DataLocalState,
    shared: Arc<DataSharedState<T>>,
}

#[derive(Clone)]
struct DataLocalState {
    last_registered_write: usize,
    nb_reads_since_write: usize,
    // A data is dirty if it has been written to since last time got access to it
    dirty: bool,
}

struct DataSharedState<T> {
    inner: Mutex<DataLockedState>,
    condvar: Condvar,
    data: UnsafeCell<T>,
}

struct DataLockedState {
    last_executed_write: usize,
    nb_reads_since_write: usize,
    nb_threads_waiting: usize,
}

// Safety: The data is protected by tracking read & write accesses.
unsafe impl<T: Sync> Sync for DataSharedState<T> {}

impl<T> Data<T> {
    pub fn new(data: T) -> Self {
        let local = DataLocalState {
            last_registered_write: 0,
            nb_reads_since_write: 0,
            dirty: false,
        };
        let shared = Arc::new(DataSharedState {
            inner: Mutex::new(DataLockedState {
                last_executed_write: 0,
                nb_reads_since_write: 0,
                nb_threads_waiting: 0,
            }),
            condvar: Condvar::new(),
            data: UnsafeCell::new(data),
        });
        Self { local, shared }
    }

    fn write_is_ready(&self, inner: &DataLockedState) -> bool {
        let state = &self.local;

        // A write is ready if all the previous reads and writes have been executed.
        let reads_are_done = inner.nb_reads_since_write == state.nb_reads_since_write;
        let writes_are_done = inner.last_executed_write == state.last_registered_write;
        reads_are_done && writes_are_done
    }

    fn read_is_ready(&self, inner: &DataLockedState) -> bool {
        // A read is ready if all the previous writes have been executed.
        inner.last_executed_write == self.local.last_registered_write
    }

    /// Declare a read task on the data, without executing it.
    ///
    /// # Safety
    ///
    /// This function affects the local state of the data container used for synchronization
    /// between threads, misuses may result in synchronization error and potentially data races.
    ///
    /// Each thread should call this function exactly once per read task on the data container.
    pub unsafe fn declare_read(&mut self) {
        self.local.nb_reads_since_write += 1;
    }

    /// Declare a write task on the data, without executing it.
    ///
    /// # Safety
    ///
    /// This function affects the local state of the data container used for synchronization
    /// between threads, misuses may result in synchronization error and potentially data races.
    ///
    /// Each thread should call this function exactly once per write task on the data container.
    pub unsafe fn declare_write(&mut self, task_id: TaskId) {
        self.local.last_registered_write = task_id.0;
        self.local.nb_reads_since_write = 0;
        self.local.dirty = true;
    }

    /// Get a reference to the data, in read-only mode.
    /// If the read is considered as ready (all the previous writes have been executed) the
    /// operation returns immediately (if there is no contention on the shared lock), otherwise
    /// the thread is paused until the desired write is marked as done.
    ///
    /// # Safety
    ///
    /// Access to the data is granted only if all previous write tasks have been marked as
    /// terminated and no write task will be performed until this task terminated. This is ensured
    /// only if all threads correctly declare their tasks and maintain a local copy of the data
    /// state adequately. To ensure that all the above condition holds, this function should never
    /// be called directly but rather used through the `task!` macro.
    pub unsafe fn get_read(&mut self) -> Ref<'_, T> {
        // If the data has not been invalidated since last time we got access to it no need to
        // synchronize.
        if !self.local.dirty {
            return Ref(self);
        }

        let mut inner = self.shared.inner.lock().unwrap();

        // Data is ready
        if self.read_is_ready(&inner) {
            drop(inner);
            return Ref(self);
        }

        // Sleep until data is ready
        inner.nb_threads_waiting += 1;
        loop {
            inner = self.shared.condvar.wait(inner).unwrap();
            if self.read_is_ready(&inner) {
                inner.nb_threads_waiting -= 1;
                drop(inner);
                return Ref(self);
            }
        }
    }

    /// Get a reference to the data, in read-write mode.
    /// If the write is considered as ready (all the previous reads and writes have been executed)
    /// the operation returns immediately (if there is no contention on the shared lock), otherwise
    /// the thread is paused until required operations are marked as done.
    ///
    /// # Safety
    ///
    /// Access to the data is granted only if all previous read and write tasks have been marked as
    /// terminated and no read or write task will be performed until this task terminated. This is
    /// ensured only if all threads correctly declare their tasks and maintain a local copy of the
    /// data state adequately. To ensure that all the above condition holds, this function should
    /// never be called directly but rather used through the `task!` macro.
    pub unsafe fn get_write(&mut self, task_id: TaskId) -> RefMut<'_, T> {
        let mut inner = self.shared.inner.lock().unwrap();

        // Data is ready
        if self.write_is_ready(&inner) {
            drop(inner);
            return RefMut(self, task_id);
        }

        // Sleep until data is ready
        inner.nb_threads_waiting += 1;
        loop {
            inner = self.shared.condvar.wait(inner).unwrap();
            if self.write_is_ready(&inner) {
                inner.nb_threads_waiting -= 1;
                drop(inner);
                return RefMut(self, task_id);
            }
        }
    }

    /// Mark a read operation as terminated.
    /// The read declaration is performed by this function.
    ///
    /// # Safety
    ///
    /// This function must be called exactly once for each read operation executed by the thread on
    /// this data, failure to do so may result in synchronization error and data races.
    unsafe fn terminate_read(&mut self) {
        self.declare_read();
        self.local.dirty = false;
        let mut inner = self.shared.inner.lock().unwrap();

        // Update shared state & wake up waiting threads
        inner.nb_reads_since_write += 1;
        if inner.nb_threads_waiting > 0 {
            self.shared.condvar.notify_all();
        }
    }

    /// Mark a write operation as terminated.
    /// The write declaration is performed by this function.
    ///
    /// # Safety
    ///
    /// This function must be called exactly once for each write operation executed by the thread
    /// on this data, failure to do so may result in synchronization error and data races.
    unsafe fn terminate_write(&mut self, task_id: TaskId) {
        self.declare_write(task_id);
        self.local.dirty = false;
        let mut inner = self.shared.inner.lock().unwrap();

        // Update shared state & wake up waiting threads
        inner.last_executed_write = task_id.0;
        inner.nb_reads_since_write = 0;
        if inner.nb_threads_waiting > 0 {
            self.shared.condvar.notify_all();
        }
    }
}

impl<T> Clone for Data<T> {
    fn clone(&self) -> Self {
        Self {
            local: self.local.clone(),
            shared: self.shared.clone(),
        }
    }
}

impl<T> Default for Data<T>
where
    T: Default,
{
    fn default() -> Self {
        Self::new(T::default())
    }
}

// ————————————————————————————— Smart Pointers ————————————————————————————— //

/// A read-only smart pointer holding the data.
pub struct Ref<'data, T>(&'data mut Data<T>);

/// A read-write smart pointer holding the data.
pub struct RefMut<'data, T>(&'data mut Data<T>, TaskId);

impl<'data, T> Deref for Ref<'data, T> {
    type Target = T;

    fn deref(&self) -> &Self::Target {
        unsafe { &*self.0.shared.data.get() }
    }
}

impl<'data, T> Deref for RefMut<'data, T> {
    type Target = T;

    fn deref(&self) -> &Self::Target {
        unsafe { &*self.0.shared.data.get() }
    }
}

impl<'data, T> DerefMut for RefMut<'data, T> {
    fn deref_mut(&mut self) -> &mut Self::Target {
        unsafe { &mut *self.0.shared.data.get() }
    }
}

impl<'data, T> Drop for Ref<'data, T> {
    fn drop(&mut self) {
        // Safety: the destructor will run only once.
        unsafe { self.0.terminate_read() }
    }
}

impl<'data, T> Drop for RefMut<'data, T> {
    fn drop(&mut self) {
        // Safety: the destructor will run only once.
        unsafe { self.0.terminate_write(self.1) }
    }
}
