# Custom Airflow image for TC-Analog Monitor (Team 4)
# Base: official Apache Airflow 2.10.5 image, Python 3.12.
FROM apache/airflow:2.10.5-python3.12

ARG AIRFLOW_VERSION=2.10.5
ARG PYTHON_VERSION=3.12

COPY requirements-airflow.txt /requirements-airflow.txt

# Install the pipeline dependencies against the official constraints file, so that
# pip never upgrades a package Airflow itself depends on.
RUN pip install --no-cache-dir \
      "apache-airflow==${AIRFLOW_VERSION}" \
      -r /requirements-airflow.txt \
      --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
