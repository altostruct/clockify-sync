FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN pip3 install -r requirements.txt

COPY src ${LAMBDA_TASK_ROOT}/src
COPY app.py ${LAMBDA_TASK_ROOT}

CMD [ "app.handler" ]
