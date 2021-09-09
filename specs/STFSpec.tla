------------------------------ MODULE STFSpec ------------------------------
EXTENDS Integers, TLC

(**************************************************************************)
(* An STF program is represented as a Control Flow, that is a set of      *)
(* tasks on which a sequential order is defined. Tasks are represented as *)
(* functions mapping data items to a kind of dependency. Dependency kinds *)
(* are read-only ("R"), write ("W") or none ("None"). Finally, a set of   *)
(* workers can execute the tasks concurrently in any order that respects  *)
(* sequential consistency, as defined in this module.                     *)
(**************************************************************************)

CONSTANTS Data,
          Tasks,
          Workers,
          ControlFlow,
          Idle

VARIABLES pendingTasks,
          workerStates

(***************************************************************************)
(* To make the specification simpler, we define the set of active tasks    *)
(* as the set of tasks being actively processes by all the workers.        *)
(***************************************************************************)

activeWorkers == {w \in Workers: workerStates[w] # Idle}

activeTasks  == {workerStates[w]: w \in activeWorkers}

-----------------------------------------------------------------------------

(***************************************************************************)
(* Initialy all the workers are idle and no task is being executed         *)
(***************************************************************************)

Init == /\ pendingTasks = ControlFlow
        /\ workerStates = [w \in Workers |-> Idle]

-----------------------------------------------------------------------------

(***************************************************************************)
(* This predicate can be used to verify the correctness of the model       *)
(* parameters and variables.                                               *)
(***************************************************************************)

TypeOK == /\ \A t \in DOMAIN Tasks: Tasks[t] \in [Data -> {"R", "W", "None"}]
          /\ ControlFlow  \subseteq (DOMAIN Tasks) \X Int
          /\ activeTasks  \subseteq ControlFlow
          /\ pendingTasks \subseteq ControlFlow

-----------------------------------------------------------------------------

(***************************************************************************)
(* An execution is said to be data-race free if there is no concurrent     *)
(* executions of two tasks such that one task has a write dependency on a  *)
(* data while the other has either a read or write dependency on the same  *)
(* data.                                                                   *)
(***************************************************************************)

DataRaceFreedom == \A <<task1, task2>> \in activeTasks \X activeTasks:
                      \A d \in Data:
                         Tasks[task1[1]][d] = "W" => \/ task1[2] = task2[2]
                                                     \/ Tasks[task2[1]][d] = "None"

-----------------------------------------------------------------------------

(***************************************************************************)
(* Sequential consistency is ensured by allowing execution of a task only  *)
(* if for each data on which this task has a read or write dependency, all *)
(* previous tasks (in the sequential order) that have a write dependency   *)
(* on that same data have already been executed.                           *)
(***************************************************************************)

ReadReady(d, tid)  == \A <<t, otherTid>> \in pendingTasks \union activeTasks:
                           \/ Tasks[t][d] = "None"
                           \/ Tasks[t][d] = "R"
                           \/ otherTid >= tid

WriteReady(d, tid) == \A <<t, otherTid>> \in pendingTasks \union activeTasks:
                           \/ Tasks[t][d] = "None"
                           \/ otherTid >= tid

TaskReady(t, tid)  == \A d \in Data:
                           \/ Tasks[t][d] = "None"
                           \/ Tasks[t][d] = "R" /\ ReadReady(d, tid)
                           \/ Tasks[t][d] = "W" /\ WriteReady(d, tid)

(***************************************************************************)
(* A step in an STF execution consists in either an idle worker starting   *)
(* to execute a task that is marked a ready, or a busy worker terminating  *)
(* the execution of a task it started earlier.                             *)
(***************************************************************************)

ExecuteTask(w, t, tid) == /\ TaskReady(t, tid)
                          /\ workerStates[w] = Idle
                          /\ workerStates'   = [workerStates EXCEPT ![w] = <<t, tid>>]
                          /\ pendingTasks'   = pendingTasks \ {<<t, tid>>}

TerminateTask(w) == /\ workerStates[w] \in (DOMAIN Tasks) \X Int
                    /\ workerStates'   = [workerStates EXCEPT ![w] = Idle]
                    /\ UNCHANGED pendingTasks

Next == \E w \in Workers: \/ \E <<t, tid>> \in pendingTasks: ExecuteTask(w, t, tid)
                          \/ TerminateTask(w)

-----------------------------------------------------------------------------

(***************************************************************************)
(* The Next predicate ensures sequential consistency by selecting tasks to *)
(* be executed among tasks whose dependencies have already been executed.  *)
(* But we are also interested in two other properties: data-race freedom   *)
(* and termination. The following theorem asserts that the STF             *)
(* specification indeed ensures those properties hold.                     *)
(***************************************************************************)

Terminated == pendingTasks \union activeTasks = {}

Spec == /\ Init
        /\ [][Next]_<<pendingTasks, workerStates>>
        /\ WF_<<pendingTasks, workerStates>>(Next)

THEOREM Spec => []DataRaceFreedom /\ <>Terminated

=============================================================================
