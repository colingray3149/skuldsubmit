// Source: skuld2 (private repo) src/run.rs at 0382a40, verbatim.
// Shows: the run record type and its stage transitions.
//! The run record: stages, terminal states and the single writer of `run.yaml` and `log.yaml`.

use crate::files;
use anyhow::{Context, Result, bail, ensure};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::io::Write;
use std::path::{Path, PathBuf};

pub const STAGES: [&str; 10] = [
    "CREATED",
    "CASE_BUILT",
    "CHECKED",
    "RUNNING",
    "PAUSED",
    "TERMINAL",
    "POSTPROCESSED",
    "JUDGED",
    "EXPORTED",
    "COMMITTED",
];
pub const TERMINAL_STATES: [&str; 5] = ["COMPLETED", "STOPPED", "DIVERGED", "CRASHED", "FAILED"];
pub const PAUSE_REASONS: [&str; 4] = ["model_error", "operator", "budget_review", "node_yield"];

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Terminal {
    pub state: String,
    /// `END_TIME`, `STOP_FILE`, `WALL_BUDGET`, `NAN`, `SIGFPE`, a gate name, or the first fatal line.
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub detail: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Mark {
    pub stage: String,
    pub at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Resolution {
    pub dx_min_m: f64,
    #[serde(default)]
    pub induction_length_m: Option<f64>,
    #[serde(default)]
    pub points_per_induction: Option<f64>,
    pub amr_levels: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Run {
    pub schema: String,
    pub run_id: String,
    pub case_id: String,
    #[serde(default)]
    pub source_kind: Option<String>,
    #[serde(default)]
    pub access: Option<String>,
    #[serde(default)]
    pub sweep: Option<String>,
    #[serde(default)]
    pub campaign: Option<String>,
    #[serde(default)]
    pub rung: Option<String>,
    pub template: String,
    pub template_version: u32,
    pub module: String,
    pub family: String,
    pub params: BTreeMap<String, Value>,
    pub stage: String,
    pub stages: Vec<Mark>,
    #[serde(default)]
    pub terminal: Option<Terminal>,
    #[serde(default)]
    pub pause_reason: Option<String>,
    pub openfoam: String,
    #[serde(default)]
    pub image: Option<String>,
    #[serde(default)]
    pub node: Option<String>,
    pub ranks: u32,
    #[serde(default)]
    pub manifest_sha256: Option<String>,
    #[serde(default)]
    pub mesh_sha256: Option<String>,
    #[serde(default)]
    pub cells: Option<u64>,
    #[serde(default)]
    pub resolution: Option<Resolution>,
    #[serde(default)]
    pub end_time_s: Option<f64>,
    #[serde(default)]
    pub sim_time_s: Option<f64>,
    #[serde(default)]
    pub wall_s: Option<f64>,
    #[serde(default)]
    pub last_time: Option<String>,
    #[serde(default)]
    pub judge: Option<String>,
    /// The Odin export folder (`odin-<hash>`) and node the run was collected from.
    #[serde(default)]
    pub odin_folder: Option<String>,
    #[serde(default)]
    pub skuld2_commit: Option<String>,
    #[serde(default)]
    pub eggs_commit: Option<String>,
}

impl Run {
    pub fn reached(&self, stage: &str) -> bool {
        self.stages.iter().any(|mark| mark.stage == stage)
    }

    /// Move to `stage`. Stages run in order; PAUSED only leaves to RUNNING; a FAILED terminal may come before
    /// RUNNING (a gate refused the case before the solver started).
    pub fn advance(&mut self, stage: &str) -> Result<()> {
        let index = |name: &str| STAGES.iter().position(|known| *known == name);
        let to = index(stage).with_context(|| format!("unknown stage {stage}"))?;
        let from = index(&self.stage).context("record holds an unknown stage")?;
        let allowed = match (self.stage.as_str(), stage) {
            ("RUNNING", "PAUSED") | ("PAUSED", "RUNNING") => true,
            ("PAUSED", _) => false,
            ("RUNNING", "TERMINAL") => true,
            (_, "TERMINAL") => {
                from < index("RUNNING").unwrap()
                    && self
                        .terminal
                        .as_ref()
                        .is_some_and(|terminal| terminal.state == "FAILED")
            }
            ("TERMINAL", _) => to == index("POSTPROCESSED").unwrap(),
            _ => to == from + 1 && stage != "PAUSED" && stage != "TERMINAL",
        };
        ensure!(allowed, "stage {} cannot move to {stage}", self.stage);
        if stage == "TERMINAL" {
            ensure!(self.terminal.is_some(), "TERMINAL needs a terminal state");
        }
        self.stage = stage.to_owned();
        self.stages.push(Mark {
            stage: stage.to_owned(),
            at: now(),
        });
        Ok(())
    }

    pub fn terminate(&mut self, state: &str, name: &str, detail: Option<String>) -> Result<()> {
        ensure!(
            TERMINAL_STATES.contains(&state),
            "unknown terminal state {state}"
        );
        if self.terminal.is_some() {
            bail!("run {} already has a terminal state", self.run_id);
        }
        self.terminal = Some(Terminal {
            state: state.to_owned(),
            name: name.to_owned(),
            detail,
        });
        let advanced = self.advance("TERMINAL");
        if advanced.is_err() {
            self.terminal = None;
        }
        advanced
    }

    pub fn load(dir: &Path) -> Result<Self> {
        let path = dir.join("run.yaml");
        let text = std::fs::read_to_string(&path)
            .with_context(|| format!("reading {}", path.display()))?;
        serde_yaml::from_str(&text).with_context(|| format!("parsing {}", path.display()))
    }

    pub fn save(&self, dir: &Path) -> Result<()> {
        files::atomic_write(
            &dir.join("run.yaml"),
            serde_yaml::to_string(self)?.as_bytes(),
        )
    }
}

/// `log.yaml`: events appended, one YAML flow mapping per line.
pub struct EventLog(PathBuf);

impl EventLog {
    pub fn new(dir: &Path) -> Self {
        Self(dir.join("log.yaml"))
    }

    pub fn append(&self, event: &str, detail: Value) -> Result<()> {
        let line = serde_json::json!({"at": now(), "event": event, "detail": detail});
        let mut file = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.0)?;
        writeln!(file, "- {line}")?;
        Ok(())
    }
}

pub fn now() -> String {
    chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true)
}

pub fn valid_run_id(id: &str) -> bool {
    id.strip_prefix("Run")
        .is_some_and(|digits| digits.len() == 5 && digits.bytes().all(|b| b.is_ascii_digit()))
}
