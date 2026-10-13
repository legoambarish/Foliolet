import json, time
import requests
for model in ['gemma3:4b', 'qwen3:4b']:
    print(time.strftime('%H:%M:%S')+' / warming '+model, flush=True)
    try:
        response=requests.post('http://127.0.0.1:11434/api/generate',json={'model':model,'prompt':'Reply ready.','think':False,'stream':False,'keep_alive':'10m','options':{'num_ctx':8192 if model.startswith('qwen') else 4096,'num_predict':8}},timeout=(5,150))
        response.raise_for_status()
        data=response.json()
        print(json.dumps({'model':model,'load_seconds':data.get('load_duration',0)/1e9,'ready':True}), flush=True)
    except (requests.RequestException,ValueError) as exc:
        print(json.dumps({'model':model,'ready':False,'reason':type(exc).__name__}),flush=True)
# Keep qwen loaded last; one loaded model is configured to protect the 8 GiB budget.
