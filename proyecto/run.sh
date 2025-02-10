#!/bin/bash
@echo off

REM Ejecuta el servidor en segundo plano
start python server.py

REM Ejecuta la interfaz de cliente FTP
streamlit run main.py

REM Mata el servidor cuando la interfaz de cliente FTP se cierre
taskkill /f /im python.exe