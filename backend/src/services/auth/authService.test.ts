import assert from "node:assert/strict";
import { describe, it, before } from "node:test";
import { authService } from "../auth/authService.js";
import { databaseService } from "../database/databaseService.js";

describe("portal auth", () => {
  before(async () => {
    await databaseService.init();
  });

  it("registers and logs in a user with default prefs", async () => {
    const email = `user_${Date.now()}@example.com`;
    const reg = await authService.register({
      email,
      password: "secret12",
      name: "Tester",
    });
    assert.ok(reg.token);
    assert.equal(reg.user.email, email);

    const login = await authService.login({ email, password: "secret12" });
    assert.equal(login.user.id, reg.user.id);

    const prefs = await databaseService.getPrefs(login.user.id);
    assert.ok(prefs);
    assert.equal(prefs?.role, "Software Engineer");
    assert.equal(prefs?.location, "Hyderabad");
  });
});
