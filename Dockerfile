# 로컬 개발용 Airflow 이미지. 공식 이미지에 ecommerce_etl 패키지와 런타임 의존성을 얹는다.
# 의존성은 pyproject.toml [project] dependencies 에서 관리한다.
# dags/ 는 런타임에 bind mount 되지만, dags가 import 하는 ecommerce_etl 은 이미지에 설치돼 있어야 한다.
ARG AIRFLOW_VERSION=2.10.3
FROM apache/airflow:${AIRFLOW_VERSION}

COPY pyproject.toml /opt/airflow/pyproject.toml
COPY src /opt/airflow/src
RUN pip install --no-cache-dir /opt/airflow
