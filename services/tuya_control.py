import tinytuya
from config import DEVICES


def _get_device(name: str) -> tinytuya.OutletDevice:
    cfg = DEVICES[name]
    return tinytuya.OutletDevice(
        dev_id=cfg["dev_id"],
        address=cfg["address"],
        local_key=cfg["local_key"],
        version=cfg["version"],
    )


def turn_on(device: str) -> dict:
    d = _get_device(device)
    d.turn_on()
    return {"device": device, "action": "on", "success": True}


def turn_off(device: str) -> dict:
    d = _get_device(device)
    d.turn_off()
    return {"device": device, "action": "off", "success": True}


def get_status(device: str) -> dict:
    d = _get_device(device)
    data = d.status()
    dps = data.get("dps", {})
    return {
        "device": device,
        "on": dps.get("1", False),
        "voltage_v": round(dps.get("20", 0) / 10, 1),
        "current_ma": dps.get("18", 0),
        "power_w": round(dps.get("19", 0) / 10, 1),
    }


def execute(intent: dict) -> dict:
    device = intent.get("device", "plug")
    action = intent.get("action")

    if device not in DEVICES:
        return {"error": f"Unknown device: {device}"}

    if action == "on":
        return turn_on(device)
    elif action == "off":
        return turn_off(device)
    elif action == "status":
        return get_status(device)
    else:
        return {"error": f"Unknown action: {action}"}
