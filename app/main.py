from fastapi import FastAPI

app = FastAPI()


# Example GET route for app
@app.get("/")
def read_root():
    return {"Message": "Hello World! FastAPI is working."}
