export DOMAIN="http://localhost"

python -m uvicorn server.main:app --port 9501 --host 0.0.0.0