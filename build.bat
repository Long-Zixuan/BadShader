@echo off
rem Compile every material folder, then package pack\ into BadShader.mcpack.
rem
rem   ColorPostProcessing -> silhouette inversion (isInBlack polygon test)
rem
rem Requires: Python 3.10 + lazurite (pip install lazurite==0.10.0)
rem           env\shaderc.exe + dxc.exe (Windows SDK, for SM60/SM65 DXIL)
cd /d "%~dp0"
if not exist build mkdir build

set "DXC=C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\dxc.exe"
py -3.10 -m lazurite build "%~dp0." --shaderc "%~dp0env\shaderc.exe" --dxc "%DXC%" -o "%~dp0build"
if errorlevel 1 goto :fail

powershell -ExecutionPolicy Bypass -File "%~dp0package.ps1"
if errorlevel 1 goto :fail

echo.
echo Done. Install BadShader.mcpack as a resource pack.
goto :eof

:fail
echo.
echo BUILD FAILED
exit /b 1
