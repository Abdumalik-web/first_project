@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Forex tahlil agenti
set PY=py
where py >nul 2>nul || set PY=python

:menu
cls
echo ============================================
echo          FOREX TAHLIL AGENTI
echo ============================================
echo.
echo   1 - Tezkor skaner  (bepul, API kalitsiz)
echo   2 - To'liq tahlil  (Claude + fundamental)
echo   3 - Haftalik hisobot (vault asosida)
echo   0 - Chiqish
echo.
echo   Natija avtomatik Obsidian'da ochiladi.
echo.
set MODE=
set /p MODE=Tanlang [1]: 
if "%MODE%"=="" set MODE=1
if "%MODE%"=="0" exit /b
if "%MODE%"=="3" goto report

set SYM=
set /p SYM=Juftlik, masalan EURUSD, GBPUSD, XAUUSD [EURUSD]: 
if "%SYM%"=="" set SYM=EURUSD
if "%MODE%"=="1" goto quick

set IMG=
echo.
echo Chart rasmi bo'lsa, faylni shu oynaga sichqoncha bilan sudrab tashlang va Enter bosing.
set /p IMG=Rasm yo'q bo'lsa shunchaki Enter: 
if defined IMG (
    %PY% -m agent %SYM% --rasm %IMG%
) else (
    %PY% -m agent %SYM%
)
goto done

:quick
%PY% -m agent %SYM% --offline
goto done

:report
%PY% -m agent hisobot --kun 7

:done
echo.
pause
goto menu
