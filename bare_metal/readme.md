# Bare Metal

A collections of single-threaded algorithms implemented without the use of any
runtime, used for evaluation of runtimes overhead.

Algorithms:

- **mm**: Matrix multiplication.
- **mm_tiled**: Matrix multiplication in which the computation is split in tasks.
- **mm_mkl**: Matrix multiplication on top of the MKL kernels.
- **mm_tiled_mkl**: Matrix multiplication on top of the MKL kernels splitting
  the computation in tasks.
- **mm_counters**: Matrix multiplication in which  tasks have been replaced by
  compute-bound tasks consisting in incrementing a counter.
- **lu_mkl**: An LU factorization without pivoting using the MKL kernel.
- **lu_tiled_mkl**: An LU factorization using a tiled algorithm with MKL kernels.
- **lu_counter**: An LU factorization using a tiled algorithm but replacing
  actual kernels with a compute-bound task consisting in incrementing a
  counter.
- **counter**: A program consisting in tasks incrementing a counter and storing
  its value in memory.

