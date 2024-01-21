from fastapi import FastAPI
from celery_module import get_corporates, get_result

app = FastAPI()

@app.get("/get-corporates/")
def start_task():
    task = get_corporates.delay()
    return {"task_id": task.id}

@app.get("/check-task/{task_id}")
def get_task_result(task_id: str):
    result = get_result(task_id)
    if result.ready():
        return {"result": result.get()}
    else:
        return {"status": "still processing"}
