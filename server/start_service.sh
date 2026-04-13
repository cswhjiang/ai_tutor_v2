export DOMAIN="http://naicha.ai/"

python -m uvicorn server.main:app --port 9501 --host 0.0.0.0 --workers 4