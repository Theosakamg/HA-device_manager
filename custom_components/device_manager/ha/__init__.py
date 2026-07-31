"""Home Assistant integration glue for Device Manager.

Adapters that bridge the integration to Home Assistant internals: runtime
service registration and device-registry lookups. This layer depends on the
managers and persistence layers, keeping HA-specific concerns out of them.
"""
