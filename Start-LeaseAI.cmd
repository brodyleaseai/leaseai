@echo off
cd /d "%~dp0"
echo Starting LeaseAI at http://localhost:8501
echo If a browser window does not open, paste that URL into Chrome or Edge.
start "" "http://localhost:8501"
streamlit run Home.py --server.enableCORS=true --server.headless=false --server.address=localhost --server.port=8501
