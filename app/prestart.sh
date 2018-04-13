#!/bin/bash

echo Run job to cache data &
flask job_scrap_votd &

echo Run one time workers to handle jobs &
for i in $(seq 1 $NUMBER_OF_WORKERS); do rq worker $QUEUE_NAME -b; done &

echo Run default worker &
rq worker $QUEUE_NAME &

echo Start server &
flask run --host=0.0.0.0 --port=80