"""Firmware layer for Device Manager.

Groups device logic by firmware (``tasmota``, ``wled``, ``zigbee``). Each
firmware package is split by treatment (``provision``, ``update``,
``maintenance``) and shares firmware-agnostic abstractions from ``base``.
Firmware modules depend on ``persistence`` and ``dto`` only.
"""
