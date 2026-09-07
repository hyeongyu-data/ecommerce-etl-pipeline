# 로컬 개발용 Airflow 이미지. 공식 이미지에 DAG 런타임 의존성만 얹는다.
ARG AIRFLOW_VERSION=2.10.3
FROM apache/airflow:${AIRFLOW_VERSION}

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
