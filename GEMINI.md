# FGC THN Meetups - Project Overview

This project is for creating an attendance tracking application for the FGC Trollhättan weekly meetups. The goal is to have a simple and efficient way to check in members, with offline-first capabilities and reporting features for Studieframjandet (SFR).

## Project Goals

*   **MVP (Minimum Viable Product):**
    *   Fast, reliable check-in for weekly meetups.
    *   Offline-first kiosk flow.
    *   CSV exports for SFR reporting.
    *   A data foundation for insights and member motivation.
    *   Create a meetup session.
    *   Generate a QR code for check-in.
    *   Register attendance with a timestamp and member ID.
    *   Export a CSV file for reporting.
*   **Non-goals (MVP):**
    *   No public member self-portal.
    *   No real-time sync to a central server.
    *   No direct eBas API integration (import file only).
*   **Future Goals:**
    *   NFC check-in.
    *   Offline-first logging with optional synchronization.
    *   Exportable reports for Studieframjandet (SFR).
    *   Basic statistics for the association.

## Getting Started

There is no source code in the `src` directory yet. This section will be updated with instructions on how to build and run the project once the implementation starts.

## Development Conventions

The `docs` directory contains detailed information about the project's requirements, check-in flow, and reporting.

### Roles

*   **Admin:** Manage data, edit history, export.
*   **Weekly leader:** Run sessions, manual check-in fallback.
*   **Member:** Check-in via QR.
*   **Guest:** Manual check-in (name).

### Usage Areas

*   **Check-in:** Sessions, kiosk scan, attendance list, manual fallback.
*   **Insights:** Trends, retention, and travel approximations (city + zip_code).
*   **Reporting:** CSV exports and two-month summaries for SFR.

### Core Check-in Flow (Kiosk)

1.  Leader starts a session on kiosk.
2.  Member shows Sverok QR.
3.  Kiosk scans QR, extracts token, hashes it.
4.  Match member by token_hash.
5.  Record check-in with timestamp.
6.  Leader can view current attendance list.

### Data Schema (Draft)

*   **Member:** `id`, `token_hash`, `member_number`, `first_name`, `last_name`, `display_name`, `discord_id`, `membership_start`, `membership_end`, `city`, `zip_code`, `source`, `created_at`, `updated_at`.
*   **Session:** `id`, `start_time`, `end_time`, `location`, `created_by`, `status`, `notes`, `created_at`, `updated_at`.
*   **Checkin:** `id`, `session_id`, `member_id`, `guest_name`, `checkin_time`, `method`, `created_by`, `source_device_id`, `notes`.
*   **ImportBatch:** `id`, `source_file_name`, `source_file_hash`, `imported_at`, `records_total`, `records_added`, `records_updated`, `columns_included`.
*   **Export (CSV):** `session_date`, `session_start_time`, `session_end_time`, `member_number`, `first_name`, `last_name`, `guest_name`, `checkin_time`, `method`.
*   **Constraints:** `token_hash` unique, one check-in per member per session, guests can check in without a `member_id`.
*   **Notes:** Avoid storing personal number or full address in MVP. Optional fields (city/zip_code) should be confirmed before import.

### Import (eBas xlsx)

*   **Cadence:** Monthly + on-demand.
*   **Source:** eBas member list export (xlsx).
*   **Default fields to import:** `member_number`, `first_name`, `last_name`, `nick`/`display_name` (if available), `discord_id` (if available), `membership_start`, `membership_end`.
*   **Optional fields (confirm before storing):** `city`, `zip_code`.
*   **Explicitly excluded in MVP:** Personal number, full address.

### Offline Behavior

*   All data stored locally on the kiosk device.
*   No internet required for check-in.
*   Manual export for reporting.

### Exports

*   CSV export for SFR reporting.
*   CSV export for internal analysis.

### Editing Rules

*   Admin can edit or remove a check-in.
*   Edits are logged with a timestamp and editor.

### UI Flow (Draft) & Wireframes

**Kiosk Flow (primary):**
1.  **Start screen:** Big "Start session" button, optional location/notes.
2.  **Session active (scan mode):** Fullscreen camera preview, status banner (Ready / Scanned / Unknown / Duplicate), short instructions, last scan info.
3.  **Scan success:** Shows member name + time, auto-returns to scan.
4.  **Unknown token:** Message "Prata med arrangor for manuell incheckning", "Call organizer" button. No self-serve entry.
5.  **Manual check-in (organizer only):** Search member list, add guest name, save check-in.
6.  **Attendance list:** Live list, filter (members/guests), end session button.
7.  **End session:** Confirm end, optional notes.

**Organizer/Admin Flow (desktop/tablet):**
1.  **Dashboard:** Sessions today, quick start session, import member list, export CSV.
2.  **Import members:** Upload eBas xlsx, show detected fields, confirm import, summary.
3.  **Reports:** Export CSV by date range, two-month summary toggle.
4.  **Data maintenance:** Edit check-ins, resolve unknown tokens.

**Roles and Access:**
*   Kiosk: scan-only, no sensitive data.
*   Organizer: session controls + manual check-in.
*   Admin: full edit + export.

### Open Questions (from `intake-questions.md`)

*   **Goals & scope:** Must-have vs. nice-to-have, primary user, check-in speed, presence measurement.
*   **User roles:** Admin edit history/export, member history view.
*   **Member-ID / Sverok:** Digital member numbers, Sverok card validation, handling members without cards/phones.
*   **Check-in flow:** Scan QR on site or show QR to be scanned, single/multiple check-ins, duplicate handling.
*   **Equipment & environment:** Hardware, offline functionality, speed requirements.
*   **Offline & sync:** Offline mode for MVP, sync method, data sharing.
*   **Data & storage:** Storage location (local file, SQLite, cloud), history retention, backup/export routines.
*   **Reports to SFR:** Required format and fields, automatic reporting.
*   **Integrity & legal:** Storing personal data (name, email), consent/policy, anonymous guest logging.
*   **Statistics & insights:** Desired insights, filtering options, in-app dashboard.
*   **Design & language:** UI language (Swedish/English), kiosk mode, branding.
*   **Technical preferences:** Webapp (PWA), avoiding accounts/ID login, technical limitations.

This file should be reviewed and discussed before any code is written.
