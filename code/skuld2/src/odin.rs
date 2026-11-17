// Source: skuld2 (private repo) src/odin.rs at 0382a40, verbatim.
// Shows: the pod-to-Odin telemetry contract: ODIN-STATUS and ODIN-CHECKPOINT lines, project events.
//! Lines Odin reads from a pod's stdout: `ODIN-STATUS {flat numeric object}` and `ODIN-CHECKPOINT {label, time}`;
//! and `odin huginn event` for asynchronous project events from host jobs.

use serde_json::{Map, Value};
use std::io::Write;

pub fn status(object: &Map<String, Value>) {
    line("ODIN-STATUS", &Value::Object(object.clone()));
}

pub fn checkpoint(object: &Value) {
    line("ODIN-CHECKPOINT", object);
}

fn line(prefix: &str, value: &Value) {
    let mut out = std::io::stdout().lock();
    let _ = writeln!(out, "{prefix} {value}");
    let _ = out.flush();
}

/// Report a project event to Odin (wakes `project_event:skuld2` watchers). Best effort: a host without the
/// command or credential gets a warning on stderr, never a failed job.
pub fn project_event(command: &[String], kind: &str, key: &str, detail: &Value) {
    let Some((program, args)) = command.split_first() else {
        return;
    };
    let result = std::process::Command::new(program)
        .args(args)
        .args(["--kind", kind, "--key", key, "--detail"])
        .arg(detail.to_string())
        .status();
    match result {
        Ok(status) if status.success() => {}
        Ok(status) => eprintln!("skuld2: project event {kind} {key} exited {status}"),
        Err(error) => eprintln!("skuld2: project event {kind} {key} not sent: {error}"),
    }
}
