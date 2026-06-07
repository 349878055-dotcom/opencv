"""认证 API — 客户注册/登录/验证 token。"""
from __future__ import annotations

from serve_workbench import Route, Handler


@Route.post("/api/auth/register")
def auth_register(self: Handler, body: bytes):
    """注册新客户账号。"""
    from gaze_engine._shared.customer_db import create_customer, get_customer
    data = self._read_body(body)
    name = (data.get("display_name") or "").strip()
    password = (data.get("password") or "").strip()
    if not name:
        return self._json({"ok": False, "error": "请输入客户名称"}, status=400)
    if not password or len(password) < 4:
        return self._json({"ok": False, "error": "密码至少4位"}, status=400)
    cid = create_customer(
        display_name=name,
        contact=data.get("contact", ""),
        preferred_species=data.get("preferred_species", "human"),
        breed=data.get("breed", ""),
        password=password,
    )
    self._json({"ok": True, "customer_id": cid, "customer": get_customer(cid)})


@Route.post("/api/auth/login")
def auth_login(self: Handler, body: bytes):
    """客户登录：验证密码，返回 token。"""
    from gaze_engine._shared.customer_db import (
        get_customer, verify_customer_password, create_auth_token,
        resolve_customer_login,
    )
    data = self._read_body(body)
    login_key = (data.get("customer_id") or "").strip()
    password = (data.get("password") or "").strip()
    if not login_key or not password:
        return self._json({"ok": False, "error": "缺少客户ID或密码"}, status=400)
    cid, resolve_err = resolve_customer_login(login_key)
    if resolve_err:
        return self._json({"ok": False, "error": resolve_err}, status=404)
    customer = get_customer(cid)
    if not customer:
        return self._json({"ok": False, "error": "客户不存在"}, status=404)
    if not verify_customer_password(cid, password):
        return self._json({"ok": False, "error": "密码错误"}, status=403)
    token = create_auth_token(cid)
    self._json({
        "ok": True,
        "token": token,
        "customer_id": cid,
        "customer": customer,
    })


@Route.post("/api/auth/verify")
def auth_verify(self: Handler, body: bytes):
    """验证 token 有效性，返回客户信息。"""
    from gaze_engine._shared.customer_db import verify_auth_token, get_customer
    data = self._read_body(body)
    token = (data.get("token") or "").strip()
    if not token:
        return self._json({"ok": False, "error": "缺少 token"}, status=400)
    cid = verify_auth_token(token)
    if not cid:
        return self._json({"ok": False, "error": "token 无效或已过期"}, status=403)
    customer = get_customer(cid)
    self._json({"ok": True, "customer_id": cid, "customer": customer})
