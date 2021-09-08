/*
 * A simple program where each tasks consists in counting up to N.
 */

#include <starpu.h>
#include <starpu_task.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static uint64_t N = 1000;
static uint64_t N_TASKS = 1000;

const uint64_t DATA_SHIFT = 7; // 1 << 7 = 128 data objects
const uint64_t N_DATA = 1 << DATA_SHIFT;

static starpu_data_handle_t *H;

// ————————————————————————————————— Utils —————————————————————————————————— //

typedef struct random_number_generator_t {
  uint64_t state;
} random_number_generator_t;

random_number_generator_t rng_new() {
  random_number_generator_t rng;
  rng.state = 0x92d68ca2;
  return rng;
}

inline uint64_t rng_next(random_number_generator_t *rng) {
  uint64_t x = rng->state;
  x ^= x << 13;
  x ^= x >> 7;
  x ^= x << 17;
  rng->state = x;
  return x;
}

// ———————————————————————————————— Program ————————————————————————————————— //

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

static struct starpu_codelet count1_codelet = {
    .cpu_funcs = {cpu_count},
    .nbuffers = 1,
    .modes = {STARPU_R},
    .name = "count1",
};

static struct starpu_codelet count2_codelet = {
    .cpu_funcs = {cpu_count},
    .nbuffers = 2,
    .modes = {STARPU_R, STARPU_R},
    .name = "count2",
};

static struct starpu_codelet count3_codelet = {
    .cpu_funcs = {cpu_count},
    .nbuffers = 3,
    .modes = {STARPU_R, STARPU_R, STARPU_RW},
    .name = "count3",
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

  // register dummy data
  H = calloc(N_DATA, sizeof(starpu_data_handle_t));
  for (int i = 0; i < N_DATA; i++) {
    starpu_variable_data_register(&H[i], STARPU_MAIN_RAM, (uintptr_t)NULL, 0);
  }
}

void cleanup() { starpu_shutdown(); }

void run() {
  int ret;
  random_number_generator_t rng = rng_new();
  for (int i = 0; i < N_TASKS; i++) {
    uint64_t x = rng_next(&rng);
    uint64_t idx_1 = x % N_DATA;
    uint64_t idx_2 = (x >> DATA_SHIFT) % N_DATA;
    uint64_t idx_3 = (x >> (2 * DATA_SHIFT)) % N_DATA;

    // Prepare the task. Depending on the indices (choosen randomly) the task
    // can have one, two or three dependencies, as a given data object is never
    // used more than once.
    struct starpu_task *task = starpu_task_create();
    if (idx_1 == idx_2) {
      if (idx_1 == idx_3) {
        task->cl = &count1_codelet;
        task->handles[0] = H[idx_1];
      } else {
          task->cl = &count2_codelet;
          task->handles[0] = H[idx_1];
          task->handles[1] = H[idx_3];
      }
    } else {
        if (idx_1 == idx_3 || idx_2 == idx_3) {
            task->cl = &count2_codelet;
            task->handles[0] = H[idx_1];
            task->handles[1] = H[idx_2];
        } else {
            task->cl = &count2_codelet;
            task->handles[0] = H[idx_1];
            task->handles[1] = H[idx_2];
            task->handles[2] = H[idx_3];
        }
    }

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
