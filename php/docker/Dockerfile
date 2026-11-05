FROM php:8.3-apache

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      mpv espeak-ng ffmpeg pulseaudio-utils qrencode nodejs python3 python3-venv ca-certificates \
      libsqlite3-dev libicu-dev \
 && docker-php-ext-install pdo_sqlite intl pcntl \
 && python3 -m venv /opt/ytdlp \
 && /opt/ytdlp/bin/pip install --no-cache-dir "yt-dlp[default]==2026.8.19" \
 && ln -s /opt/ytdlp/bin/yt-dlp /usr/local/bin/yt-dlp \
 && apt-get purge -y libsqlite3-dev libicu-dev && apt-get install -y --no-install-recommends libicu76 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -u 1000 -m -s /bin/bash kfm \
 && a2enmod rewrite headers \
 && sed -ri 's#DocumentRoot /var/www/html#DocumentRoot /app/public#' /etc/apache2/sites-available/000-default.conf \
 && printf '<Directory /app/public>\n  AllowOverride All\n  Require all granted\n</Directory>\nServerTokens Prod\nServerSignature Off\n' \
      > /etc/apache2/conf-enabled/kozgazfm.conf \
 && printf 'upload_max_filesize=32M\npost_max_size=34M\nexpose_php=Off\ndate.timezone=Europe/Budapest\nsession.save_path=/adat/munkamenetek\nsession.cookie_httponly=1\nsession.cookie_samesite=Strict\nsession.use_strict_mode=1\n' \
      > /usr/local/etc/php/conf.d/kozgazfm.ini \
 && mkdir -p /home/kfm/.config/yt-dlp && printf -- '--js-runtimes node\n' > /home/kfm/.config/yt-dlp/config \
 && chown -R kfm:kfm /home/kfm

ENV APACHE_RUN_USER=kfm APACHE_RUN_GROUP=kfm TZ=Europe/Budapest KOZGAZ_FM_ADAT=/adat

COPY --chown=kfm:kfm . /app
WORKDIR /app
