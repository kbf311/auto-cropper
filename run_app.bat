@echo off
cd /d %~dp0

:: 1. 仮想環境の有効化
call venv\Scripts\activate

:: 2. Python スクリプトを実行
python auto_cropper.py

pause