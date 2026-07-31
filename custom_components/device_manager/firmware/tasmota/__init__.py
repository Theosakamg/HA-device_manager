"""Tasmota firmware package.

Split by treatment:
  * ``provision``   - deploy-time configuration adapter (:class:`TasmotaAdapter`);
  * ``update``      - OTA firmware upgrade operations;
  * ``maintenance`` - restart, status, AP switching and availability batches.

``client`` provides the shared low-level HTTP/MQTT/DB infrastructure and
``shared`` the pure URL / MQTT-topic helpers used across treatments.
"""
