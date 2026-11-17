// Source: Odin crates/odin-omp/src/host_tools/delegation/owner/task_tools.rs (excerpt).
// Shows: the steer cap: a child steered [limits] max_steers_without_progress times with no successful tool call
// is escalated to the owner instead of being steered again.
        };
        // A child steered again and again without progress is stuck on
        // something steering cannot give it: it goes to the owner instead.
        let steer_progress = match &request.control {
            TaskControl::Steer(_) => {
                let (succeeded, head) = self
                    .control
                    .succeeded_tools_after(child, link.steer_head)
                    .map_err(|error| TaskToolFailure::new("result_read_failed", error))?;
                let unproductive = if succeeded > 0 {
                    0
                } else {
                    link.steers_without_progress
                };
