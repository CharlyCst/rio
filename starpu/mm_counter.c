/*
 * A simple matrix multiplication on top of StarPU
 */

#include <starpu.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

// Default values
static int N_REPEAT = 1;
static int N = 1000;
static int N_TILES = 24;

// Matricies
static double *A;
static double *B;
static double *C;

// Handles
static starpu_data_handle_t *A_h;
static starpu_data_handle_t *B_h;
static starpu_data_handle_t *C_h;

static void register_matrices() {
  A_h = calloc(N_TILES * N_TILES, sizeof(starpu_data_handle_t));
  B_h = calloc(N_TILES * N_TILES, sizeof(starpu_data_handle_t));
  C_h = calloc(N_TILES * N_TILES, sizeof(starpu_data_handle_t));

  for (int i = 0; i < N_TILES; i++) {
    for (int j = 0; j < N_TILES; j++) {
      starpu_variable_data_register(&A_h[i + j * N_TILES], 0, (uintptr_t)NULL,
                                    0);
      starpu_variable_data_register(&B_h[i + j * N_TILES], 0, (uintptr_t)NULL,
                                    0);
      starpu_variable_data_register(&C_h[i + j * N_TILES], 0, (uintptr_t)NULL,
                                    0);
    }
  }
}

static void unregister_matrices() {
  for (int i = 0; i < N_TILES; i++) {
    for (int j = 0; j < N_TILES; j++) {
      starpu_data_unregister(A_h[i + j * N_TILES]);
      starpu_data_unregister(B_h[i + j * N_TILES]);
      starpu_data_unregister(C_h[i + j * N_TILES]);
    }
  }
}

static void cpu_count(void *handles[], void *arg) {
  // We use volatile to force the compiler to actually perform the writes
  volatile uint64_t c = 0;
  // The Rust version unroll by default, for fair comparison we force unrolling
  // in the C version too.
#pragma GCC unroll 8
  for (uint64_t i = 0; i < N; i++) {
    c = i;
  }
}

static struct starpu_codelet mm_codelet = {
    .cpu_funcs = {cpu_count},
    .nbuffers = 3,
    .modes = {STARPU_R, STARPU_R, STARPU_RW},
    .name = "mm",
};

void init(int argc, char *argv[]) {
  int arg = 0;
  for (int i = 1; i < argc; i++) {
    int value = atoi(argv[i]);
    if (arg == 0) {
      N_REPEAT = value;
      arg++;
    } else if (arg == 1) {
      N = value;
      arg++;
    } else {
      printf("Too much arguments\n");
      exit(1);
    }
  }

  // Initialize StarPU
  int ret = starpu_init(NULL);
  STARPU_CHECK_RETURN_VALUE(ret, "starpu_init");

  // Initialize matrices
  register_matrices();
}

void cleanup() {
  unregister_matrices();
  starpu_shutdown();
}

void run() {
  int ret;

  for (int repeat = 0; repeat < N_REPEAT; repeat++) {
    for (int i = 0; i < N_TILES; i++) {
      for (int j = 0; j < N_TILES; j++) {
        for (int k = 0; k < N_TILES; k++) {
          struct starpu_task *task = starpu_task_create();
          task->cl = &mm_codelet;
          task->handles[0] = A_h[i + k * N_TILES];
          task->handles[1] = B_h[k + j * N_TILES];
          task->handles[2] = C_h[i + j * N_TILES];
          ret = starpu_task_submit(task);
          // STARPU_CHECK_RETURN_VALUE(ret, "starpu_task_submit");
        }
      }
    }
  }
  starpu_task_wait_for_all();
}

int main(int argc, char *argv[]) {
  init(argc, argv);
  run();
  cleanup();
}
