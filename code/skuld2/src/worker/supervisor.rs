// Source: skuld2 (private repo) src/worker/supervisor.rs at 0382a40, verbatim.
// Shows: the in-pod supervision loop (log tail, stop file, deadlines, stalls, exit classification).
//! The supervision loop: log tail, stop requests, deadlines, stalls, ODIN-STATUS and ODIN-CHECKPOINT lines,
//! and the exit classification of 06 section 6.

use super::{Solver, control, log::LogTail, state};
use crate::config::Config;
use crate::odin;
use anyhow::Result;
use serde_json::{Map, Value, json};
use std::os::unix::process::ExitStatusExt;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{Duration, Instant};

pub struct Plan {
    pub case: PathBuf,
    pub fields: Vec<String>,
    pub ranks: u32,
    pub cells: Option<u64>,
    pub end_time_s: f64,
    /// Stop cleanly once this much wall time has passed (the pod deadline less the margin).
    pub budget: Duration,
    /// Optional command printing one flat JSON object of live counters (waves, wave_speed_ms).
    pub live: Option<Vec<String>>,
    /// Checked mesh digest and destination for immutable checkpoint observations.
    pub observation: Option<(String, PathBuf)>,
    pub module: String,
    pub allowlist: PathBuf,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum Stop {
    Budget,
    Pod,
    Stall,
}

#[derive(Debug)]
pub struct Outcome {
    pub state: &'static str,
    pub name: String,
    pub detail: Option<String>,
    pub sim_time_s: Option<f64>,
    pub last_complete: Option<String>,
    pub wall_s: f64,
}

/// Solver progress sampled for the running run record.
pub struct Progress {
    pub sim_time_s: Option<f64>,
    pub last_complete: Option<String>,
    pub wall_s: f64,
}

pub fn supervise(
    mut solver: Solver,
    plan: &Plan,
    config: &Config,
    env: &[(String, String)],
    mut persist: impl FnMut(Progress) -> Result<()>,
) -> Result<Outcome> {
    let started = Instant::now();
    let cap = config.gate.max_log_tail_bytes;
    let log_path = plan.case.join("log.foamRun");
    let mut tail = LogTail::default();
    let mut stop: Option<(Stop, Instant, bool)> = None; // reason, when requested, stop file written
    let mut last_growth = (0u64, Instant::now());
    let mut last_status =
        Instant::now() - Duration::from_secs(config.stepping.status_every_seconds);
    let mut last_persist = started;
    let mut seen_complete = std::collections::HashSet::new();
    let mut writes = 0u64;
    let mut divergence_since: Option<Instant> = None;
    let mut control_seq = 0u64;
    let mut end_time = plan.end_time_s;
    let mut ranks = RankTracker::default();
    let mut live = Map::new();
    let status = loop {
        ranks.sample(solver.child.id(), &plan.case, plan.ranks);
        if let Some(status) = solver.child.try_wait()? {
            break status;
        }
        match control::apply_steer(Path::new("/var/run/odin/control/control.json"), &plan.case, &plan.module, &plan.allowlist, control_seq, cap) {
            Ok(Some((seq, end))) => { control_seq = seq; if let Some(end) = end { end_time = end; } }
            Ok(None) => {},
            Err(error) => eprintln!("control request refused: {error:#}"),
        }
        tail.read_new(&log_path, cap)?;
        let s = &tail.summary;
        if s.nan_seen {
            let since = divergence_since.get_or_insert_with(Instant::now);
            let signal = if since.elapsed() >= Duration::from_secs(config.control.stop_grace_seconds) {
                libc::SIGKILL
            } else {
                libc::SIGTERM
            };
            control::signal_group(solver.pgid, signal)?;
        }
        let size = std::fs::metadata(&log_path).map(|m| m.len()).unwrap_or(0);
        if size != last_growth.0 {
            last_growth = (size, Instant::now());
        }
        if stop.is_none() {
            let reason = if control::terminated() {
                Some(Stop::Pod)
            } else if started.elapsed() >= plan.budget {
                Some(Stop::Budget)
            } else if last_growth.1.elapsed() >= Duration::from_secs(config.stepping.stall_seconds)
            {
                Some(Stop::Stall)
            } else {
                None
            };
            if let Some(reason) = reason {
                stop = Some((reason, Instant::now(), false));
            }
        }
        if let Some((reason, since, written)) = stop.as_mut() {
            let grace = Duration::from_secs(if *reason == Stop::Pod {
                config.control.pod_term_grace_seconds
            } else {
                config.control.stop_grace_seconds
            });
            if !*written && s.steps > 0 {
                control::touch(&plan.case, &config.control.stop_file)?;
                *written = true;
            }
            if since.elapsed() >= grace * 2 {
                control::signal_group(solver.pgid, libc::SIGKILL)?;
            } else if since.elapsed() >= grace || (*reason == Stop::Stall && !*written) {
                control::signal_group(solver.pgid, libc::SIGTERM)?;
            }
        }
        checkpoints(plan, &mut seen_complete, &mut writes)?;
        if last_status.elapsed() >= Duration::from_secs(config.stepping.status_every_seconds) {
            if let Some(command) = &plan.live {
                live = live_counters(
                    command,
                    &plan.case,
                    env,
                    Duration::from_secs(config.stepping.status_every_seconds / 2),
                    cap,
                    Duration::from_secs(config.stepping.batch_seconds),
                );
            }
            update_telemetry(&mut live, &ranks, control_seq);
            odin::status(&status_object(
                &tail,
                plan,
                writes,
                started.elapsed(),
                end_time,
                &live,
                "running",
            ));
            last_status = Instant::now();
        }
        if last_persist.elapsed() >= Duration::from_secs(config.stepping.persist_every_seconds) {
            let progress = Progress {
                sim_time_s: tail.summary.time,
                last_complete: state::latest_complete(&plan.case, plan.ranks, &plan.fields)?.map(|(_, name)| name),
                wall_s: started.elapsed().as_secs_f64(),
            };
            if let Err(error) = persist(progress) {
                let _ = control::signal_group(solver.pgid, libc::SIGKILL);
                let _ = solver.child.wait();
                return Err(error);
            }
            last_persist = Instant::now();
        }
        std::thread::sleep(Duration::from_secs(config.stepping.batch_seconds));
    };
    let orphan_deadline = Instant::now() + Duration::from_secs(config.control.stop_grace_seconds);
    while control::group_alive(solver.pgid) {
        control::signal_group(solver.pgid, libc::SIGKILL)?;
        if Instant::now() >= orphan_deadline {
            anyhow::bail!("solver process group {} remains after orphan cleanup grace", solver.pgid);
        }
        std::thread::sleep(Duration::from_secs(config.stepping.batch_seconds).min(orphan_deadline.saturating_duration_since(Instant::now())));
    }
    tail.read_new(&log_path, cap)?;
    let last_complete =
        state::latest_complete(&plan.case, plan.ranks, &plan.fields)?.map(|(_, name)| name);
    checkpoints(plan, &mut seen_complete, &mut writes)?;
    ranks.sample(solver.child.id(), &plan.case, plan.ranks);
    update_telemetry(&mut live, &ranks, control_seq);
    let wall_s = started.elapsed().as_secs_f64();
    odin::status(&status_object(
        &tail,
        plan,
        writes,
        started.elapsed(),
        end_time,
        &live,
        "terminal",
    ));
    let s = &tail.summary;
    let (state, name, detail) = if s.nan_seen {
        ("DIVERGED", "NAN".to_owned(), None)
    } else if s.sigfpe || status.signal() == Some(libc::SIGFPE) || status.code() == Some(136) {
        ("DIVERGED", "SIGFPE".to_owned(), None)
    } else if let Some(fatal) = &s.fatal {
        ("CRASHED", fatal.chars().take(512).collect(), None)
    } else if let Some((reason, _, _)) = stop {
        let name = match reason {
            Stop::Budget => "WALL_BUDGET",
            Stop::Pod => "OPERATOR",
            Stop::Stall => "STALL",
        };
        ("STOPPED", name.to_owned(), None)
    } else if status.success() && (s.stop_file_write || plan.case.join(&config.control.stop_file).exists()) {
        ("STOPPED", "STOP_FILE".to_owned(), None)
    } else if status.success() && s.ended && (!s.shock_stop || last_complete.is_some()) {
        let done = s
            .time
            .is_some_and(|time| time >= end_time * (1.0 - 1e-9));
        (
            "COMPLETED",
            if done { "END_TIME" } else if s.shock_stop { "SHOCK_POSITION" } else { "SOLVER_END" }.to_owned(),
            None,
        )
    } else {
        let why = match (status.code(), status.signal()) {
            (Some(code), _) => format!("exit status {code}"),
            (_, Some(signal)) => format!("killed by signal {signal}"),
            _ => "unknown exit".to_owned(),
        };
        ("CRASHED", why, None)
    };
    Ok(Outcome {
        state,
        name,
        detail,
        sim_time_s: s.time,
        last_complete,
        wall_s,
    })
}

fn checkpoints(plan: &Plan, seen: &mut std::collections::HashSet<String>, writes: &mut u64) -> Result<()> {
    let root = state::roots(&plan.case, plan.ranks).into_iter().next().expect("one root");
    for (time, name) in state::times(&root)? {
        if time <= 0.0 || seen.contains(&name) || !state::complete(&plan.case, plan.ranks, &name, &plan.fields) { continue; }
        if let Some((mesh, directory)) = &plan.observation {
            let out = directory.join(&name);
            if !out.exists() { crate::observe::freeze(&plan.case, plan.ranks, &name, mesh, &plan.fields, &out)?; }
        }
        *writes += 1;
        odin::checkpoint(&json!({"label": format!("t={name}"), "time": name}));
        seen.insert(name);
    }
    Ok(())
}

pub fn status_object(
    tail: &LogTail,
    plan: &Plan,
    writes: u64,
    wall: Duration,
    end_time: f64,
    live: &Map<String, Value>,
    _summary: &str,
) -> Map<String, Value> {
    let s = &tail.summary;
    let mut object = Map::new();
    let mut put = |key: &str, value: Option<f64>| {
        if let Some(value) = value.filter(|v| v.is_finite()) {
            object.insert(key.to_owned(), json!(value));
        }
    };
    put("sim_time_us", s.time.map(|t| t * 1e6));
    put("end_time_us", Some(end_time * 1e6));
    put("delta_t_ns", s.delta_t.map(|dt| dt * 1e9));
    put("courant_max", s.courant_max);
    put("residual_max", s.residual_max);
    put("cells", plan.cells.map(|c| c as f64));
    put("ranks", Some(plan.ranks as f64));
    put("nan_seen", Some(if s.nan_seen { 1.0 } else { 0.0 }));
    put("writes", Some(writes as f64));
    put("wall_s", Some(wall.as_secs_f64().round()));
    for (key, value) in live {
        if value.is_number() && !key.is_empty()
            && key.bytes().all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
            && !object.contains_key(key)
        {
            object.insert(key.clone(), value.clone());
        }
    }
    object
}

fn update_telemetry(live: &mut Map<String, Value>, ranks: &RankTracker, control_seq: u64) {
    // Probe output must not masquerade as authoritative supervisor measurements.
    live.remove("ranks_dead");
    live.remove("shm_used_mib");
    live.insert("control_seq".into(), json!(control_seq));
    if let Some(dead) = ranks.dead() { live.insert("ranks_dead".into(), json!(dead)); }
    if let Some(used) = shm_used_mib() { live.insert("shm_used_mib".into(), json!(used)); }
}

#[cfg(test)]
mod telemetry_tests {
    use super::*;

