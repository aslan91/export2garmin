# Agent Guidelines for `export2garmin`

Welcome, Agent! This repository is a fork of `RobertWojtowicz/export2garmin`, customized for automated health telemetry synchronization (Xiaomi/Mi Scale and Omron Blood Pressure) to Garmin Connect. It runs as a scheduled background service on a Raspberry Pi in the homelab environment.

---

## 1. System Purpose & Core Architecture

`export2garmin` orchestrates Bluetooth Low Energy (BLE) peripheral scanning, metric extraction, and cloud upload:
- **Target Platform**: Raspberry Pi (Linux / Debian ARM) with BlueZ and Bluetooth adapter (`hci0`).
- **Data Sources**:
  - Xiaomi Mi Body Composition Scale 2 / S400 (weight, body fat, muscle mass, bone mass, visceral fat).
  - Omron Blood Pressure Monitors (M4/M7 Intelli IT: systolic, diastolic, pulse).
- **Destination**: Garmin Connect Health API via OAuth tokens.
- **Runtime Mode**: Can run as a single-pass cron job or continuous loop (`import_data.sh -l`).

---

## 2. Architectural Boundaries & Component Map

- **`import_data.sh`**: Central process orchestrator. Manages concurrency locking, BLE/WiFi watchdogs, module execution sequence, and upload retry throttling.
- **`miscale/`**:
  - `miscale_ble.py`: BLE adapter health checking and MAC detection.
  - `body_scales.py` & `s400_ble.py`: Peripheral GATT discovery and byte-array telemetry decoders.
  - `Xiaomi_Scale_Body_Metrics.py`: Bioelectrical impedance calculation algorithms.
  - `miscale_export.py`: Garmin Connect upload client for weight and body composition.
- **`omron/`**:
  - `omblepy.py` & `sharedDriver.py`: Omron BLE pairing and GATT record retrieval.
  - `omron_export.py`: Garmin Connect blood pressure upload integration.
  - `omron_pairing.sh`: Interactive BLE pairing helper for new devices.
- **`user/`**:
  - `export2garmin.cfg`: Primary configuration (user weights, MAC addresses, Garmin credentials, feature flags).
  - `import_tokens.py`: Garmin OAuth token generator (MFA/2FA interactive login).
  - `miscale_backup.csv` & `omron_backup.csv`: Local tabular state logs.
- **`tests/`**: Offline test suite covering Mi Scale 2 packet decoding, body composition metrics, Omron HEM-7155T bitwise decoding, blood pressure categorization, and shell pipeline contracts.

---

## 3. Non-Negotiable Domain Invariants & Guardrails

1. **Upstream Fork Hygiene**:
   - This repository tracks upstream `https://github.com/RobertWojtowicz/export2garmin.git` on `master`.
   - **Rule**: Commit **only** `AGENTS.md` and direct operational bugfixes. **Never commit tool-specific pointer files** (`CLAUDE.md`, `.cursorrules`, `.clinerules`, `.github/copilot-instructions.md`) to Git; keep local assistant pointers untracked via `.git/info/exclude`.
   - Preserve upstream directory structures and naming conventions to avoid merge conflicts during upstream rebases.

2. **Process Locking & Stale PID Recovery**:
   - **Invariant**: If a previous run crashes, `import_data.sh` must verify whether the stored PID is alive (`kill -0 $pid`) with positive numeric validation, check process command line via `/proc/$pid/cmdline` to prevent stale locking on recycled PIDs, and resolve startup races before clearing locks. Stale locks must be cleared automatically (`cleanup_import_lock`) to prevent permanent service deadlock on unattended hosts.

3. **Garmin API Throttling & Retry Backoff**:
   - Failed cloud uploads must be throttled. Never execute rapid retry loops against Garmin endpoints on network or auth errors.
   - Ensure Garmin client sessions are properly instantiated and cached rather than repeatedly re-authenticating per measurement row.

4. **Credential & Secret Protection**:
   - **Never commit** `user/export2garmin.cfg` containing live passwords, OAuth token files, or measurement CSV files.
   - All runtime tokens and session stores must be gitignored or kept strictly in `user/`.

5. **BLE Scanning Resilience & Timebase Invariants**:
   - `miscale_ble.py` must wait for stabilized measurements (`isStabilized`) and never abort the BLE scan early on non-impedance packets. Weight readings without bio-impedance (e.g. socks, calluses) must be preserved and exported cleanly with calculated BMI.
   - `import_data.sh` must not apply redundant timezone hour offsets (`miscale_time_zone * 3600`) to timestamps parsed by `dt.timestamp()`, which are already in UTC epoch seconds.
   - Scale Clock Resilience: Mi Scale 2 loses RTC synchronization upon battery removal and broadcasts timestamps starting in epoch 1970. Both `miscale_ble.py` and `import_data.sh` must recognize uninitialized scale timestamps (`year < 2020` / `unix_time < 1577836800`) and fall back to the host's authoritative NTP timestamp so valid weigh-ins are never dropped due to false unsynchronization.
   - Data Extraction Invariant: `import_data.sh` must extract scale data via strict regex matching (`grep -E '^[0-9]+;[0-9.]+;[0-9]+' | tail -n 1`) to reject multiline banner output and prevent bash arithmetic syntax errors.

---

## 4. Operational Verification & Testing Protocol

Before committing changes:
```bash
# 1. Validate Bash syntax:
bash -n import_data.sh

# 2. Validate Python syntax across all modules:
python3 -m py_compile miscale/*.py omron/*.py omron/deviceSpecific/*.py

# 3. Run the automated test suite (27 offline unit tests):
python3 -m unittest discover tests
# or via pytest:
uv run --with pytest pytest

# 4. Dry-run single cycle execution (if on host with hardware/tokens):
./import_data.sh
```

---

## 5. State Persistence, Secret Hygiene & Hardware Protection

- **SD Card Wear Minimization**: Temporary logs (`temp.log`) and lockfiles should target RAM-backed storage (`/tmp` or zram/log2ram) as configured in `switch_temp_path`.
- **Atomic Operations**: CSV backups (`miscale_backup.csv`, `omron_backup.csv`) serve as local persistent ledgers with duplicate check via measurement timestamps.

---

## 6. Git Delivery & Agent Self-Audit Checklist

When completing work in this repository, verify:
- [ ] Bash scripts pass `bash -n` syntax check.
- [ ] Python files compile cleanly without syntax errors (`python -m py_compile`).
- [ ] Automated test suite passes (`python3 -m unittest discover tests`).
- [ ] No local `.cfg`, credentials, tokens, or CSV data files are staged in Git.
- [ ] Only relevant, clean bugfixes, tests, and `AGENTS.md` are staged.
- [ ] Commit message uses Conventional Commits format (e.g. `test: ...` or `fix(import): ...`).
- [ ] Upstream diff is kept minimal.
