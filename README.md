**Build Flask App image:**

`docker build --no-cache --pull --rm -t flask-stock-exchange:latest .`

**Run Flask App container:**

`docker run -d -p 80:5000 --name flask-sx flask-stock-exchange`