    #[test]
    fn supervisor_counters_override_probe_and_omit_unknown_ranks() {
        let mut live = Map::new();
        live.insert("ranks_dead".into(), json!(99));
        live.insert("shm_used_mib".into(), json!(-1));
        live.insert("control_seq".into(), json!(99));
        let mut ranks = RankTracker::default();
        update_telemetry(&mut live, &ranks, 2);
        assert!(!live.contains_key("ranks_dead"));
        assert_eq!(live["control_seq"], json!(2));
        if let Some(used) = live.get("shm_used_mib") { assert!(used.as_f64().unwrap() >= 0.0); }
        ranks.initialized = true;
        ranks.sample_valid = true;
        ranks.dead.insert((123, 456));
        update_telemetry(&mut live, &ranks, 3);
        assert_eq!(live["ranks_dead"], json!(1));
        assert_eq!(live["control_seq"], json!(3));
    }

    #[test]
    fn rank_identity_detects_exit_and_pid_reuse() {
        let mut ranks = RankTracker::default();
        ranks.initialized = true;
        ranks.identities.insert((std::process::id(), u64::MAX));
        ranks.sample(std::process::id(), Path::new("."), 1);
        assert_eq!(ranks.dead(), Some(1));
    }
}

#[derive(Default)]
struct RankTracker {
    identities: std::collections::HashSet<(u32, u64)>,
    dead: std::collections::HashSet<(u32, u64)>,
    initialized: bool,
    sample_valid: bool,
}

impl RankTracker {
    fn sample(&mut self, root: u32, case: &Path, expected: u32) {
        self.sample_valid = false;
        let Ok(entries) = std::fs::read_dir("/proc") else { return; };
        let mut records = std::collections::HashMap::new();
        for entry in entries.flatten() {
            let Ok(pid) = entry.file_name().to_string_lossy().parse::<u32>() else { continue; };
            let Ok(stat) = std::fs::read_to_string(entry.path().join("stat")) else { continue; };
            let Some((_, rest)) = stat.rsplit_once(") ") else { continue; };
            let fields: Vec<_> = rest.split_whitespace().collect();
            if fields.len() <= 19 { continue; }
            if let (Ok(parent), Ok(start)) = (fields[1].parse::<u32>(), fields[19].parse::<u64>()) {
                records.insert(pid, (parent, start, fields[0] != "Z"));
            }
        }
        if self.initialized {
            for &(pid, start) in &self.identities {
                match std::fs::read_to_string(format!("/proc/{pid}/stat")) {
                    Ok(stat) => {
                        let Some((_, rest)) = stat.rsplit_once(") ") else { return; };
                        let fields: Vec<_> = rest.split_whitespace().collect();
                        if fields.len() <= 19 { return; }
                        let Ok(tick) = fields[19].parse::<u64>() else { return; };
                        if fields[0] == "Z" || tick != start { self.dead.insert((pid, start)); }
                    }
                    Err(error) if error.kind() == std::io::ErrorKind::NotFound => { self.dead.insert((pid, start)); }
                    Err(_) => return,
                }
            }
            self.sample_valid = true;
            return;
        }
        let mut descendants = std::collections::HashSet::from([root]);
        loop {
            let before = descendants.len();
            for (&pid, &(parent, _, _)) in &records { if descendants.contains(&parent) { descendants.insert(pid); } }
            if before == descendants.len() { break; }
        }
        let case = case.canonicalize().unwrap_or_else(|_| case.to_path_buf());
        for pid in descendants {
            let Some(&(_, start, true)) = records.get(&pid) else { continue; };
            let dir = PathBuf::from(format!("/proc/{pid}"));
            let Ok(cwd) = std::fs::read_link(dir.join("cwd")) else { continue; };
            let Ok(args) = std::fs::read(dir.join("cmdline")) else { continue; };
            let mut args = args.split(|&b| b == 0);
            let first = args.next().unwrap_or_default();
            if cwd == case && first.rsplit(|&b| b == b'/').next() == Some(b"foamRun")
                && (expected == 1 || args.any(|arg| arg == b"-parallel")) {
                self.identities.insert((pid, start));
            }
        }
        if self.identities.len() == expected as usize { self.initialized = true; self.sample_valid = true; }
        else { self.identities.clear(); }
    }

