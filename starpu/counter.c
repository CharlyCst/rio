/*
 * A simple program where each tasks consists in counting up to N.
 */

#include <starpu.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

uint64_t N = 1000;
uint64_t N_TASKS = 1000;

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

static struct starpu_codelet count_codelet = {
    .cpu_funcs = {cpu_count},
    .nbuffers = 0,
    .modes = {},
    .name = "count",
};

void init(int argc, char *argv[]) {
  int arg = 0;
  for (int i = 1; i < argc; i++) {
    int value = atoi(argv[i]);
    if (arg == 0) {
      N_TASKS = value;
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
}

void cleanup() {
    starpu_shutdown();
}

void run() {
  int ret;
  for (int i = 0; i < N_TASKS; i++) {
    struct starpu_task *task = starpu_task_create();
    task->cl = &count_codelet;
    ret = starpu_task_submit(task);
    STARPU_CHECK_RETURN_VALUE(ret, "starpu_task_submit");
  }
  starpu_task_wait_for_all();
}

int main(int argc, char *argv[]) {
  init(argc, argv);
  run();
  cleanup();
}
