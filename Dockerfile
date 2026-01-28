FROM python:3.11-slim

WORKDIR /app

COPY src/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app

ENV PORT=10000
EXPOSE 10000

CMD ["python","mine_armour_dashboard.py"]
