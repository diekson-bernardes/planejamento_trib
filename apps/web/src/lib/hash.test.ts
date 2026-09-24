import { describe, expect, it } from "vitest";

import { sha256Hex } from "@/lib/hash";

describe("sha256Hex", () => {
  it("calcula o SHA-256 conhecido de 'abc'", async () => {
    const data = new TextEncoder().encode("abc");
    expect(await sha256Hex(data.buffer as ArrayBuffer)).toBe(
      "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    );
  });

  it("aceita Blob (arquivo do navegador)", async () => {
    const blob = new Blob(["abc"], { type: "application/pdf" });
    expect(await sha256Hex(blob)).toBe("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  });
});
