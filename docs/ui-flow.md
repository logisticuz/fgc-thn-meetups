# UI flow (draft)

## Kiosk flow (primary)
1) Start screen
   - Big "Start session" button
   - Optional: select location and notes

2) Session active (scan mode)
   - Fullscreen camera preview
   - Status banner (Ready / Scanned / Unknown / Duplicate)
   - Short instructions for members

3) Scan success
   - Shows member name + time
   - Auto-returns to scan after 2-3 seconds

4) Unknown token
   - Message: "Prata med arrangor for manuell incheckning"
   - Large "Call organizer" button
   - No self-serve entry on kiosk

5) Manual check-in (organizer only)
   - Search member list
   - Add guest name
   - Save check-in

6) Attendance list
   - Live list for the session
   - Filter: members / guests
   - End session button

7) End session
   - Confirm end
   - Optional notes

## Organizer/admin flow (desktop/tablet)
1) Dashboard
   - Sessions today
   - Quick start session
   - Import member list
   - Export CSV

2) Import members
   - Upload eBas xlsx
   - Show fields detected
   - Confirm import
   - Summary: added/updated

3) Reports
   - Export CSV by date range
   - Two-month summary toggle

4) Data maintenance
   - Edit check-ins
   - Resolve unknown tokens

## Roles and access
- Kiosk: scan-only, no sensitive data
- Organizer: session controls + manual check-in
- Admin: full edit + export
