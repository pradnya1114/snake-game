FINGER-TRACKING SNAKE GAME
==========================

A full-screen interactive snake game controlled using your index finger 
via the webcam. Built using Python, Mediapipe, OpenCV, and Pygame.

--------------------------------------
FEATURES
--------------------------------------
- Finger tracking using Mediapipe
- Neon snake animation
- Camera preview at top-right
- Random obstacles each round
- Food explosions with particles
- Timer and scoring system
- Start Menu -> Game -> End Screen
- Sound effects
- PNG and WAV assets supported

--------------------------------------
FOLDER STRUCTURE
--------------------------------------
finger_snake/
    finger_snake.py
    assets/
        main_bg.png
        game_bg.png
        end_bg.png
        start_btn.png
        eat.wav
        explode.wav
        gameover.wav

--------------------------------------
REQUIREMENTS
--------------------------------------
Python 3.11 recommended.

Install required packages:

pip install pygame opencv-python mediapipe numpy

--------------------------------------
RUNNING THE GAME
--------------------------------------
Run this command:

python finger_snake.py

--------------------------------------
BUILDING EXE (WINDOWS)
--------------------------------------
Use this PyInstaller command:

pyinstaller --onefile --windowed --clean --noupx ^
--exclude-module torch ^
--exclude-module tensorflow ^
--exclude-module keras ^
--exclude-module tensorboard ^
--add-data "assets;assets" ^
finger_snake.py

The EXE will be created inside the "dist" folder.

--------------------------------------
UPLOADING TO GODADDY
--------------------------------------
1. Zip the following:
   - finger_snake.exe
   - assets folder
   - README

2. Upload the ZIP to your GoDaddy "public_html" directory.

3. Create a simple download link:

<a href="finger_snake.zip" download>Download Game</a>

--------------------------------------
CONTROLS
--------------------------------------
Start Game: Click Start or press S
Restart: R
Quit: ESC
Move: Move your index finger in front of webcam

--------------------------------------
TECHNOLOGIES USED
--------------------------------------
Python
Pygame
OpenCV
Mediapipe
NumPy
PyInstaller

--------------------------------------
LICENSE
--------------------------------------
Free for personal and educational use.
Not for resale without permission.
