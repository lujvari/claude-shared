# 0007 — cd-kits opens in the Q3 window

**Status:** done

## Purpose

cd-kits sits beside cd-tools in practice (shared kits checkout), so `cd-up` opens it in the `cd-q3` window with tools, dev and mep instead of `cd-q1`.

## Requirements

- REQ-1: `cd-up` SHALL list `kits` in `q3`, after `mep`, and not in `q1`.
- REQ-2: `launchers/README.md` and `specs/CURRENT.md` SHALL name the same groups.

## Scenarios

- **Given** no box is running **When** the owner runs `cd-up` **Then** cd-kits opens as a tab in `cd-q3`, and `cd-q1` holds only apg and asr.

## Out of scope

- Home-desk rectangles (`rect_of home/*`): need the home screens' working areas, measured at home (OPEN.md, cd-up window placement).
