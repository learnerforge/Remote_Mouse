# Roadmap — Version Plan

## Overview

Remote Mouse is on a journey from **35/100** to **~95/100** vs a wired mouse across 30 hardware specs, each with 4 sub-conditions = **120 total versions**.

## Version Groups

| Major | Specs | Current | Target |
|-------|-------|---------|--------|
| v1 | DPI, CPI, Polling Rate, IPS, Max Acceleration | 19/100 | 95/100 |
| v2 | Sensor Type, Sensor Model, Click Latency, LOD, Debounce | 26/100 | 95/100 |
| v3 | Switch Type, Click Durability, Buttons, Programmable, Memory | 5/100 | 95/100 |
| v4 | Wired, Bluetooth, 2.4GHz, Battery, Charging | 55/100 | 85/100 |
| v5 | Fast Charging, Weight, Dimensions, Ergonomics, Grip | 33/100 | 85/100 |
| v6 | PTFE Feet, Build Material, RGB, Software, Compatibility | 100/100 | 100/100 |

## Current Focus

### v1 Series — Motion & Tracking

| Version | Spec | Feature | Status |
|---------|------|---------|--------|
| v1.0.0 | DPI | Preset Selectors (400/800/1600/3200) | ✅ Done |
| v1.0.2 | DPI | Effective DPI Display | ⬜ Planned |
| v1.0.4 | DPI | Per-Profile DPI | ⬜ Planned |
| v1.0.6 | DPI | Status Bar DPI Indicator | ⬜ Planned |
| v1.2.0 | CPI | System CPI Display | ⬜ Planned |
| v1.2.2 | CPI | Pointer Speed Mapping | ⬜ Planned |
| v1.2.4 | CPI | Fine-grained CPI Steps | ⬜ Planned |
| v1.2.6 | CPI | Auto-Calibration | ⬜ Planned |

## Full Plan

See [`version_control.md`](../version_control.md) (local file, gitignored) for the complete 120-version breakdown with detailed specs, conditions, and implementation notes.

## Score Tracking

| Quarter | Target Score | Milestone |
|---------|:-----------:|-----------|
| Q1 | 35 | v1.0.0 DPI presets |
| Q2 | 50 | v1 series complete (motion & tracking) |
| Q3 | 65 | v2 series complete (sensing & clicks) |
| Q4 | 80 | v3 series complete (switches & buttons) |
| Future | 95 | All 30 specs at 95+ |

## Guiding Principles

1. **Each version builds on the prior** — follow spec-index → condition-patch order
2. **No breaking changes** — all versions are backward compatible
3. **Phone zero-install remains** — the core constraint never changes
4. **WebSocket-first** — all new features go through the existing event system
5. **Local-first** — cloud features (tunnel, email) are optional additions
