from fastapi import FastAPI

from router import payment


app = FastAPI()

app.include_router(payment)