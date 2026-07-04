@echo off
echo.
echo ==========================================
echo   ResumeForge - First Time Setup
echo   Run this ONCE before using the tool
echo ==========================================
echo.

echo [1/2] Installing required Python packages...
pip install flask lxml docx2pdf pypdf

echo.
echo [2/2] Verifying installation...
python -c "import flask, lxml, docx2pdf, pypdf; print('All packages OK')"

echo.
echo ==========================================
echo   Setup Complete!
echo   You can now double-click launch.bat
echo   to open ResumeForge anytime.
echo ==========================================
echo.
pause

