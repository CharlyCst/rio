mod data;
mod runtime;
mod task_macro;

pub use data::*;
pub use runtime::*;
pub use task_macro::*;

#[cfg(test)]
mod tests {
    use super::*;

    fn add(a: &i32, b: &mut i32) {
        *b += *a;
    }

    fn double(a: &mut i32) {
        *a *= 2;
    }

    fn check_is_answer(a: &i32) {
        assert_eq!(*a, 42);
    }

    fn control_flow(mut rt: Runtime, args: (Data<i32>, Data<i32>)) {
        let (mut a, mut b) = args;

        task!{
            rt, add,
            R: a;
            RW: b;
        }
        task! {
            rt, double,
            RW: b;
        }
        task! {
            rt, check_is_answer,
            R: b;
        }
    }

    #[test]
    fn integration() {
        let map = move |task_id| ExecutorId::new((task_id as u32) % 2);
        let a = Data::new(1);
        let b = Data::new(20);
        go(2, map, (a, b), control_flow);
    }
}
