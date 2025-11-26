@echo off
echo ===========================================
echo      FINGER SNAKE GAME - EXE BUILDER
echo ===========================================

REM >>> SET YOUR PYTHON FROM snake_env <<<
set PYTHON="C:\Users\mintl\Desktop\SNAKE GAME\snake_env\Scripts\python.exe"

REM >>> SET YOUR SCRIPT NAME HERE <<<
set SCRIPT=finger_snake.py

REM >>> PATH TO YOUR MEDIAPIPE WHEEL <<<
set MEDIAWHEEL="C:\Users\mintl\Desktop\SNAKE GAME\mediapipe-0.9.0.1-cp310-cp310-win_amd64.whl"

echo.
echo Checking Python version...
%PYTHON% --version

echo.
echo Installing/upgrading pip, setuptools, wheel...
%PYTHON% -m pip install --upgrade pip setuptools wheel

echo.
echo Installing required packages (pygame, opencv, numpy)...
%PYTHON% -m pip install pygame opencv-python numpy

echo.
echo Installing Mediapipe 0.9.0.1 (EXE-friendly)...
%PYTHON% -m pip install --force-reinstall %MEDIAWHEEL%

echo.
echo Installing BACKPORTS FIX (prevents EXE crash)...
%PYTHON% -m pip install backports
%PYTHON% -m pip install backports.tarfile

echo.
echo Installing PyInstaller...
%PYTHON% -m pip install pyinstaller

echo.
echo Cleaning old build files...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del %SCRIPT:.py=.spec% 2>nul

echo.
echo ===========================================
echo           BUILDING EXE NOW...
echo ===========================================

%PYTHON% -m PyInstaller ^
    --onefile ^
    --windowed ^
    --clean ^
    --noupx ^
    --noconfirm ^
    --collect-all mediapipe ^
    --collect-all cv2 ^
    --collect-all numpy ^
    --add-data "assets;assets" ^
    %SCRIPT%

echo.
echo ===========================================
echo              BUILD COMPLETE!
echo EXE is located in: dist\%SCRIPT:.py=.exe%
echo ===========================================
pause
