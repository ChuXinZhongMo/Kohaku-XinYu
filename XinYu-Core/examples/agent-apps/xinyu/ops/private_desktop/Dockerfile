# XinYu private ISOLATED desktop image.
#
# A local, owner-built image (NOT an arbitrary prebuilt desktop image) so the
# supply chain is auditable. Base is pinned by digest. Everything installed here
# runs only inside XinYu's isolated container — never on the owner's host.
#
# Components: XFCE (desktop), TigerVNC/x11vnc (VNC), noVNC + websockify (HTML5
# live view over loopback HTTP), xdotool (action injection), imagemagick
# (frame capture), firefox-esr (a browser inside the isolated desktop).
#
# Build:  docker build -t xinyu/private-desktop:1 ops/private_desktop
# All runtime ports are bound to 127.0.0.1 by the host launcher, not here.

FROM debian:bookworm-slim@sha256:0104b334637a5f19aa9c983a91b54c89887c0984081f2068983107a6f6c21eeb

ENV DEBIAN_FRONTEND=noninteractive

# Resilience for slow/flaky links: retry fetches and use long timeouts so a
# transient stall does not abort the whole layer.
RUN printf 'Acquire::Retries "8";\nAcquire::http::Timeout "180";\nAcquire::https::Timeout "180";\n' \
      > /etc/apt/apt.conf.d/80-xinyu-retries

# Minimal XFCE desktop + VNC + noVNC + action/capture tools. No browser in the
# first landing (added later "if needed") to keep the image small over a slow link.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      xfce4 \
      xfce4-terminal \
      xvfb \
      x11vnc \
      x11-utils \
      xdotool \
      imagemagick \
      novnc \
      websockify \
      dbus-x11 \
      ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# noVNC ships its client under /usr/share/novnc; expose vnc.html as index.
RUN if [ -f /usr/share/novnc/vnc.html ] && [ ! -f /usr/share/novnc/index.html ]; then \
      ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html; \
    fi

COPY entrypoint.sh /usr/local/bin/xinyu-desktop-entrypoint.sh
RUN chmod +x /usr/local/bin/xinyu-desktop-entrypoint.sh

EXPOSE 5900 6080
ENTRYPOINT ["/usr/local/bin/xinyu-desktop-entrypoint.sh"]
