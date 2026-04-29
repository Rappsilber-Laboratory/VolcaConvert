#!/bin/sh
envsubst '${API_URL}' < /usr/share/nginx/html/script.js.template > /usr/share/nginx/html/script.js
