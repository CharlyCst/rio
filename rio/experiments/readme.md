# Experiments

The crate in which live the experiments using Rio used for benchmarking.

**Experiments**:

- **mm**: A matrix multiplication.
- **mm_mkl**: A matrix multiplication using the MKL kernels.
- **mm_counter**: A matrix multiplication where tasks have been replaced with
  compute-bound tasks consisting in incrementing a counter.
- **lu**: A LU factorization without pivoting.
- **lu_mkl**: A LU factorization without pivoting using the MKL kernels.
- **lu_counter**: A LU factorization without pivoting in which tasks have been replaced by compute-bound tasks consisting in incrementing a counter.
- **couter**: Independent tasks consisting in incrementing a counter and
  storing its value to memory.
- **counter_deps**: Same as 'counter', but with random dependencies.

