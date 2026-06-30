#!/usr/bin/env python3

import argparse
import json
import socket
import struct
import time
from typing import Dict, Iterable, List, Optional, Tuple


CHARGE_POINT_STATUS = {
    0: "Available",
    1: "Preparing",
    2: "Charging",
    3: "SuspendedEVSE",
    4: "SuspendedEV",
    5: "Finishing",
    6: "Reserved",
    7: "Unavailable",
    8: "Faulted",
}

CHARGE_POINT_ERROR = {
    0: "ConnectorLockFailure",
    1: "EVCommunicationError",
    2: "GroundFailure",
    3: "HighTemperature",
    4: "InternalError",
    5: "LocalListConflict",
    6: "NoError",
    7: "OtherError",
    8: "OverCurrentFailure",
    9: "OverVoltage",
    10: "PowerMeterFailure",
    11: "PowerSwitchFailure",
    12: "ReaderFailure",
    13: "ResetFailure",
    14: "UnderVoltage",
    15: "WeakSignal",
}

MEASURANDS = {
    0: "EnergyActiveExportRegister",
    1: "EnergyActiveImportRegister",
    2: "EnergyReactiveExportRegister",
    3: "EnergyReactiveImportRegister",
    4: "EnergyActiveExportInterval",
    5: "EnergyActiveImportInterval",
    6: "EnergyReactiveExportInterval",
    7: "EnergyReactiveImportInterval",
    8: "PowerActiveExport",
    9: "PowerActiveImport",
    10: "PowerOffered",
    11: "PowerReactiveExport",
    12: "PowerReactiveImport",
    13: "PowerFactor",
    14: "CurrentImport",
    15: "CurrentExport",
    16: "CurrentOffered",
    17: "Voltage",
    18: "Frequency",
    19: "Temperature",
    20: "SoC",
    21: "RPM",
}

READING_CONTEXT = {
    0: "InterruptionBegin",
    1: "InterruptionEnd",
    2: "Other",
    3: "SampleClock",
    4: "SamplePeriodic",
    5: "TransactionBegin",
    6: "TransactionEnd",
    7: "Trigger",
}

SAMPLED_LOCATION = {
    0: "Outlet",
    1: "Cable",
    2: "EV",
    3: "Inlet",
    4: "Body",
}

UNIT_OF_MEASURE = {
    0: "Wh",
    1: "kWh",
    4: "W",
    5: "kW",
    10: "A",
    11: "V",
    12: "Celsius",
    15: "Percent",
}

STATE_KEY_BY_MEASURAND = {
    "CurrentImport": "current_import",
    "CurrentOffered": "current_offered",
    "EnergyActiveImportInterval": "energy_active_import_interval",
    "EnergyActiveImportRegister": "energy_active_import_register",
    "Frequency": "frequency",
    "PowerActiveImport": "power_active_import",
    "PowerFactor": "power_factor",
    "Temperature": "temperature",
    "Voltage": "voltage",
}


TRIGGER_MESSAGE = {
    0: "BootNotification",
    1: "DiagnosticsStatusNotification",
    2: "FirmwareStatusNotification",
    3: "Heartbeat",
    4: "MeterValues",
    5: "StatusNotification",
}

TRIGGER_NAME_TO_VALUE = {
    "boot": 0,
    "diagnostics": 1,
    "firmware": 2,
    "heartbeat": 3,
    "meter-values": 4,
    "status": 5,
}

TRIGGER_MESSAGE_STATUS = {
    0: "Accepted",
    1: "Rejected",
    2: "NotImplemented",
}

DATA_TRANSFER_CASE = {
    3: "Raw",
    4: "DataFirmwareUpgradeInfoReq",
    5: "DataFirmwareUpgradeInfoConf",
    6: "DataFirmwareUpgradeReq",
    7: "DataFirmwareUpgradeConf",
    8: "DataLogBlockReq",
    9: "DataLogBlockConf",
    10: "DataVendorStatusReq",
    11: "DataVendorStatusConf",
    12: "DataContinueReq",
    13: "DataContinueConf",
    14: "DataPullAllConfigurationReq",
    15: "DataPullAllConfigurationConf",
    16: "DataPullAllChargeProfileReq",
    17: "DataPullAllChargeProfileConf",
    18: "DataUpdateToFlashReq",
    19: "DataUpdateToFlashConf",
    20: "DataScanApPointReq",
    21: "DataScanApPointConf",
    22: "DataSwitchWorkModeReq",
    23: "DataSwitchWorkModeConf",
    24: "DataPullAllAuthorizationCacheReq",
    25: "DataPullAllAuthorizationCacheConf",
}

DATA_TRANSFER_STATUS = {
    0: "Accepted",
    1: "Rejected",
    2: "UnknownMessageId",
    3: "UnknownVendorId",
}

