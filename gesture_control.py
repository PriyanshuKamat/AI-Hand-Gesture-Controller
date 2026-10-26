import time
import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import screen_brightness_control as sbc
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# 1. Webcam Setup
wCam, hCam = 640, 480
cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)

# 2. MediaPipe Hands Setup
mpHands = mp.solutions.hands if hasattr(mp, "solutions") else None
if mpHands:
    hands = mpHands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.8,
        min_tracking_confidence=0.8,
        model_complexity=0
    )
    mpDraw = mp.solutions.drawing_utils

# 3. Pycaw Audio Setup
devices = AudioUtilities.GetDeviceEnumerator()
default = devices.GetDefaultAudioEndpoint(0, 1)
interface = default.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = interface.QueryInterface(IAudioEndpointVolume)

volRange = volume.GetVolumeRange()
minVol = volRange[0]
maxVol = volRange[1]

# Variables
pTime = 0
smoothVolBar = 400
smoothVolPer = 0
smoothBriBar = 400
smoothBriPer = 0
is_muted = False
last_toggle_time = 0

# Lock State Variables
is_locked = False
last_lock_toggle_time = 0

print("🚀 Perfect Gesture Control Started! Press 'q' to exit.")

while True:
    success, img = cap.read()
    if not success:
        print("Webcam error!")
        break

    img = cv2.flip(img, 1)
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB) if (mpHands and "hands" in locals()) else None

    lmList = []
    if results and results.multi_hand_landmarks:
        for handLms in results.multi_hand_landmarks:
            for id, lm in enumerate(handLms.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lmList.append([id, cx, cy])

            mpDraw.draw_landmarks(img, handLms, mpHands.HAND_CONNECTIONS)

    if len(lmList) != 0:
        # Finger states (True if finger is up)
        index_up = lmList[8][2] < lmList[6][2]
        middle_up = lmList[12][2] < lmList[10][2]
        ring_up = lmList[16][2] < lmList[14][2]
        pinky_up = lmList[20][2] < lmList[18][2]

        # --- GESTURE 0: LOCK / UNLOCK TOGGLE (3 Fingers Up: Index + Middle + Ring up) ---
        three_fingers_up = index_up and middle_up and ring_up and not pinky_up

        if three_fingers_up:
            current_time = time.time()
            if current_time - last_lock_toggle_time > 2.0:  # 2 second cooldown
                is_locked = not is_locked
                last_lock_toggle_time = current_time

        # --- IF LOCKED: DISABLE ALL OTHER ACTIONS ---
        if is_locked:
            cv2.putText(
                img,
                "🔒 LOCKED (Show 3 Fingers to Unlock)",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )
        else:
            # --- GESTURE 1: FIST (Mute / Unmute) ---
            # All 4 fingers folded (Mukka)
            fingers_folded = not index_up and not middle_up and not ring_up and not pinky_up

            # --- GESTURE 2: VICTORY SIGN (Play / Pause) ---
            # Index & Middle up, Ring & Pinky down
            victory_sign = index_up and middle_up and not ring_up and not pinky_up

            if fingers_folded:
                is_muted = True
                volume.SetMute(1, None)
                cv2.putText(
                    img,
                    "MUTED (Fist)",
                    (180, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    3,
                )

            elif victory_sign:
                current_time = time.time()
                if current_time - last_toggle_time > 2.0:
                    pyautogui.press("playpause")
                    last_toggle_time = current_time
                cv2.putText(
                    img,
                    "PLAY / PAUSE (V-Sign)",
                    (140, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    3,
                )

            else:
                if is_muted:
                    volume.SetMute(0, None)
                    is_muted = False

                # --- GESTURE 3: VOLUME CONTROL (Thumb [4] & Index [8]) ---
                x1, y1 = lmList[4][1], lmList[4][2]
                x2, y2 = lmList[8][1], lmList[8][2]

                cv2.circle(img, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
                cv2.circle(img, (x2, y2), 10, (255, 0, 255), cv2.FILLED)
                cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)

                length_vol = np.hypot(x2 - x1, y2 - y1)
                vol = np.interp(length_vol, [30, 200], [minVol, maxVol])
                volBar = np.interp(length_vol, [30, 200], [400, 150])
                volPer = np.interp(length_vol, [30, 200], [0, 100])

                smoothVolBar = smoothVolBar * 0.75 + volBar * 0.25
                smoothVolPer = smoothVolPer * 0.75 + volPer * 0.25
                volume.SetMasterVolumeLevel(vol, None)

                # --- GESTURE 4: BRIGHTNESS CONTROL (Thumb [4] & Ring Finger [16]) ---
                x3, y3 = lmList[4][1], lmList[4][2]
                x4, y4 = lmList[16][1], lmList[16][2]

                cv2.circle(img, (x3, y3), 10, (0, 255, 255), cv2.FILLED)
                cv2.circle(img, (x4, y4), 10, (0, 255, 255), cv2.FILLED)
                cv2.line(img, (x3, y3), (x4, y4), (0, 255, 255), 3)

                length_bri = np.hypot(x4 - x3, y4 - y3)
                brightnessPer = np.interp(length_bri, [30, 200], [0, 100])
                briBar = np.interp(length_bri, [30, 200], [400, 150])

                smoothBriBar = smoothBriBar * 0.75 + briBar * 0.25
                smoothBriPer = smoothBriPer * 0.75 + brightnessPer * 0.25
                try:
                    sbc.set_brightness(int(smoothBriPer))
                except:
                    pass

    # --- UI DRAWING (Volume Bar) ---
    cv2.rectangle(img, (50, 150), (85, 400), (255, 0, 255), 3)
    cv2.rectangle(img, (50, int(smoothVolBar)), (85, 400), (255, 0, 255), cv2.FILLED)
    cv2.putText(img, f"{int(smoothVolPer)}%", (40, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
    cv2.putText(img, "Volume", (40, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)

    # --- UI DRAWING (Brightness Bar) ---
    cv2.rectangle(img, (550, 150), (585, 400), (0, 255, 255), 3)
    cv2.rectangle(img, (550, int(smoothBriBar)), (585, 400), (0, 255, 255), cv2.FILLED)
    cv2.putText(img, f"{int(smoothBriPer)}%", (530, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(img, "Brightness", (525, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    # --- FPS Counter ---
    cTime = time.time()
    fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
    pTime = cTime
    cv2.putText(img, f"FPS: {int(fps)}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow("Gesture Control System - Pro AI Project", img)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()