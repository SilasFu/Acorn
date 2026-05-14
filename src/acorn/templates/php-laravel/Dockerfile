FROM php:{{php_version}}-fpm

RUN apt-get update && apt-get install -y \
    git unzip libpq-dev \
    && docker-php-ext-install pdo pdo_pgsql

COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-dev
COPY . .

EXPOSE {{port}}
CMD ["php", "artisan", "serve", "--host=0.0.0.0", "--port={{port}}"]
