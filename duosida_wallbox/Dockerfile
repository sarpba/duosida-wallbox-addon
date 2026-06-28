ARG BUILD_FROM=ghcr.io/home-assistant/base:3.22
FROM ${BUILD_FROM}

ARG BUILD_ARCH
ARG BUILD_VERSION
ARG BUILD_DESCRIPTION
ARG BUILD_NAME

LABEL \
  io.hass.name="${BUILD_NAME}" \
  io.hass.description="${BUILD_DESCRIPTION}" \
  io.hass.arch="${BUILD_ARCH}" \
  io.hass.type="addon" \
  io.hass.version="${BUILD_VERSION}"

RUN apk add --no-cache python3

WORKDIR /opt/duosida
COPY duosida_probe.py duosida_web.py ./
COPY web ./web
COPY run.sh /

RUN chmod a+x /run.sh

CMD ["/run.sh"]
