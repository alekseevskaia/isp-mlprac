FROM python:3.10

RUN pip install -U pip setuptools wheel

COPY dist/mlcourse_prac-0.1.0-py3-none-any.whl /mlcourse_prac-0.1.0-py3-none-any.whl
RUN pip install /mlcourse_prac-0.1.0-py3-none-any.whl

CMD mlcourse-server