    fn dead(&self) -> Option<usize> { (self.initialized && self.sample_valid).then_some(self.dead.len()) }
}

fn shm_used_mib() -> Option<f64> {
    let mut stats = std::mem::MaybeUninit::<libc::statvfs>::uninit();
    if unsafe { libc::statvfs(c"/dev/shm".as_ptr(), stats.as_mut_ptr()) } != 0 { return None; }
    let stats = unsafe { stats.assume_init() };
    Some((stats.f_blocks.saturating_sub(stats.f_bfree) as f64) * stats.f_frsize as f64 / 1_048_576.0)
}

/// Run the live-counter command with a time cap; on any failure, no counters.
fn live_counters(
    command: &[String],
    case: &Path,
    env: &[(String, String)],
    cap: Duration,
    max_bytes: u64,
    cadence: Duration,
) -> Map<String, Value> {
    let Some(program) = command.first() else { return Map::new(); };
    let Ok(mut child) = Command::new(program)
        .args(&command[1..])
        .current_dir(case)
        .env_clear()
        .envs(env.iter().map(|(k, v)| (k, v)))
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::null())
        .spawn()
    else {
        return Map::new();
    };
    use std::io::Read;
    use std::os::fd::AsRawFd;
    let mut stdout = child.stdout.take().expect("piped stdout");
    let fd = stdout.as_raw_fd();
    if unsafe { libc::fcntl(fd, libc::F_SETFL, libc::O_NONBLOCK) } < 0 {
        let _ = child.kill();
        let _ = child.wait();
        return Map::new();
    }
    let mut out = Vec::new();
    let mut buffer = [0u8; 4096];
    let started = Instant::now();
    while started.elapsed() < cap {
        loop {
            match stdout.read(&mut buffer) {
                Ok(0) => break,
                Ok(n) => {
                    out.extend_from_slice(&buffer[..n]);
                    if out.len() as u64 > max_bytes {
                        let _ = child.kill();
                        let _ = child.wait();
                        return Map::new();
                    }
                }
                Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => break,
                Err(_) => { let _ = child.kill(); let _ = child.wait(); return Map::new(); }
            }
        }
        if let Ok(Some(status)) = child.try_wait() {
            if !status.success() { return Map::new(); }
            return std::str::from_utf8(&out).ok()
                .and_then(|text| text.lines().last())
                .and_then(|line| serde_json::from_str(line).ok())
                .unwrap_or_default();
        }
        std::thread::sleep(cadence.min(cap.saturating_sub(started.elapsed())));
    }
    let _ = child.kill();
    let _ = child.wait();
    Map::new()
}
