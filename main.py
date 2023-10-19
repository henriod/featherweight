import asyncio
import logging
import subprocess
from datetime import datetime
import time

import redis.asyncio as redis
import uvicorn
from fastapi import Depends, FastAPI, Header, Response, status, BackgroundTasks
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel

from typing import Optional, List, Union, Any

from config import settings

app = FastAPI(dependencies=[Depends(RateLimiter(times=1, seconds=5))])
logger = logging.getLogger(__name__)
# .env variables can be validated and accessed from the config, here to set a log level
logging.basicConfig(level=settings.LOG_LEVEL.upper())


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str

class C2BMpesaRequest(BaseModel):
    TransactionType: str
    TransID: str
    TransTime: str
    TransAmount: float
    BusinessShortCode: str
    BillRefNumber: str
    InvoiceNumber: str
    OrgAccountBalance: float
    ThirdPartyTransID: str
    MSISDN: str
    FirstName: str
    MiddleName: str
    LastName: str


class PaymentConfirmation(BaseModel):
    receipt_id: Optional[int]
    success: bool = False
    errors: Optional[List[str]]


class PaymentConfirmationResponse(BaseModel):
    ResultCode: str = "0"
    ResultDesc: str = "Accepted"


def create_receipt(c2b_mpesa_request: C2BMpesaRequest, transaction_date: str):

    # perform system related events here e.g. create the receipt:

    receipt = {}

    return receipt


@app.get("/")
def root():
    # endpoints can be marked as `async def` if they do async work, otherwise use `def`
    # which will make the request run on a thread "awaited"
    return {"message": "Hello world. Welcome to FastAPI!"}


@app.get("/user", response_model=UserResponse)
def current_user():
    # this endpoint's repsonse will match the UserResponse model
    return {
        "user_id": "0123456789",
        "email": "me@kylegill.com",
        "name": "Kyle Gill",
        "extra_field_ignored_by_model": "This field is ignored by the response model",
    }


@app.get("/cached", response_model=UserResponse)
@cache(expire=30)  # cache for 30 seconds
async def cached():
    # for demonstration purposes, this is a slow endpoint that waits 5 seconds
    await asyncio.sleep(5)
    return {
        "user_id": "0123456789",
        "email": "cached@kylegill.com",
        "name": "Kyle Gill",
    }


@app.on_event("startup")
async def startup():
    redis_url = f"redis://{settings.REDISUSER}:{settings.REDISPASSWORD}@{settings.REDISHOST}:{settings.REDISPORT}"
    try:
        red = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(red)
    except Exception:
        raise Exception(
            "Redis connection failed, ensure redis is running on the default port 6379"
        )

    FastAPICache.init(RedisBackend(red), prefix="fastapi-cache")


@app.middleware("http")
async def time_request(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["Server-Timing"] = str(process_time)
    logger.info(f"{request.method} {round(process_time, 5)}s {request.url}")
    return response

@app.post("/receipts/c2b-payment-confirmation", tags=["Receipts"], response_model=PaymentConfirmation)
async def c2b_mpesa_confirmation_resource(
    background_tasks: BackgroundTasks, 
    response: Response, 
    c2b_mpesa_request: Any = Body(None)
    ):

    # log time
    # start = time.perf_counter()

    # # check transaction time:
    # # default date time:
    # transaction_date_time = (datetime.today()).strftime('%Y-%m-%d %H:%M')
    # transaction_date = (datetime.today()).strftime('%Y-%m-%d')

    # try:
    #     mpesa_request_time = datetime.strptime(c2b_mpesa_request.TransTime, "%Y%m%d%H%M%S").date()
    #     transaction_date_time = mpesa_request_time.strftime('%Y-%m-%d %H:%M')
    #     transaction_date = mpesa_request_time.strftime('%Y-%m-%d')

    # except ValueError as e:
    #     error_on_date_conversion = f"M-Pesa Date conversion error: Date:{c2b_mpesa_request.TransTime} does not conform to %d %b %Y"

    payment_confirmation = PaymentConfirmation()
    logger.warning("=------------",c2b_mpesa_request)

    # # check if request invoice number is numeric:
    # if c2b_mpesa_request.BillRefNumber.isnumeric():
    #     # do validation here:
    #     # then:
    #     receipt = create_receipt(c2b_mpesa_request, transaction_date)
    #     # Save data in Redis
    #     redis_url = f"redis://{settings.REDISUSER}:{settings.REDISPASSWORD}@{settings.REDISHOST}:{settings.REDISPORT}"
    #     red = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    #     await red.set(f'receipt:{receipt.id}', receipt.json())

    # else:

    #     # value supplied was not an integer, do alphanumeric validation here:

    #     # add receipting creation code:
    #     # create the receipt object:
    #     receipt = create_receipt(c2b_mpesa_request, transaction_date)
    #     # Save data in Redis
    #     redis_url = f"redis://{settings.REDISUSER}:{settings.REDISPASSWORD}@{settings.REDISHOST}:{settings.REDISPORT}"
    #     red = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    #     await red.set(f'receipt:{c2b_mpesa_request.TransID}', c2b_mpesa_request.json())

    # # performance monitoring
    # request_time = time.perf_counter() - start

    # print(request_time)

    return payment_confirmation

def dev():
    try:
        subprocess.check_output(["redis-cli", "ping"], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        logger.warning(
            "Redis is not already running, have you started it with redis-server?"
        )
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
