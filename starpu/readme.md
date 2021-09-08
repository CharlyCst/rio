# StarPU

A collection of algorithms implemented on top of StarPU.

Algorithms:

- **mm_counters**: Matrix multiplication in which tasks have been replaced by
  compute-bound tasks consisting in incrementing a counter.
- **lu_counter**: An LU factorization without pivoting in which tasks have been
  replaced by compute-bound tasks consisting in incrementing a counter.
- **counter**: An experiment in which tasks consists in independent tasks
  incrementing a counter and storing its value to memory. This is intended to
  avoid pitfalls of memory locality effect on efficiency during benchmarks.
- **counter_deps**: Same as 'counter', but this time there are random
  dependencies between the tasks.

