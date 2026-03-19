# Wireframes (draft)

## Kiosk - Start session
+--------------------------------------------------------------+
| FGC THN MEETUPS                          [Settings] [Admin] |
|--------------------------------------------------------------|
|                                                              |
|                     STARTA SESSION                           |
|                                                              |
|  [ Location: ______________ ]   [ Notes: ________________ ]  |
|                                                              |
|                [ Start ]                                     |
|                                                              |
|  Tip: Offline mode ok                                         |
+--------------------------------------------------------------+

## Kiosk - Scan mode
+--------------------------------------------------------------+
| Session: Wed 19:00 - Open          Status: READY             |
|--------------------------------------------------------------|
|  [ CAMERA PREVIEW - FULL WIDTH ]                             |
|                                                              |
|  Show your Sverok QR to the camera                            |
|                                                              |
|  Last scan: -                                                 |
+--------------------------------------------------------------+

## Kiosk - Scan success
+--------------------------------------------------------------+
| Session: Wed 19:00 - Open          Status: CHECKED IN         |
|--------------------------------------------------------------|
|  [ CAMERA PREVIEW ]                                           |
|                                                              |
|  Viktor Molina  19:42                                         |
|  Welcome back!                                                |
|                                                              |
|  (auto returns to scan)                                       |
+--------------------------------------------------------------+

## Kiosk - Unknown token
+--------------------------------------------------------------+
| Session: Wed 19:00 - Open          Status: UNKNOWN            |
|--------------------------------------------------------------|
|  [ CAMERA PREVIEW ]                                           |
|                                                              |
|  QR not recognized                                            |
|  Please contact the organizer to check in manually.          |
|                                                              |
+--------------------------------------------------------------+

## Kiosk - Attendance list
+--------------------------------------------------------------+
| Session: Wed 19:00 - Open    [End Session] [Manual Check-in]  |
|--------------------------------------------------------------|
|  Members (12)              Guests (2)                         |
|  ----------------------------------------------------------   |
|  19:05  Adam Kullander                                      | |
|  19:11  Ahmed Bashir                                        | |
|  19:16  Albin Fonde                                         | |
|  ...                                                        | |
|--------------------------------------------------------------|
|  Export CSV (admin)                                           |
+--------------------------------------------------------------+

## Organizer/Admin - Dashboard
+--------------------------------------------------------------+
| FGC THN MEETUPS  Dashboard                                    |
|--------------------------------------------------------------|
|  [ Start Session ]  [ Import Members ]  [ Export CSV ]        |
|                                                              |
|  Sessions Today                                               |
|  ----------------------------------------------------------   |
|  Wed 19:00  Open   12 checked in   [View]                     |
|  Sun 14:00  Closed 23 checked in   [View]                     |
|                                                              |
+--------------------------------------------------------------+

## Organizer/Admin - Import members
+--------------------------------------------------------------+
| Import eBas member list                                       |
|--------------------------------------------------------------|
|  [ Choose file .xlsx ]                                        |
|  Detected fields: member_number, first_name, last_name        |
|  Optional: city, zip_code                                     |
|                                                              |
|  [ Import ]                                                   |
|                                                              |
|  Result: added 12, updated 4                                  |
+--------------------------------------------------------------+

## Organizer/Admin - Reports
+--------------------------------------------------------------+
| Reports                                                      |
|--------------------------------------------------------------|
|  Date range: [ 2025-01-01 ] to [ 2025-02-29 ]                 |
|  Format: [ CSV v ]                                            |
|  [ Export for SFR ]                                           |
|                                                              |
|  Quick: [ Last 2 months ] [ This month ]                      |
+--------------------------------------------------------------+
