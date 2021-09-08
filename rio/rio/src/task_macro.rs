#[macro_export]
macro_rules! task {
    // —————————————————————————————————— Main —————————————————————————————————— //
    // All the ways to call the `task!` macro !                                   //
    // —————————————————————————————————————————————————————————————————————————— //

    ($rt:ident, $fun:ident) => {
        task!{handle_task $rt, $fun, [], []}
    };

    ($rt:ident, $fun:ident, R: $($read_data:ident),+ $(;)?) => {
        task!{handle_task $rt, $fun, [$($read_data),+], []}
    };

    ($rt:ident, $fun:ident, RW: $($write_data:ident),+ $(;)?) => {
        task!{handle_task $rt, $fun, [], [$($write_data),+]}
    };

    ($rt:ident, $fun:ident, R: $($read_data:ident),+; RW: $($write_data:ident),+ $(;)?) => {
        task!{handle_task $rt, $fun, [$($read_data),+], [$($write_data),+]}
    };

    ($rt:ident, $fun:ident, map: $args:expr; R: $($read_data:ident),+ $(;)?) => {
        task!{handle_task $rt, $fun, [$($read_data),+], [], $args}
    };

    ($rt:ident, $fun:ident, map: $args:expr; RW: $($write_data:ident),+ $(;)?) => {
        task!{handle_task $rt, $fun, [], [$($write_data),+], $args}
    };

    ($rt:ident, $fun:ident, map: $args:expr; R: $($read_data:ident),+; RW: $($write_data:ident),+ $(;)?) => {
        task!{handle_task $rt, $fun, [$($read_data),+], [$($write_data),+], $args}
    };

    // —————————————————————————— Private Main Handler —————————————————————————— //
    // Main handler with a slightly uglier syntax, used to handle all the cases   //
    // at once while still exposing a nice interface to the user.                 //
    // —————————————————————————————————————————————————————————————————————————— //

    (handle_task $rt:ident, $fun:ident, [$($read_data:ident),*], [$($write_data:ident),*] $(,)? $($args:expr)?) => {
        unsafe {
            let (_task_id, ownership) = task!{get_task_id $rt, $($args)?};
            match ownership {
                $crate::TaskOwnership::Owner => {
                    {
                        // Get the data
                        task!{get_data_read  $($read_data),*}
                        task!{get_data_write _task_id, $($write_data),*}

                        // Perform the task
                        task!(call_fun $fun, [$($read_data),*], [$($write_data),*])
                    }
                }
                $crate::TaskOwnership::NotOwner => {
                    task!{register_task_read $($read_data),*}
                    task!{register_task_write _task_id, $($write_data),*}
                }
            }
        }
    };

    // —————————————————————————————— Get task_id ——————————————————————————————— //

    // Using custom mapping arguments
    (get_task_id $rt:ident, $args:expr) => {
        $rt.next_task_args($args)
    };

    // Default case: using TaskID (`usize`) as mapping argument
    (get_task_id $rt:ident,) => {
        $rt.next_task()
    };

    // ————————————————————————————— Call Function —————————————————————————————— //

    (call_fun $fun:ident, [$($read_args:ident),+], [$($write_args:ident),*]) => {
        $fun($(&$read_args),+, $(&mut $write_args),*);
    };
    (call_fun $fun:ident, [], [$($write_args: ident),*]) => {
        $fun($(&mut $write_args),*);
    };

    // ———————————————————————————————— Get Data ———————————————————————————————— //

    (get_data_read $(,)?) => {};
    (get_data_read $data:ident) => {
        let $data = $data.get_read();
    };
    (get_data_read $data:ident, $($datas:ident),+) => {
        task!{get_data_read $data}
        task!{get_data_read $($datas),+}
    };

    (get_data_write $task_id:ident $(,)?) => {};
    (get_data_write $task_id:ident, $data:ident) => {
        let mut $data = $data.get_write($task_id);
    };
    (get_data_write $task_id:ident, $data:ident, $($datas:ident),+) => {
        task!{get_data_write $task_id, $data}
        task!{get_data_write $task_id, $($datas),+}
    };

    // —————————————————————————————— Register Task ————————————————————————————— //

    (register_task_read ) => {};
    (register_task_read $data:ident) => {
        $data.declare_read();
    };
    (register_task_read $data:ident, $($datas:ident),+) => {
        task!{register_task_read $data}
        task!{register_task_read $($datas),+}
    };

    (register_task_write $task_id:ident $(,)?) => {};
    (register_task_write $task_id:ident, $data:ident) => {
        $data.declare_write($task_id);
    };
    (register_task_write $task_id:ident, $data:ident, $($datas:ident),+) => {
        task!{register_task_write $task_id, $data}
        task!{register_task_write $task_id, $($datas),+}
    };
}
