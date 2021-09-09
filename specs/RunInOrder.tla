----------------------------- MODULE RunInOrder -----------------------------
EXTENDS Integers

(***************************************************************************)
(* The STF specification imposes very few constraints on the execution     *)
(* order beyond sequential consistency, this module defines a more         *)
(* restrictive "in-order" model that adds two constraints: the worker      *)
(* responsible for a task is deterministically choosen by a Mapping        *)
(* function and each worker executes its attributed tasks in the           *)
(* sequential order. By implementing the STF specification, this modules   *)
(* shows that the "in-order" model satisfy the same three properties:      *)
(* sequential consistency, data-race freedom and termination.              *)
(***************************************************************************)

CONSTANTS Data,
          Tasks,
          Workers,
          ControlFlow,
          Mapping,
          Idle

VARIABLES workerPendingTasks,
          terminatedTasks,
          workerStates

(***************************************************************************)
(* To make following statements simpler, we define the pending and active  *)
(* tasks in terms of the worker task queues and worker states.             *)
(***************************************************************************)

pendingTasks  == UNION {workerPendingTasks[w]: w \in Workers}

activeWorkers == {w \in Workers: workerStates[w] # Idle}

activeTasks   == {workerStates[w]: w \in activeWorkers}

-----------------------------------------------------------------------------

(***************************************************************************)
(* Initially all the workers are idle and the tasks are attributed to the  *)
(* workers using the Mapping function.                                     *)
(***************************************************************************)

Init == /\ terminatedTasks = {}
        /\ workerStates = [w \in Workers |-> Idle]
        /\ workerPendingTasks =
              [w \in Workers |-> {<<t, tid>> \in ControlFlow: Mapping[tid] = w}]

-----------------------------------------------------------------------------

(***************************************************************************)
(* This proposition can be used to verify that constants and variables     *)
(* hold sensible values.                                                   *)
(***************************************************************************)

TypeOK == /\ ControlFlow \subseteq (DOMAIN Tasks) \X Int
          /\ \A t \in DOMAIN Tasks: Tasks[t] \in [Data -> {"R", "W", "None"}]
          /\ pendingTasks \union activeTasks \union terminatedTasks = ControlFlow

-----------------------------------------------------------------------------

(***************************************************************************)
(* The two main differences in the way the next tasks are choosen compared *)
(* to the STF specification is that tasks are choosen from the pool of     *)
(* tasks assigned to a given worker and that only the first (in sequential *)
(* order) of that pool is considered for execution.                        *)
(***************************************************************************)

ReadReady(d, tid)  == \A <<t, other_tid>> \in ControlFlow:
                         \/ Tasks[t][d] = "None"
                         \/ Tasks[t][d] = "R"
                         \/ tid <= other_tid
                         \/ <<t, other_tid>> \in terminatedTasks

WriteReady(d, tid) == \A <<t, other_tid>> \in ControlFlow:
                         \/ Tasks[t][d] = "None"
                         \/ tid <= other_tid
                         \/ <<t, other_tid>> \in terminatedTasks

TaskReady(t, tid) == \A d \in Data:
                         \/ Tasks[t][d] = "None"
                         \/ Tasks[t][d] = "R" /\ ReadReady(d, tid)
                         \/ Tasks[t][d] = "W" /\ WriteReady(d, tid)

ExecuteTask(w) == workerStates[w] = Idle /\ \E <<t, tid>> \in workerPendingTasks[w]:
                    /\ \A <<other_t, other_tid>> \in workerPendingTasks[w]: tid <= other_tid
                    /\ TaskReady(t, tid)
                    /\ workerPendingTasks' =
                       [workerPendingTasks EXCEPT ![w] = workerPendingTasks[w] \ {<<t, tid>>}]
                    /\ workerStates' = [workerStates EXCEPT ![w] = <<t, tid>>]
                    /\ UNCHANGED terminatedTasks

TerminateTask(w) == /\ workerStates[w] \in (DOMAIN Tasks) \X Int
                    /\ workerStates' = [workerStates EXCEPT ![w] = Idle]
                    /\ terminatedTasks' = terminatedTasks \union {workerStates[w]}
                    /\ UNCHANGED workerPendingTasks

Next == \E w \in Workers: ExecuteTask(w) \/ TerminateTask(w)

-----------------------------------------------------------------------------

(***************************************************************************)
(* The following theorem asserts that the "in-order" model implements the  *)
(* STF specification, and thus ensures sequential consistency, data-race   *)
(* freedom and termination.                                                *)
(***************************************************************************)

Spec == /\ Init
        /\ [][Next]_<<workerPendingTasks, terminatedTasks, workerStates>>
        /\ WF_<<workerPendingTasks, terminatedTasks, workerStates>>(Next)

STF == INSTANCE STFSpec

THEOREM Spec => STF!Spec

=============================================================================
