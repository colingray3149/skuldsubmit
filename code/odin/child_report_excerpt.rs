// Source: Odin crates/odin-cli/src/odind/child_report.rs (excerpt, one function).
// Shows: the report wake a delegating seat receives when a child finishes: whole answer up to a declared cap,
// explicit labelling of a cut, and what to do with blocked or failed children (Lab 2 'idle churn' and re-steer loops).
/// A delegated child's report wake text, carrying up to `cap` characters of
/// its answer (the seat's `[limits] report_answer_chars`) and labelling any cut.
/// A failed turn is not successful completion; its observed text is relayed
/// as partial work only.
fn settled_child_report(
    settled: &odin_omp::host_tools::delegation::SettledChild,
    cap: usize,
) -> String {
    let child = settled.child;
    let excerpt = odin_omp::host_tools::delegation::relayed_answer(&settled.answer, cap, child);
    if settled.failed {
        let said = if excerpt.is_empty() {
            "No partial work is available.".to_owned()
        } else {
            format!("The last text it wrote (partial work, not its result):\n{excerpt}")
        };
        return format!(
            "Work you delegated (task {child}) was observed failing its latest turn; this is not \
             successful task completion. {said}\n\
             Check its current task state first: it may already have recovered since this \
             report was captured. Do not present partial text as a final result. If it is \
             still failed and you choose to re-delegate, call task_pause with \
             childSession=\"{child}\" and action=\"stop\", and await success first. If stop \
             fails, report cleanup as pending. If you lack task.pause authority, ask an \
             authorized coordinator; do not claim cleanup or a completed learning review. \
             Tell the owner plainly what failed and what comes next — no ids."
        );
    }
    format!(
        "Work you delegated (task {child}) just finished a turn. Its answer:\n{excerpt}\n\
         Compare it with what you asked for. A turn result, completion prose, a pushed branch \
         or a merge receipt does not establish final task completion. If it stopped before \
         the task is done (a plan, a survey or a progress note instead of the result), tell it \
         to carry on with task_steer and say nothing to the owner. An answer Odin cut is not \
         one: it is whole, so read the rest with task_read instead of asking it again. If it says \
         it is blocked, or asks for something it cannot get itself (an approval, access, a \
         decision) that you cannot give it, tell the owner once, plainly, what it needs and wait \
         for them: steering it to carry on will not unblock it. If it is asking you something you \
         can answer, answer it through task_steer. Keep incomplete work, questions and \
         escalations resumable; do not stop those children. Only after you accept the final \
         task result and no continuation or escalation remains, call \
         task_pause with childSession=\"{child}\" and action=\"stop\", and await success \
         before declaring that child stopped or cleaned up. If stop fails, report cleanup \
         as pending, not complete. If you lack task.pause authority, ask the authorized \
         owner to stop this exact child and do not claim cleanup. When the task is done or \
         truly blocked, tell the owner what they need to know — plainly, no ids. A successful \
         stop proves teardown, not that task learning review has finished."
    )
}
