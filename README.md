```bash
pip install -r requirements.txt
pip install manim-voiceover[all]
pip install -U python-dotenv tiktoken openai
```

* 运行后端
```bash
cd ai_tutor
python -m uvicorn server.api:app --port 9501 --host 0.0.0.0 --workers 4
```

* 运行cli前端
```bash
cd ai_tutor
python apps/art_cli.py --message {your_message}
```
