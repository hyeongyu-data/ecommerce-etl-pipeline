# 로컬 개발용 Airflow 이미지. 공식 이미지에 DAG 런타임 의존성만 얹는다.
# 의존성은 pyproject.toml [project] dependencies 에서 관리한다.
ARG AIRFLOW_VERSION=2.10.3
FROM apache/airflow:${AIRFLOW_VERSION}

COPY pyproject.toml /opt/airflow/pyproject.toml
RUN pip install --no-cache-dir /opt/airflow
