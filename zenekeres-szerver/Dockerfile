FROM php:8.3-apache
RUN a2enmod headers \
 && printf 'ServerTokens Prod\nServerSignature Off\n<Directory /var/www/html>\n  AllowOverride None\n  Options -Indexes\n  FallbackResource /index.php\n</Directory>\n<FilesMatch "\\.(css|js|png)$">\n  Header set Cache-Control "public, max-age=3600"\n</FilesMatch>\n' > /etc/apache2/conf-enabled/zenekeres.conf \
 && printf 'expose_php = Off\ndisplay_errors = Off\nlog_errors = On\nsession.use_cookies = 0\n' > /usr/local/etc/php/conf.d/zenekeres.ini \
 && mkdir -p /data && chown www-data:www-data /data
COPY public/ /var/www/html/
COPY src/ /var/www/src/
VOLUME /data
HEALTHCHECK --interval=60s --timeout=5s CMD php -r 'exit(@file_get_contents("http://127.0.0.1/egeszseg") ? 0 : 1);'
