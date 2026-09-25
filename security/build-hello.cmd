@echo off
setlocal
set "framework=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319"
set "runtime=%WINDIR%\Microsoft.NET\assembly\GAC_MSIL\System.Runtime\v4.0_4.0.0.0__b03f5f7f11d50a3a\System.Runtime.dll"
"%framework%\csc.exe" /nologo /target:exe /out:"%~dp0HelloVerifier.exe" /r:"%WINDIR%\System32\WinMetadata\Windows.Security.winmd" /r:"%WINDIR%\System32\WinMetadata\Windows.Foundation.winmd" /r:"%framework%\System.Runtime.WindowsRuntime.dll" /r:"%runtime%" "%~dp0HelloVerifier.cs"
exit /b %errorlevel%
