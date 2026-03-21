# FGC THN Meetups - MVP Spec

## Goals
- Fast, reliable check-in for weekly meetups
- Offline-first kiosk flow
- CSV exports for SFR reporting
- A data foundation for insights and member motivation

## Non-goals (MVP)
- No public member self-portal
- No real-time sync to a central server
- No direct eBas API integration (import file only)

## Roles
- Admin: manage data, edit history, export
- Weekly leader: run sessions, manual check-in fallback
- Member: check-in via QR
- Guest: manual check-in (name)

## Usage areas
- Check-in: sessions, kiosk scan, attendance list, manual fallback
- Insights: trends, retention, and travel approximations (city + zip_code)
- Reporting: CSV exports and two-month summaries for SFR

## Core flow (kiosk)
1) Leader starts a session on kiosk
2) Member shows Sverok QR
3) Kiosk scans QR, extracts token, hashes it
4) Match member by token_hash
5) Record check-in with timestamp
6) Leader can view current attendance list

## QR handling
- Store token_hash (sha256) only
- Never store raw token or full eBas URL
- If token_hash unknown: mark as "unknown" and allow manual mapping
  - UI tells member to contact organizer for manual check-in

## Import (eBas xlsx)
- Import cadence: monthly + on-demand
- Source: eBas member list export (xlsx)
- Default fields to import:
  - member_number
  - first_name
  - last_name
  - nick / display_name (if available)
  - discord_id (if available)
  - membership_start
  - membership_end
- Optional fields (confirm before storing):
  - city
  - zip_code
- Explicitly excluded in MVP:
  - personal number
  - full address

## Offline behavior
- All data stored locally on the kiosk device
- No internet required for check-in
- Manual export for reporting

## Exports
- CSV export for SFR reporting
- CSV export for internal analysis

## Editing rules
- Admin can edit or remove a check-in
- Edits are logged with timestamp and editor

## UI
- Kiosk mode with large buttons and clear scan status
- Admin view for exports and basic insights
- Brand: match fgt-checkin-system (cyan on dark)

## Open questions
- Confirm required columns for SFR report
