FROM nginx:alpine

COPY index.html /usr/share/nginx/html/
COPY style.css /usr/share/nginx/html/
COPY script.js.template /usr/share/nginx/html/
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Copy the substitution script and make it executable
COPY substitute_env.sh /docker-entrypoint.d/30-substitute_env.sh
RUN chmod +x /docker-entrypoint.d/30-substitute_env.sh

EXPOSE 80
