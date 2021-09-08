/* Matrix Multiplication
 *
 * A simple C program performing a matrix multiplication.
 **/
#include <stdio.h>
#include <stdlib.h>

int n = 64; // matrix size
double *a = NULL;
double *b = NULL;
double *c = NULL;

void init(int argc, char *argv[]) {
  if (argc > 1) {
    n = atoi(argv[1]);
  }
  int nn = n * n;

  // Allocate matrices
  a = calloc(nn, sizeof(double));
  b = calloc(nn, sizeof(double));
  c = calloc(nn, sizeof(double));
  if (a == NULL || b == NULL || c == NULL) {
    printf("Failed to allocate matrix of size %d * %d\n", n, n);
    exit(1);
  }

  // Initialize A and B
  for (int j = 0; j < n; j++) {
    for (int i = 0; i < n; i++) {
      b[i + j * n] = (i + j);
      if (i == j) {
        a[i + j * n] = 2;
      }
    }
  }
}

// Compute C = A B
void run() {
  for (int j = 0; j < n; j++) {
    for (int i = 0; i < n; i++) {
      for (int k = 0; k < n; k++) {
        c[i + j * n] += a[i + k * n] * b[k + j * n];
      }
    }
  }
}

void cleanup() {
  free(a);
  free(b);
  free(c);
}

int main(int argc, char *argv[]) {
  init(argc, argv);
  run();
  cleanup();
  return 0;
}
