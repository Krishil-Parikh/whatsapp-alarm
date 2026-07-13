# whatsapp-alarm

Rings a looping alarm + popup on Windows when a specific contact sends you a
message on WhatsApp Desktop.

## How it works

WhatsApp Desktop suspends its UI when minimized to the system tray, so polling
its window directly is unreliable. Instead, this script reads Windows' Action
Center notification feed (`UserNotificationListener`), which WhatsApp Desktop
posts to for every incoming message regardless of whether the app window is
open or minimized.

Every few seconds it checks for new WhatsApp toast notifications. When the
notification's sender name matches a name you configure, it:

1. Plays a Windows alarm sound on a loop.
2. Shows a popup with the message preview and a "Stop Alarm" button.

## Requirements

- Windows 10/11
- Python 3.12 (the `winsdk` package does not yet ship wheels for free-threaded
  builds like 3.13t)
- WhatsApp Desktop (Microsoft Store app), with Windows notifications enabled
  for it (Settings → System → Notifications → WhatsApp → On)

## Setup

```
py -3.12 -m pip install winsdk
```

Edit `CONTACT_MATCHES` near the top of `whatsapp_alarm.py` with the contact's
name (and any short form WhatsApp might use in the notification title),
lowercase:

```python
CONTACT_MATCHES = ["jane doe", "jane"]
```

## Run

```
py -3.12 -u whatsapp_alarm.py
```

Leave it running. It has no visible window by default — only the popup
appears when a match fires. Close the console/process to stop it.

## Notes / limitations

- A chat you currently have open and focused in WhatsApp won't generate a
  notification (you're already looking at it), so the alarm won't fire for
  messages in that chat until you switch away.
- The first run grants this script access to Windows notifications; no extra
  setup is normally required beyond enabling notifications for WhatsApp
  itself.
- Matching is a case-insensitive substring check against the notification
  title/body text, so partial names can over-match in busy group chats.
