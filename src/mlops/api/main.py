from fastapi import FastAPI, UploadFile, File

app = FastAPI()

@app.get("/")
def index():
    return {'Hello':'World!'}

@app.get("/api/v1/recommend/{user_code}")
def get_user(user_code):
    return {"user_code": user_code}