CONFIGURATION_STATUS = {
    0: "Accepted",
    1: "Rejected",
    2: "RebootRequired",
    3: "NotSupported",
}

REMOTE_START_STOP_STATUS = {
    0: "Accepted",
    1: "Rejected",
}

OCPP_CASE = {
    1: "AuthorizeConf",
    2: "AuthorizeReq",
    3: "BootNotificationConf",
    4: "BootNotificationReq",
    9: "ChangeConfigurationConf",
    10: "ChangeConfigurationReq",
    15: "DataTransferConf",
    16: "DataTransferReq",
    23: "GetConfigurationConf",
    24: "GetConfigurationReq",
    29: "HeartbeatConf",
    30: "HeartbeatReq",
    31: "MeterValuesConf",
    32: "MeterValuesReq",
    33: "RemoteStartTransactionConf",
    34: "RemoteStartTransactionReq",
    35: "RemoteStopTransactionConf",
    36: "RemoteStopTransactionReq",
    45: "StartTransactionConf",
    46: "StartTransactionReq",
    47: "StatusNotificationConf",
    48: "StatusNotificationReq",
    49: "StopTransactionConf",
    50: "StopTransactionReq",
    51: "TriggerMessageConf",
    52: "TriggerMessageReq",
}


def read_varint(buf: bytes, offset: int) -> Tuple[int, int]:
    shift = 0
    value = 0
    while True:
        if offset >= len(buf):
            raise ValueError("truncated varint")
        byte = buf[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return value, offset
        shift += 7
        if shift > 63:
            raise ValueError("varint too large")


def encode_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("negative varint is not supported")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def encode_field_varint(field: int, value: int) -> bytes:
    return encode_varint((field << 3) | 0) + encode_varint(value)


def encode_field_sint64(field: int, value: int) -> bytes:
    zigzag = (value << 1) ^ (value >> 63)
    return encode_varint((field << 3) | 0) + encode_varint(zigzag)


def encode_field_fixed32_float(field: int, value: float) -> bytes:
    return encode_varint((field << 3) | 5) + struct.pack("<f", value)


def encode_field_len(field: int, value: bytes) -> bytes:
    return encode_varint((field << 3) | 2) + encode_varint(len(value)) + value


def parse_message(buf: bytes) -> List[Tuple[int, int, object]]:
    fields: List[Tuple[int, int, object]] = []
    offset = 0
    while offset < len(buf):
        tag, offset = read_varint(buf, offset)
        field = tag >> 3
        wire_type = tag & 0x07
        if wire_type == 0:
            value, offset = read_varint(buf, offset)
        elif wire_type == 1:
            if offset + 8 > len(buf):
                raise ValueError("truncated fixed64")
            value = buf[offset : offset + 8]
            offset += 8
        elif wire_type == 2:
            length, offset = read_varint(buf, offset)
            if offset + length > len(buf):
                raise ValueError("truncated len field")
            value = buf[offset : offset + length]
            offset += length
        elif wire_type == 5:
            if offset + 4 > len(buf):
                raise ValueError("truncated fixed32")
            value = buf[offset : offset + 4]
            offset += 4
        else:
            raise ValueError(f"unsupported wire type {wire_type}")
        fields.append((field, wire_type, value))
    return fields


def safe_utf8(value: bytes) -> Optional[str]:
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if all(b in (9, 10, 13) or 32 <= b < 127 for b in value):
        return text
    return None


def fixed32_float(value: object) -> float:
    return struct.unpack("<f", value)[0]  # type: ignore[arg-type]


def fixed64_u64(value: object) -> int:
    return struct.unpack("<Q", value)[0]  # type: ignore[arg-type]


def decode_boot_notification_req(payload: bytes) -> Dict[str, object]:
    names = {
        1: "chargeBoxSerialNumber",
        2: "chargePointModel",
        3: "chargePointSerialNumber",
        4: "chargePointVendor",
        5: "firmwareVersion",
        6: "iccid",
        7: "imsi",
        8: "meterSerialNumber",
        9: "meterType",
    }
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if wire_type == 2 and field in names:
            out[names[field]] = safe_utf8(value) or value.hex()  # type: ignore[arg-type]
    return out


def decode_trigger_message_req(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if wire_type != 0:
            continue
        if field == 1:
            out["requestedMessage"] = TRIGGER_MESSAGE.get(value, value)
        elif field == 2:
            out["connectorId"] = value
    return out


def decode_trigger_message_conf(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if field == 1 and wire_type == 0:
            out["status"] = TRIGGER_MESSAGE_STATUS.get(value, value)
    return out


def decode_remote_start_transaction_req(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if field == 1 and wire_type == 0:
            out["connectorId"] = value
        elif field == 2 and wire_type == 2:
            out["idTag"] = safe_utf8(value) or value.hex()  # type: ignore[arg-type]
    return out


def decode_remote_stop_transaction_req(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if field == 1 and wire_type == 0:
            out["transactionId"] = value
    return out


def decode_remote_start_stop_conf(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if field == 1 and wire_type == 0:
            out["status"] = REMOTE_START_STOP_STATUS.get(value, value)
    return out


def decode_change_configuration_req(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if wire_type != 2:
            continue
        text = safe_utf8(value) or value.hex()  # type: ignore[arg-type]
        if field == 1:
            out["key"] = text
        elif field == 2:
            out["value"] = text
    return out


def decode_change_configuration_conf(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if field == 1 and wire_type == 0:
            out["status"] = CONFIGURATION_STATUS.get(value, value)
    return out


def decode_status_notification_req(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if wire_type == 0:
            if field == 1:
                out["connectorId"] = value
            elif field == 2:
                out["errorCode"] = CHARGE_POINT_ERROR.get(value, value)
            elif field == 4:
                out["status"] = CHARGE_POINT_STATUS.get(value, value)
            elif field == 5:
                out["timestamp"] = value
        elif wire_type == 2:
            text = safe_utf8(value) or value.hex()  # type: ignore[arg-type]
            if field == 3:
                out["info"] = text
            elif field == 6:
                out["vendorId"] = text
            elif field == 7:
                out["vendorErrorCode"] = text
    return out


def decode_sampled_value(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if field == 1 and wire_type == 2:
            out["value"] = safe_utf8(value) or value.hex()  # type: ignore[arg-type]
        elif field == 2 and wire_type == 0:
            out["context"] = READING_CONTEXT.get(value, value)
        elif field == 4 and wire_type == 0:
            out["measurand"] = MEASURANDS.get(value, value)
        elif field == 6 and wire_type == 0:
            out["location"] = SAMPLED_LOCATION.get(value, value)
        elif field == 7 and wire_type == 0:
            out["unit"] = UNIT_OF_MEASURE.get(value, value)
    return out


def decode_meter_value(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {"sampledValues": []}
    sampled_values: List[Dict[str, object]] = out["sampledValues"]  # type: ignore[assignment]
    for field, wire_type, value in parse_message(payload):
        if field == 1 and wire_type == 0:
            out["timestamp"] = value
        elif field == 2 and wire_type == 2:
            sampled_values.append(decode_sampled_value(value))  # type: ignore[arg-type]
    return out


def decode_meter_values_req(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {"meterValues": []}
    meter_values: List[Dict[str, object]] = out["meterValues"]  # type: ignore[assignment]
    for field, wire_type, value in parse_message(payload):
        if field == 1 and wire_type == 0:
            out["connectorId"] = value
        elif field == 2 and wire_type == 0:
            out["transactionId"] = value
        elif field == 3 and wire_type == 2:
            meter_values.append(decode_meter_value(value))  # type: ignore[arg-type]
    return out


def decode_data_vendor_status_req(payload: bytes) -> Dict[str, object]:
    names = {
        1: ("voltage", "float"),
        2: ("current", "float"),
        3: ("energy", "float"),
        4: ("accEnergy", "float"),
        5: ("power", "float"),
        6: ("powerFactor", "float"),
        7: ("freq", "float"),
        8: ("temp", "float"),
        9: ("cpHigh", "float"),
        10: ("cpFreq", "float"),
        11: ("cpDuty", "float"),
        12: ("cpState", "int"),
        13: ("otempA", "float"),
        14: ("otempB", "float"),
        15: ("brd12V", "float"),
        16: ("brd5V", "float"),
        17: ("status", "status"),
        18: ("transactionStart", "int"),
        19: ("transactionStop", "int"),
        20: ("timestamp", "int"),
        21: ("transactionId", "int"),
        22: ("idTag", "str"),
        23: ("vendorInfo", "str"),
    }
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        spec = names.get(field)
        if spec is None:
            continue
        name, kind = spec
        if kind == "float" and wire_type == 5:
            out[name] = fixed32_float(value)
        elif kind == "int" and wire_type == 0:
            out[name] = value
        elif kind == "status" and wire_type == 0:
            out[name] = CHARGE_POINT_STATUS.get(value, value)
        elif kind == "str" and wire_type == 2:
            out[name] = safe_utf8(value) or value.hex()  # type: ignore[arg-type]
    return out


def decode_data_pull_all_configuration_conf(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    field_names = {
        1: ("maxWorkTemp", "float"),
        2: ("maxWorkVoltage", "float"),
        3: ("maxWorkCurrent", "float"),
        4: ("minWorkVoltage", "float"),
        5: ("screenSensitivity", "sint"),
        6: ("wifiApSsid", "str"),
        7: ("wifiApPass", "str"),
        8: ("wifiStaSsid", "str"),
        9: ("wifiStaPass", "str"),
        10: ("directWorkMode", "bool"),
        11: ("utcOffset", "sint"),
        12: ("connectServer", "bool"),
        19: ("heartbeatInterval", "int"),
        22: ("meterValuesAlignedData", "str"),
        23: ("meterValuesSampledDataList", "str"),
        24: ("meterValueSampleInterval", "int"),
        32: ("supportedFeatureProfiles", "str"),
        45: ("chargepointName", "str"),
        46: ("maxWhPerCharge", "int"),
    }
    for field, wire_type, value in parse_message(payload):
        spec = field_names.get(field)
        if spec is None:
            continue
        name, kind = spec
        if kind == "float" and wire_type == 5:
            out[name] = fixed32_float(value)
        elif kind == "str" and wire_type == 2:
            out[name] = safe_utf8(value) or value.hex()  # type: ignore[arg-type]
        elif kind == "bool" and wire_type == 0:
            out[name] = bool(value)
        elif kind == "int" and wire_type == 0:
            out[name] = value
        elif kind == "sint" and wire_type == 0:
            out[name] = (value >> 1) ^ -(value & 1)
    return out


def decode_data_transfer_conf(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if field == 1 and wire_type == 0:
            out["status"] = DATA_TRANSFER_STATUS.get(value, value)
        elif wire_type == 2:
            case_name = DATA_TRANSFER_CASE.get(field, f"Field{field}")
            out["dataCase"] = case_name
            if field == 15:
                out["data"] = decode_data_pull_all_configuration_conf(value)  # type: ignore[arg-type]
            else:
                out["data"] = {"rawHex": value.hex()}  # type: ignore[arg-type]
    return out


def decode_data_transfer_req(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if field == 1 and wire_type == 2:
            out["vendorId"] = safe_utf8(value) or value.hex()  # type: ignore[arg-type]
        elif field == 2 and wire_type == 2:
            out["messageId"] = safe_utf8(value) or value.hex()  # type: ignore[arg-type]
        elif wire_type == 2:
            case_name = DATA_TRANSFER_CASE.get(field, f"Field{field}")
            out["dataCase"] = case_name
            if field == 10:
                out["data"] = decode_data_vendor_status_req(value)  # type: ignore[arg-type]
            else:
                out["data"] = {"rawHex": value.hex()}  # type: ignore[arg-type]
    return out


def decode_ocpp_message(payload: bytes) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for field, wire_type, value in parse_message(payload):
        if field == 100 and wire_type == 2:
            out["clientId"] = safe_utf8(value) or value.hex()  # type: ignore[arg-type]
        elif field == 101 and wire_type == 0:
            out["messageId"] = value
        elif wire_type == 2 and field in OCPP_CASE:
            case_name = OCPP_CASE[field]
            out["dataCase"] = case_name
            if field == 4:
                out["data"] = decode_boot_notification_req(value)  # type: ignore[arg-type]
            elif field == 9:
                out["data"] = decode_change_configuration_conf(value)  # type: ignore[arg-type]
            elif field == 10:
                out["data"] = decode_change_configuration_req(value)  # type: ignore[arg-type]
            elif field == 15:
                out["data"] = decode_data_transfer_conf(value)  # type: ignore[arg-type]
            elif field == 16:
                out["data"] = decode_data_transfer_req(value)  # type: ignore[arg-type]
            elif field == 32:
                out["data"] = decode_meter_values_req(value)  # type: ignore[arg-type]
            elif field == 33:
                out["data"] = decode_remote_start_stop_conf(value)  # type: ignore[arg-type]
            elif field == 34:
                out["data"] = decode_remote_start_transaction_req(value)  # type: ignore[arg-type]
            elif field == 35:
                out["data"] = decode_remote_start_stop_conf(value)  # type: ignore[arg-type]
            elif field == 36:
                out["data"] = decode_remote_stop_transaction_req(value)  # type: ignore[arg-type]
            elif field == 48:
                out["data"] = decode_status_notification_req(value)  # type: ignore[arg-type]
            elif field == 52:
                out["data"] = decode_trigger_message_req(value)  # type: ignore[arg-type]
            elif field == 51:
                out["data"] = decode_trigger_message_conf(value)  # type: ignore[arg-type]
            else:
                out["data"] = {"rawHex": value.hex()}  # type: ignore[arg-type]
    return out


def format_decoded(obj: object, indent: int = 0) -> List[str]:
    prefix = "  " * indent
    lines: List[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(format_decoded(value, indent + 1))
            else:
                lines.append(f"{prefix}{key}: {value}")
        return lines
    if isinstance(obj, list):
        for index, value in enumerate(obj):
            lines.append(f"{prefix}- item {index + 1}:")
            lines.extend(format_decoded(value, indent + 1))
        return lines
    lines.append(f"{prefix}{obj}")
    return lines


def to_number(value: object) -> object:
    if not isinstance(value, str):
        return value
    try:
        parsed = float(value)
    except ValueError:
        return value
    if parsed.is_integer():
        return int(parsed)
    return parsed


def update_state_from_decoded(decoded: Dict[str, object], state: Dict[str, object]) -> None:
    data_case = decoded.get("dataCase")
    data = decoded.get("data")
    if not isinstance(data, dict):
        return

    if data_case == "BootNotificationReq":
        state["client_id"] = decoded.get("clientId")
        for key in (
            "chargePointModel",
            "chargePointSerialNumber",
            "chargePointVendor",
            "firmwareVersion",
        ):
            if key in data:
                state[key] = data[key]
        return

    if data_case == "StatusNotificationReq":
        for key, value in data.items():
            state[f"status_{key}"] = value
        return

    if data_case == "ChangeConfigurationConf":
        for key, value in data.items():
            state[f"change_configuration_{key}"] = value
        return

    if data_case == "RemoteStartTransactionConf":
        for key, value in data.items():
            state[f"remote_start_{key}"] = value
        return

    if data_case == "RemoteStopTransactionConf":
        for key, value in data.items():
            state[f"remote_stop_{key}"] = value
        return

    if data_case == "MeterValuesReq":
        if "connectorId" in data:
            state["connector_id"] = data["connectorId"]
        if "transactionId" in data:
            state["transaction_id"] = data["transactionId"]
        for meter_value in data.get("meterValues", []):
            if not isinstance(meter_value, dict):
                continue
            if "timestamp" in meter_value:
                state["meter_timestamp"] = meter_value["timestamp"]
            for sampled in meter_value.get("sampledValues", []):
                if not isinstance(sampled, dict):
                    continue
                measurand = sampled.get("measurand")
                if not isinstance(measurand, str):
                    continue
                key = STATE_KEY_BY_MEASURAND.get(measurand)
                if key is None:
                    continue
                state[key] = to_number(sampled.get("value"))
                unit = sampled.get("unit")
                if unit:
                    state[f"{key}_unit"] = unit
        return

    if data_case == "DataTransferReq":
        if data.get("dataCase") == "DataVendorStatusReq" and isinstance(data.get("data"), dict):
            for key, value in data["data"].items():  # type: ignore[index]
                state[f"vendor_{key}"] = value
        return

    if data_case == "DataTransferConf":
        if data.get("dataCase") == "DataPullAllConfigurationConf" and isinstance(data.get("data"), dict):
            config = data["data"]  # type: ignore[index]
            for key in (
                "heartbeatInterval",
                "meterValueSampleInterval",
                "maxWorkCurrent",
                "maxWorkVoltage",
                "minWorkVoltage",
                "maxWorkTemp",
            ):
                if key in config:
                    state[f"config_{key}"] = config[key]


def build_state(chunks: Iterable[bytes]) -> Dict[str, object]:
    state: Dict[str, object] = {}
    for chunk in chunks:
        try:
            decoded = decode_ocpp_message(chunk)
        except ValueError:
            continue
        update_state_from_decoded(decoded, state)
    return state


def wrap_user_wifi(payload: bytes) -> bytes:
    frame = bytearray(len(payload) + 8)
    frame[0] = 0xAA
    frame[1] = 0xFD
    frame[2] = 0x55
    frame[3] = ((len(payload) + 2) >> 8) & 0xFF
    frame[4] = (len(payload) + 2) & 0xFF
    frame[5] = 0x61
    frame[6] = 0x00
    frame[7 : 7 + len(payload)] = payload
    checksum = 97 + sum(payload)
    frame[-1] = checksum & 0xFF
    return bytes(frame)


def unwrap_user_wifi(buffer: bytearray) -> List[bytes]:
    frames: List[bytes] = []
    offset = 0
    while len(buffer) - offset >= 8:
        if not (
            buffer[offset] == 0x55
            and buffer[offset + 1] == 0xFD
            and buffer[offset + 2] == 0xAA
            and buffer[offset + 5] == 0x61
            and buffer[offset + 6] == 0x00
        ):
            offset += 1
            continue
        declared_len = (buffer[offset + 3] << 8) | buffer[offset + 4]
        total_len = declared_len + 6
        if declared_len < 2:
            offset += 1
            continue
        if len(buffer) - offset < total_len:
            break
        payload_len = declared_len - 2
        payload = bytes(buffer[offset + 7 : offset + 7 + payload_len])
        checksum = buffer[offset + 7 + payload_len]
        expected = (97 + sum(payload)) & 0xFF
        if checksum == expected:
            frames.append(payload)
            offset += total_len
        else:
            offset += 1
    if offset:
        del buffer[:offset]
    return frames


def skip_field(buf: bytearray, offset: int, wire_type: int) -> Optional[int]:
    try:
        if wire_type == 0:
            _, offset = read_varint(buf, offset)
            return offset
        if wire_type == 1:
            return offset + 8 if offset + 8 <= len(buf) else None
        if wire_type == 2:
            length, offset = read_varint(buf, offset)
            return offset + length if offset + length <= len(buf) else None
        if wire_type == 5:
            return offset + 4 if offset + 4 <= len(buf) else None
    except ValueError:
        return None
    return None


def extract_raw_ocpp_messages(buffer: bytearray) -> List[bytes]:
    messages: List[bytes] = []
    start = 0
    offset = 0
    while offset < len(buffer):
        field_start = offset
        try:
            tag, offset = read_varint(buffer, offset)
        except ValueError:
            break
        field = tag >> 3
        wire_type = tag & 0x07
        next_offset = skip_field(buffer, offset, wire_type)
        if next_offset is None:
            offset = field_start
            break
        offset = next_offset
        if field == 101 and wire_type == 0:
            messages.append(bytes(buffer[start:offset]))
            start = offset
    if start:
        del buffer[:start]
    return messages


def build_trigger_message(client_id: str, message_id: int, trigger: int) -> bytes:
    inner = encode_field_varint(1, trigger) + encode_field_varint(2, 1)
    return (
        encode_field_len(52, inner)
        + encode_field_len(100, client_id.encode("utf-8"))
        + encode_field_varint(101, message_id)
    )


def build_trigger_boot(client_id: str, message_id: int) -> bytes:
    return build_trigger_message(client_id, message_id, TRIGGER_NAME_TO_VALUE["boot"])


def build_pull_config(client_id: str, message_id: int) -> bytes:
    inner = (
        encode_field_len(1, b"smartchargepile.x-cheng.com")
        + encode_field_len(2, b"DataPullAllConfigurationReq")
        + encode_field_len(14, b"")
    )
    return (
        encode_field_len(16, inner)
        + encode_field_len(100, client_id.encode("utf-8"))
        + encode_field_varint(101, message_id)
    )


def build_change_configuration(client_id: str, message_id: int, key: str, value: str) -> bytes:
    inner = encode_field_len(1, key.encode("utf-8")) + encode_field_len(2, value.encode("utf-8"))
    return (
        encode_field_len(10, inner)
        + encode_field_len(100, client_id.encode("utf-8"))
        + encode_field_varint(101, message_id)
    )


def build_update_to_flash(client_id: str, message_id: int, update_type: int = 0) -> bytes:
    inner = (
        encode_field_len(1, b"smartchargepile.x-cheng.com")
        + encode_field_len(2, b"DataUpdateToflashReq")
        + encode_field_len(18, encode_field_varint(1, update_type))
    )
    return (
        encode_field_len(16, inner)
        + encode_field_len(100, client_id.encode("utf-8"))
        + encode_field_varint(101, message_id)
    )


def build_remote_start(client_id: str, message_id: int, id_tag: str) -> bytes:
    inner = encode_field_varint(1, 1) + encode_field_len(2, id_tag.encode("utf-8"))
    return (
        encode_field_len(34, inner)
        + encode_field_len(100, client_id.encode("utf-8"))
        + encode_field_varint(101, message_id)
    )


def build_remote_stop(client_id: str, message_id: int, transaction_id: int) -> bytes:
    inner = encode_field_varint(1, transaction_id)
    return (
        encode_field_len(36, inner)
        + encode_field_len(100, client_id.encode("utf-8"))
        + encode_field_varint(101, message_id)
    )


def build_boot_notification_conf_minimal(message_id: int) -> bytes:
    return encode_field_len(3, encode_field_sint64(1, int(time.time()))) + encode_field_varint(101, message_id)


def build_heartbeat_conf(client_id: str, message_id: int) -> bytes:
    inner = encode_field_sint64(1, int(time.time()))
    return (
        encode_field_len(29, inner)
        + encode_field_len(100, client_id.encode("utf-8"))
        + encode_field_varint(101, message_id)
    )


def build_empty_conf(client_id: str, message_field: int, message_id: int) -> bytes:
    return (
        encode_field_len(message_field, b"")
        + encode_field_len(100, client_id.encode("utf-8"))
        + encode_field_varint(101, message_id)
    )


def build_data_vendor_status_conf(client_id: str, message_id: int) -> bytes:
    inner = encode_field_varint(1, 0) + encode_field_len(11, b"")
    return (
        encode_field_len(15, inner)
        + encode_field_len(100, client_id.encode("utf-8"))
        + encode_field_varint(101, message_id)
    )


def maybe_wrap(payload: bytes, transport: str) -> bytes:
    return wrap_user_wifi(payload) if transport == "wrapped" else payload


def build_payload(args: argparse.Namespace) -> bytes:
    if args.mode == "ascii":
        return args.ascii.encode("ascii")
    message_id = args.message_id or int(time.time()) & 0x7FFFFFFF
    if args.mode in {"trigger-boot", "session", "set-max-current"}:
        payload = build_trigger_boot(args.client_id, message_id)
    elif args.mode == "trigger":
        payload = build_trigger_message(args.client_id, message_id, TRIGGER_NAME_TO_VALUE[args.trigger])
    elif args.mode == "pull-config":
        payload = build_pull_config(args.client_id, message_id)
    elif args.mode in {"change-config", "set-max-current-direct"}:
        if args.mode == "set-max-current-direct":
            if args.max_current is None:
                raise ValueError("--max-current is required for mode=set-max-current-direct")
            args.config_key = "VendorMaxWorkCurrent"
            args.config_value = f"{args.max_current:g}"
        if not args.config_key or args.config_value is None:
            raise ValueError(f"--config-key and --config-value are required for mode={args.mode}")
        payload = build_change_configuration(args.client_id, message_id, args.config_key, args.config_value)
    elif args.mode == "start":
        if not args.id_tag:
            raise ValueError("--id-tag is required for mode=start")
        payload = build_remote_start(args.client_id, message_id, args.id_tag)
    elif args.mode == "stop":
        if args.transaction_id is None:
            raise ValueError("--transaction-id is required for mode=stop")
        payload = build_remote_stop(args.client_id, message_id, args.transaction_id)
    else:
        raise ValueError(f"unsupported mode: {args.mode}")
    return maybe_wrap(payload, args.transport)


def build_auto_reply(
    frame: bytes,
    transport: str,
    request_config: bool,
    session_triggers: List[int],
    config_updates: List[Tuple[str, str]],
    persist_config: bool,
) -> List[bytes]:
    replies: List[bytes] = []
    try:
        decoded = decode_ocpp_message(frame)
    except ValueError:
        return replies
    message_id = decoded.get("messageId")
    client_id = decoded.get("clientId")
    if not isinstance(message_id, int):
        return replies
    reply_client_id = client_id if isinstance(client_id, str) else ""
    data_case = decoded.get("dataCase")
    if data_case == "BootNotificationReq":
        if transport == "raw":
            replies.append(build_boot_notification_conf_minimal(message_id))
        else:
            replies.append(maybe_wrap(build_boot_notification_conf_minimal(message_id), transport))
        if request_config:
            follow_client_id = client_id if isinstance(client_id, str) else "From Python"
            next_message_id = message_id + 1
            for key, value in config_updates:
                replies.append(
                    maybe_wrap(
                        build_change_configuration(follow_client_id, next_message_id, key, value),
                        transport,
                    )
                )
                next_message_id += 1
            if persist_config and config_updates:
                replies.append(maybe_wrap(build_update_to_flash(follow_client_id, next_message_id), transport))
                next_message_id += 1
            replies.append(maybe_wrap(build_pull_config(follow_client_id, next_message_id), transport))
            next_message_id += 1
            for index, trigger in enumerate(session_triggers, start=0):
                replies.append(
                    maybe_wrap(
                        build_trigger_message(follow_client_id, next_message_id + index, trigger),
                        transport,
                    )
                )
    elif data_case == "HeartbeatReq":
        replies.append(maybe_wrap(build_heartbeat_conf(reply_client_id, message_id), transport))
    elif data_case == "MeterValuesReq":
        replies.append(maybe_wrap(build_empty_conf(reply_client_id, 31, message_id), transport))
    elif data_case == "StatusNotificationReq":
        replies.append(maybe_wrap(build_empty_conf(reply_client_id, 47, message_id), transport))
    elif data_case == "DataTransferReq":
        nested = decoded.get("data")
        if isinstance(nested, dict) and nested.get("dataCase") == "DataVendorStatusReq":
            replies.append(maybe_wrap(build_data_vendor_status_conf(reply_client_id, message_id), transport))
    return replies


def recv_frames(
    host: str,
    port: int,
    payload: bytes,
    duration: float,
    transport: str,
    request_config: bool,
    session_triggers: List[int],
    config_updates: List[Tuple[str, str]],
    persist_config: bool,
) -> List[bytes]:
    sock = socket.socket()
    sock.settimeout(1.0)
    sock.connect((host, port))
    if payload:
        sock.sendall(payload)

    frames: List[bytes] = []
    raw_frames: List[bytes] = []
    buffer = bytearray()
    raw_buffer = bytearray()
    sent_session_actions = False
    end = time.time() + duration

    while time.time() < end:
        try:
            data = sock.recv(4096)
        except socket.timeout:
            continue
        if not data:
            break
        if transport == "wrapped":
            if data.startswith(b"\x55\xfd\xaa"):
                buffer.extend(data)
                new_frames = unwrap_user_wifi(buffer)
            else:
                new_frames = [data]
            frames.extend(new_frames)
            for frame in new_frames:
                try:
                    decoded = decode_ocpp_message(frame)
                except ValueError:
                    decoded = {}
                send_session_actions = (
                    request_config
                    and not sent_session_actions
                    and decoded.get("dataCase") == "BootNotificationReq"
                )
                if send_session_actions:
                    sent_session_actions = True
                send_replies(
                    sock,
                    build_auto_reply(
                        frame,
                        transport=transport,
                        request_config=send_session_actions,
                        session_triggers=session_triggers if send_session_actions else [],
                        config_updates=config_updates if send_session_actions else [],
                        persist_config=persist_config,
                    ),
                )
        else:
            raw_buffer.extend(data)
            new_frames = extract_raw_ocpp_messages(raw_buffer)
            raw_frames.extend(new_frames)
            for frame in new_frames:
                try:
                    decoded = decode_ocpp_message(frame)
                except ValueError:
                    decoded = {}
                send_session_actions = (
                    request_config
                    and not sent_session_actions
                    and decoded.get("dataCase") == "BootNotificationReq"
                )
                if send_session_actions:
                    sent_session_actions = True
                send_replies(
                    sock,
                    build_auto_reply(
                        frame,
                        transport=transport,
                        request_config=send_session_actions,
                        session_triggers=session_triggers if send_session_actions else [],
                        config_updates=config_updates if send_session_actions else [],
                        persist_config=persist_config,
                    ),
                )

    sock.close()
    return frames if transport == "wrapped" else raw_frames


def send_replies(sock: socket.socket, replies: List[bytes]) -> None:
    for index, reply in enumerate(replies):
        if index:
            time.sleep(0.3)
        sock.sendall(reply)


def hexdump_chunks(chunks: Iterable[bytes]) -> None:
    for index, chunk in enumerate(chunks, start=1):
        print(f"frame {index} len {len(chunk)}")
        print(chunk.hex())
        try:
            decoded = decode_ocpp_message(chunk)
        except ValueError as exc:
            print(f"decode_error: {exc}")
            print()
            continue
        if decoded:
            for line in format_decoded(decoded):
                print(line)
        else:
            print("decoded: <empty>")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe a Duosida charger on TCP/9988.")
    parser.add_argument("--host", default="192.168.7.140")
    parser.add_argument("--port", type=int, default=9988)
    parser.add_argument(
        "--mode",
        choices=[
            "session",
            "trigger",
            "trigger-boot",
            "pull-config",
            "change-config",
            "set-max-current",
            "set-max-current-direct",
            "start",
            "stop",
            "ascii",
        ],
        default="session",
    )
    parser.add_argument("--transport", choices=["raw", "wrapped"], default="raw")
    parser.add_argument("--ascii", default="STATUS")
    parser.add_argument("--client-id", default="From Python")
    parser.add_argument("--message-id", type=int)
    parser.add_argument(
        "--trigger",
        choices=sorted(TRIGGER_NAME_TO_VALUE),
        default="heartbeat",
        help="Trigger message to send in trigger mode or after session boot.",
    )
    parser.add_argument(
        "--session-trigger",
        action="append",
        choices=sorted(TRIGGER_NAME_TO_VALUE),
        default=[],
        help="Additional trigger to send after session boot. Can be repeated.",
    )
    parser.add_argument("--id-tag")
    parser.add_argument("--transaction-id", type=int)
    parser.add_argument("--config-key")
    parser.add_argument("--config-value")
    parser.add_argument("--max-current", type=float)
    parser.add_argument("--no-persist", action="store_true", help="Do not send DataUpdateToflashReq after a config change.")
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--request-config", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print the latest decoded state as JSON.")
    args = parser.parse_args()

    if args.mode == "session":
        args.request_config = True
        if args.trigger:
            args.session_trigger.insert(0, args.trigger)
    elif args.mode in {"set-max-current", "set-max-current-direct"}:
        if args.max_current is None:
            raise ValueError(f"--max-current is required for mode={args.mode}")
        if not 6 <= args.max_current <= 32:
            raise ValueError("--max-current must be between 6 and 32 A")
    if args.mode == "set-max-current":
        args.request_config = True
        args.config_key = "VendorMaxWorkCurrent"
        args.config_value = f"{args.max_current:g}"
        args.session_trigger.insert(0, "meter-values")

    payload = build_payload(args)
    session_triggers = [TRIGGER_NAME_TO_VALUE[name] for name in args.session_trigger]
    config_updates = []
    if args.config_key and args.config_value is not None:
        config_updates.append((args.config_key, args.config_value))
    frames = recv_frames(
        args.host,
        args.port,
        payload,
        args.duration,
        transport=args.transport if args.mode != "ascii" else "raw",
        request_config=args.request_config,
        session_triggers=session_triggers,
        config_updates=config_updates if args.mode != "change-config" else [],
        persist_config=not args.no_persist,
    )
    if not frames:
        print("No frames received.")
        return
    if args.json:
        print(json.dumps(build_state(frames), indent=2, sort_keys=True))
        return
    hexdump_chunks(frames)


if __name__ == "__main__":
    main()
