FROM python:3.9

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=reviews_dashboard.settings
ENV PYTHONUNBUFFERED=1

RUN python manage.py migrate

# use Daphne for WS + HTTP
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "reviews_dashboard.asgi:application"]
