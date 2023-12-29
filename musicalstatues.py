import tkinter as tk
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import time
import random
import cv2
from PIL import Image, ImageTk
import numpy as np
import subprocess

packages = ["pillow", "spotipy", "opencv-python", "numpy", "tk"]

for package in packages:
    subprocess.run(["pip", "install", package])

# Spotify API credentials
SPOTIPY_CLIENT_ID = '053a582d4a8441e89a0c514ad8efb3ff'
SPOTIPY_CLIENT_SECRET = 'bda2a54cc0d1495aa02a16c09d6abf74'
SPOTIPY_REDIRECT_URI = 'http://localhost:8080/callback'
SCOPE = 'user-library-read user-read-playback-state user-modify-playback-state'

camera = cv2.VideoCapture(0)  # Use the default camera (you may need to adjust this)

# Ask the user for the Spotify playlist link
playlist_link = input("Enter the Spotify playlist link: ")

# Extract the right part after the last colon
playlist_id = playlist_link.split('/')[-1].split('?')[0]

# Construct the PLAYLIST_URI
PLAYLIST_URI = f'spotify:playlist:{playlist_id}'
PLAY_DURATION_MIN = 20  # Minimum duration to play each track (in seconds)
PLAY_DURATION_MAX = 30  # Maximum duration to play each track (in seconds)
STOP_WARNING_DURATION = 5  # Duration before stopping to show the yellow light (in seconds)

# Spotify authentication
sp = Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                       client_secret=SPOTIPY_CLIENT_SECRET,
                                       redirect_uri=SPOTIPY_REDIRECT_URI,
                                       scope=SCOPE))

# Load and play the playlist
playlist = sp.playlist_tracks(PLAYLIST_URI)
playlist_uris = [track['track']['uri'] for track in playlist['items']]
random.shuffle(playlist_uris)
current_track = 0

# OpenCV setup for video recording (MP4)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use 'mp4v' for MP4 format
out = cv2.VideoWriter('dance_session.mp4', fourcc, 20.0, (640, 480))  # Adjust resolution as needed

# Adjustable parameters
BACKGROUND_UPDATE_INTERVAL = 30  # Update background every 30 frames
CONTOUR_AREA_THRESHOLD = 500  # Minimum contour area to detect movement

# Define frame count
frame_count = 0

# Function to check if anything is moving
def is_anything_moving():
    global background, frame_count

    _, frame = camera.read()
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)

    if 'background' not in globals() or frame_count % BACKGROUND_UPDATE_INTERVAL == 0:
        background = gray_frame.copy()

    frame_count += 1

    # Ensure both frames have the same dimensions
    background = cv2.resize(background, (gray_frame.shape[1], gray_frame.shape[0]))

    try:
        # Calculate the absolute difference between the current frame and the background
        delta_frame = cv2.absdiff(background, gray_frame)
        threshold_frame = cv2.threshold(delta_frame, 30, 255, cv2.THRESH_BINARY)[1]
        threshold_frame = cv2.dilate(threshold_frame, None, iterations=2)

        # Find contours of moving objects
        contours, _ = cv2.findContours(threshold_frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Check if any contour has a significant area (indicating movement)
        for contour in contours:
            contour_area = cv2.contourArea(contour)
            print("Contour Area:", contour_area)  # Debugging statement
            if contour_area > CONTOUR_AREA_THRESHOLD and status_label.cget("text") == "Don't move!":
                print("Movement detected!")  # Debugging statement
                # Close the app
                root.destroy()
                return True
    except cv2.error as e:
        print("Error:", e)

    return False

# Function to update the camera feed in a separate window and record the video
def update_camera_feed():
    global out
    _, frame = camera.read()
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.flip(frame, 1)  # Flip the image horizontally

    # Adjust the size of the frame
    frame = cv2.resize(frame, (640, 480))  # Set the desired width and height

    # Write the frame to the video file
    out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    img = Image.fromarray(frame)

    if is_anything_moving():
        print("Closing the app")  # Debugging statement
        out.release()  # Release the video writer
        root.destroy()

    img = Image.fromarray(frame)
    img = ImageTk.PhotoImage(img)
    camera_label.img = img
    camera_label.config(image=img)
    root.after(10, update_camera_feed)

# Function to update the current track label
def update_track_label():
    current_track_info = sp.current_playback()
    if current_track_info:
        track_name = current_track_info['item']['name']
        artist_names = ', '.join(artist['name'] for artist in current_track_info['item']['artists'])
        last.config(text=f"Last played: {track_name} - {artist_names}")

# Function to update the status label
def update_status_label(status):
    status_label.config(text=status)
    update_semafor(status)

# Function to update the "semafor" lights
def update_semafor(status):
    canvas_semafor.delete("all")  # Clear previous drawings
    if status == "Dance!":
        canvas_semafor.create_oval(50, 50, 150, 150, outline="", fill="green")  # Green light
    elif status == "Get ready to stop!":
        canvas_semafor.create_oval(50, 50, 150, 150, outline="", fill="yellow")  # Yellow light
    elif status == "Don't move!":
        canvas_semafor.create_oval(50, 50, 150, 150, outline="", fill="red")  # Red light

# Function to play each track for a fixed duration before pausing
def play_track():
    global background
    sp.start_playback(uris=[playlist_uris[current_track]])
    duration = random.randint(PLAY_DURATION_MIN, PLAY_DURATION_MAX)
    update_status_label("Dance!")
    update_track_label()

    # Reset background for motion detection
    _, background = camera.read()

    # Check for motion during the dance interval
    root.after((duration - STOP_WARNING_DURATION) * 1000, lambda: show_yellow_light(duration))

# Function to show the yellow light before stopping
def show_yellow_light(duration):
    update_status_label("Get ready to stop!")
    update_semafor("Get ready to stop!")
    root.after(STOP_WARNING_DURATION * 1000, lambda: stop_track())

# Function to stop the current track
def stop_track():
    sp.pause_playback()
    update_status_label("Don't move!")
    last.config(text="")
    root.after(5000, next_track)

# Function to move to the next track
def next_track():
    global current_track
    current_track += 1
    if current_track < len(playlist_uris):
        play_track()
    else:
        print("All tracks played. Game over.")

# GUI setup
root = tk.Tk()
root.title("Musical Statues Game")
root.geometry("1090x1080")  # Set window size to fullscreen

# Frame to center the components
center_frame = tk.Frame(root)
center_frame.pack(expand=True)

# Label for "Now Playing: Muzica"
last = tk.Label(center_frame, text=f"Now Playing:", font=("Helvetica", 14))
last.pack(side="top", anchor="w", padx=10, pady=10)

# Label to display the camera feed
camera_label = tk.Label(center_frame)
camera_label.pack(side="top", pady=20)

# Canvas for the "semafor"
canvas_semafor = tk.Canvas(center_frame, width=200, height=200)
canvas_semafor.pack(side="top", pady=20)

# Label to display dance/don't move status
status_label = tk.Label(center_frame, text="", font=("Helvetica", 48))
status_label.pack(side="top", pady=20)

# Start the game by playing the first track
play_track()

# Start the GUI event loop
root.after(10, update_camera_feed)
root.mainloop()
