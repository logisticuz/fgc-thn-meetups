# Data schema (draft)

## Member
- id (uuid)
- token_hash (string, sha256)
- member_number (string, optional)
- first_name (string)
- last_name (string)
- display_name (string, optional)
- discord_id (string, optional)
- membership_start (date, optional)
- membership_end (date, optional)
- city (string, optional)
- zip_code (string, optional)
- source (enum: ebas_import, manual)
- created_at (datetime)
- updated_at (datetime)

## Session
- id (uuid)
- start_time (datetime)
- end_time (datetime, optional)
- location (string, optional)
- created_by (string, optional)
- status (enum: open, closed)
- notes (string, optional)
- created_at (datetime)
- updated_at (datetime)

## Checkin
- id (uuid)
- session_id (uuid)
- member_id (uuid, optional)
- guest_name (string, optional)
- checkin_time (datetime)
- method (enum: qr_scan, manual)
- created_by (string, optional)
- source_device_id (string, optional)
- notes (string, optional)

## ImportBatch
- id (uuid)
- source_file_name (string)
- source_file_hash (string)
- imported_at (datetime)
- records_total (int)
- records_added (int)
- records_updated (int)
- columns_included (string[])

## Export (CSV)
- session_date
- session_start_time
- session_end_time
- member_number
- first_name
- last_name
- guest_name
- checkin_time
- method

## Constraints
- token_hash unique
- one check-in per member per session
- guests can check in without a member_id

## Notes
- Avoid storing personal number or full address in MVP
- Optional fields (city/zip_code) should be confirmed before import
