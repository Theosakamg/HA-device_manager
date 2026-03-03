import { describe, it, expect } from "vitest";
import { computeDerivedFields } from "../utils/computed-fields";
import { normalizeFunction, normalizeFirmware } from "../utils/normalizers";
import type { DmDevice, ComputedDeviceFields } from "../types/device";
import devices from "./fixtures/devices.json";

type DeviceFixture = Partial<DmDevice> & { expected: ComputedDeviceFields };

describe("computeDerivedFields", () => {
  it("computes hostname, mqttTopic, link and fqdn correctly for fixtures", () => {
    for (const d of devices as DeviceFixture[]) {
      // persisted fields must remain present
      expect(d.mac).toBeTruthy();

      const result = computeDerivedFields(d);
      const exp = d.expected;
      expect(result.hostname).toEqual(exp.hostname);
      expect(result.mqttTopic).toEqual(exp.mqttTopic);
      expect(result.link).toEqual(exp.link);
      expect(result.fqdn).toEqual(exp.fqdn);
      expect(result.countTopic).toEqual(exp.countTopic);
    }
  });
});

describe("normalizers", () => {
  it("normalizeFunction accepts known functions and slugifies others", () => {
    expect(normalizeFunction("Button")).toEqual("button");
    expect(normalizeFunction("DoorBell")).toEqual("doorbell");
    expect(normalizeFunction("Unknown Func")).toEqual("unknown-func");
  });

  it("normalizeFirmware normalizes known firmware names", () => {
    expect(normalizeFirmware("Tasmota")).toEqual("tasmota");
    expect(normalizeFirmware("Embedded")).toEqual("embeded");
    expect(normalizeFirmware("WLED")).toEqual("wled");
    expect(normalizeFirmware("Some FW")).toEqual("some-fw");
  });
});
