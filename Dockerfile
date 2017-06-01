FROM python:3 

RUN pip3 install flask requests uwsgi

RUN mkdir -p /usr/app/
COPY . /usr/app/

WORKDIR /usr/app

EXPOSE 80

CMD uwsgi --http-socket :80 --module steamvalue --callable app