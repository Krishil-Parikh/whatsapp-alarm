"""
Watches Windows notifications for WhatsApp Desktop messages from a specific
contact and rings a looping alarm + popup when one arrives.

Requires one-time setup: `py -3.12 -m pip install winsdk` (already installed).
Run with: py -3.12 whatsapp_alarm.py
"""

import asyncio
import queue
import threading
import tkinter as tk
import winsound
from datetime import datetime

from winsdk.windows.ui.notifications import NotificationKinds
from winsdk.windows.ui.notifications.management import (
    UserNotificationListener,
    UserNotificationListenerAccessStatus,
)

# --- Configure who to watch for -------------------------------------------
# Add the contact's name (and any nickname/short form WhatsApp might show in
# the notification title) in lowercase.
CONTACT_MATCHES = ["contact name here"]
WHATSAPP_APP_HINTS = ["whatsapp"]
ALARM_SOUND = r"C:\Windows\Media\Alarm10.wav"
POLL_SECONDS = 3
# ---------------------------------------------------------------------------

seen_ids = set()
alarm_active = threading.Event()
alert_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()


def is_whatsapp(app_info) -> bool:
    if app_info is None:
        return False
    name = (app_info.display_info.display_name or "").lower()
    aumid = (app_info.app_user_model_id or "").lower()
    return any(h in name for h in WHATSAPP_APP_HINTS) or any(
        h in aumid for h in WHATSAPP_APP_HINTS
    )


def contact_matched(texts: list[str]) -> bool:
    joined = " ".join(texts).lower()
    return any(m in joined for m in CONTACT_MATCHES)


def play_alarm_loop():
    alarm_active.set()
    while alarm_active.is_set():
        winsound.PlaySound(ALARM_SOUND, winsound.SND_FILENAME)
    winsound.PlaySound(None, winsound.SND_PURGE)


def stop_alarm():
    alarm_active.clear()


async def poll_loop():
    listener = UserNotificationListener.current
    status = await listener.request_access_async()
    if status != UserNotificationListenerAccessStatus.ALLOWED:
        print(
            "Notification access was not granted. Enable it manually in "
            "Settings > Privacy & Security > Notifications > Notification access."
        )
        return

    # Seed with notifications that already exist so we don't alarm on old messages.
    existing = await listener.get_notifications_async(NotificationKinds.TOAST)
    for n in existing:
        seen_ids.add(n.id)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Watching WhatsApp for a message from "
          f"'{CONTACT_MATCHES[0]}' (checking every {POLL_SECONDS}s). Leave this window open.")

    while True:
        try:
            notifs = await listener.get_notifications_async(NotificationKinds.TOAST)
            for n in notifs:
                if n.id in seen_ids:
                    continue
                seen_ids.add(n.id)

                if not is_whatsapp(n.app_info):
                    continue

                texts = []
                for binding in n.notification.visual.bindings:
                    for t in binding.get_text_elements():
                        texts.append(t.text)
                if not texts:
                    continue

                if contact_matched(texts):
                    title_text = texts[0]
                    body_text = texts[1] if len(texts) > 1 else ""
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] MATCH: {title_text} - {body_text}")
                    alert_queue.put((title_text, body_text))
        except Exception as e:
            print("poll error:", e)

        await asyncio.sleep(POLL_SECONDS)


def run_asyncio_thread():
    asyncio.run(poll_loop())


def show_popup(root, title_text, body_text):
    win = tk.Toplevel(root)
    win.title("WhatsApp Alert")
    win.attributes("-topmost", True)
    win.geometry("420x230+80+80")
    tk.Label(win, text="New message!", font=("Segoe UI", 16, "bold"), fg="#c00").pack(pady=(14, 4))
    tk.Label(win, text=title_text, font=("Segoe UI", 12, "bold")).pack()
    tk.Label(win, text=body_text, font=("Segoe UI", 10), wraplength=380, justify="left").pack(
        pady=8, padx=10
    )
    tk.Label(win, text=datetime.now().strftime("%H:%M:%S"), fg="#666").pack()

    def stop(_event=None):
        stop_alarm()
        win.destroy()

    tk.Button(
        win,
        text="Stop Alarm",
        command=stop,
        bg="#c00",
        fg="white",
        font=("Segoe UI", 11, "bold"),
        padx=20,
        pady=8,
    ).pack(pady=10)
    win.protocol("WM_DELETE_WINDOW", stop)
    win.bell()


def check_queue(root):
    try:
        while True:
            title_text, body_text = alert_queue.get_nowait()
            if not alarm_active.is_set():
                threading.Thread(target=play_alarm_loop, daemon=True).start()
            show_popup(root, title_text, body_text)
    except queue.Empty:
        pass
    root.after(300, check_queue, root)


def main():
    threading.Thread(target=run_asyncio_thread, daemon=True).start()

    root = tk.Tk()
    root.withdraw()  # no visible main window, only popups when triggered
    root.after(300, check_queue, root)
    root.mainloop()


if __name__ == "__main__":
    main()
